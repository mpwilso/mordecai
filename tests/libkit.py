"""Builds skill libraries in temporary Git repositories, for the library and MCP tests.

Every repository gets its own Git identity and an empty global config, so a developer's own Git
settings (such as commit signing) never change what a test sees.
"""

import json
import subprocess
from pathlib import Path

from builder import make_result, same

from mordecai.card import build, to_json
from mordecai.library import changelog as cl
from mordecai.library.release import fork, release
from mordecai.result import parse


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )
    return done.stdout


def isolate_git(monkeypatch, tmp_path: Path) -> None:
    config = tmp_path / "gitconfig"
    config.write_text("")
    for key, value in {
        "GIT_CONFIG_GLOBAL": str(config),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        "MORDECAI_CACHE": str(tmp_path / "cache"),
        "XDG_CONFIG_HOME": str(tmp_path / "xdg-config"),
        "XDG_STATE_HOME": str(tmp_path / "xdg-state"),
    }.items():
        monkeypatch.setenv(key, value)
    for key in ("MORDECAI_LIBRARY_CONFIG", "MORDECAI_GITHUB_TOKEN", "GITHUB_TOKEN"):
        monkeypatch.delenv(key, raising=False)


def init(repo: Path) -> Path:
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, "init", "--quiet", "--initial-branch=main")
    return repo


def commit(repo: Path, message: str = "change") -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "--quiet", "--allow-empty", "-m", message)
    return git(repo, "rev-parse", "HEAD").strip()


def skill_md(name: str, description: str, body: str, stamps: dict | None = None) -> str:
    meta = ""
    if stamps:
        meta = "metadata:\n" + "".join(f'  {k}: "{v}"\n' for k, v in stamps.items())
    return f"---\nname: {name}\ndescription: {description}\n{meta}---\n\n{body}\n"


def write_copy(
    repo: Path,
    skill: str,
    variant: str | None = None,
    body: str = "Say hello.",
    description: str | None = None,
    based_on: str | None = None,
    notes: tuple = ("- First version.",),
    stamps: bool = False,
    library: str = "library",
) -> Path:
    """An unreleased copy with an Unreleased changelog section. Returns its copy folder."""
    path = repo / library / skill / (f"variants/{variant}" if variant else "base")
    folder = path / skill
    folder.mkdir(parents=True, exist_ok=True)
    s = None
    if stamps:
        s = {"mordecai-version": "0.0.0"}
        if variant:
            s.update({"mordecai-variant": variant, "mordecai-based-on": f"{skill}@{based_on}"})
    text = skill_md(skill, description or f"Use when greeting someone ({skill}).", body, s)
    (folder / "SKILL.md").write_text(text)
    from mordecai.library.versions import parse_version

    log = cl.new(parse_version(based_on) if based_on else None, list(notes))
    (path / "CHANGELOG.md").write_text(cl.render(log))
    return path


def note(copy_dir: Path, text: str) -> None:
    """Add a line under Unreleased."""
    log_path = copy_dir / "CHANGELOG.md"
    variant = "variants" in copy_dir.parts
    log = cl.parse(log_path.read_text(), variant)
    sec = log.unreleased or cl.Section(None, None, log.based_on, ())
    from dataclasses import replace

    log = replace(log, unreleased=replace(sec, notes=(*sec.notes, text)))
    log_path.write_text(cl.render(log))


def greeting_library(repo: Path, stamps: bool = True) -> Path:
    """A library with skill 'greeting': base 1.0.0 and 1.1.0, variant 'formal' 1.0.0 based on
    base 1.0.0 (so behind), and variant 'brief' 1.0.0 based on 1.1.0. All committed and tagged."""
    init(repo)
    (repo / "README.md").write_text("a library\n")
    base = write_copy(repo, "greeting", stamps=stamps)
    commit(repo, "start")
    release(repo / "library", "greeting", None, "major")
    (base / "greeting" / "SKILL.md").write_text(
        (base / "greeting" / "SKILL.md").read_text().replace("Say hello.", "Say hello warmly.")
    )
    note(base, "- Warmer.")
    release(repo / "library", "greeting", None, "minor")
    formal = repo / "library/greeting/variants/formal"
    fork(repo / "library", "greeting", "formal")
    (formal / "greeting" / "SKILL.md").write_text(
        (formal / "greeting" / "SKILL.md").read_text().replace("Say hello", "Say good day")
    )
    commit(repo, "fork formal")
    # Fork happened at 1.1.0; pin formal's lineage to 1.0.0 to make it behind.
    release(repo / "library", "greeting", "formal", "major", based_on="1.0.0")
    fork(repo / "library", "greeting", "brief")
    commit(repo, "fork brief")
    release(repo / "library", "greeting", "brief", "major")
    return repo


def add_card(
    repo: Path,
    copy_dir: Path,
    version: str,
    effect: str = "helps",
    cases_at: str = "evals/greeting",
) -> Path:
    """A real card and result for copy_dir's skill folder, made by the engine, in
    evidence/<version>/. The cases live at cases_at in the repo."""
    skill = copy_dir.parent.parent.name if "variants" in copy_dir.parts else copy_dir.parent.name
    cases_root = repo / cases_at
    names = [f"case-{i}" for i in range(6)]
    for n in names:
        (cases_root / "evals" / n).mkdir(parents=True, exist_ok=True)
        (cases_root / "evals" / n / "prompt.md").write_text(f"Do {n}.\n")
    with_, without = {"helps": ([1, 1, 1], [0, 0, 0]), "hurts": ([0, 0, 0], [1, 1, 1])}[effect]
    doc = make_result(same(6, with_, without), plugin_path=str(cases_root))
    data = json.dumps(doc, indent=2).encode()
    card = build(parse(doc), data, copy_dir / skill, roots=[repo])
    out = copy_dir / "evidence" / version
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_bytes(data)
    (out / "card.json").write_text(to_json(card, out))
    return out
