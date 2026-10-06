"""Everything a source, config, lockfile or MCP argument holds is untrusted. Each test here was
a problem reproduced first, or a check that one can't happen: paths that escape, links that are
followed, Git options or transports smuggled in, hooks that run, a token that leaks, and an MCP
error that names local folders."""

import io
import json
import os
import subprocess

import pytest

pytest.importorskip("strictyaml")

from libkit import commit, git, greeting_library, init, write_copy  # noqa: E402

from mordecai.cli import main  # noqa: E402
from mordecai.library import LibraryError, gitio  # noqa: E402
from mordecai.library import install as inst  # noqa: E402
from mordecai.library.export import export_marketplace, export_skills  # noqa: E402
from mordecai.library.lock import Lock  # noqa: E402
from mordecai.library.skillmd import check_folder  # noqa: E402
from mordecai.library.sources import Library, parse_config  # noqa: E402
from mordecai.provenance import hash_dir  # noqa: E402


def run(argv):
    out = io.StringIO()
    try:
        code = main(argv, out=out)
    except SystemExit as e:  # argparse refusing an argument
        code = e.code
    return code, out.getvalue()


@pytest.fixture
def setup(gitenv):
    repo = greeting_library(gitenv / "lib")
    proj = gitenv / "proj"
    (proj / "src").mkdir(parents=True)
    (proj / "src" / "main.py").write_text("code\n")
    cfg = gitenv / "mordecai-library.toml"
    cfg.write_text(f'[[source]]\nname = "org"\npath = "{repo}"\n')
    return repo, proj, cfg


def lib_for(repo, **extra):
    doc = {"source": [{"name": "org", "path": str(repo)}], **extra}
    return Library(parse_config(doc, None, repo.parent))


def entry(skill, hash_):
    return {
        "skill": skill,
        "variant": None,
        "version": "1.0.0",
        "tag": None,
        "source": {},
        "commit": None,
        "path": "p",
        "hash": hash_,
        "verdict": "unmeasured",
        "evidence": "unmeasured",
        "allowed": [],
    }


def write_lock(proj, entries):
    (proj / "mordecai-lock.json").write_text(
        json.dumps({"lockfileVersion": 1, "installed": entries})
    )


# Lockfiles -------------------------------------------------------------------------------------


def test_a_tampered_lockfile_cant_make_uninstall_delete_the_project(setup):
    """Reproduced: a lockfile naming src/ as an install of skill "src", with src/'s hash, made
    uninstall delete it."""
    _, proj, _ = setup
    write_lock(proj, {"src": entry("src", hash_dir(proj / "src"))})
    assert run(["library", "uninstall", "src", "--project", str(proj)])[0] == 2
    assert (proj / "src" / "main.py").read_text() == "code\n"


@pytest.mark.parametrize("key", ["/etc/greeting", "../greeting", "a/../../greeting", "a\\greeting"])
def test_lockfile_keys_that_escape_are_refused(setup, key):
    _, proj, _ = setup
    write_lock(proj, {key: entry("greeting", "sha256:00")})
    assert run(["library", "uninstall", "greeting", "--project", str(proj)])[0] == 2
    assert run(["library", "status", "--project", str(proj)])[0] == 2


def test_a_lockfile_entry_for_a_folder_that_isnt_that_skill_is_never_touched(setup, capsys):
    """Even with --force, update and uninstall leave alone a folder whose SKILL.md doesn't name
    the skill the lockfile says is there."""
    repo, proj, cfg = setup
    victim = proj / "notes" / "greeting"
    victim.mkdir(parents=True)
    (victim / "todo.md").write_text("mine\n")
    write_lock(proj, {"notes/greeting": entry("greeting", hash_dir(victim))})
    args = ["--config", str(cfg), "--project", str(proj)]
    code, _ = run(["library", "uninstall", "greeting", "--force", "--project", str(proj)])
    assert code == 2 and "isn't a greeting skill folder" in capsys.readouterr().err
    code, text = run(["library", "update", "--yes", "--force", *args])
    assert "isn't a greeting skill folder" in text
    assert (victim / "todo.md").read_text() == "mine\n"


def test_a_lockfile_entry_through_a_link_is_refused(setup, gitenv):
    _, proj, _ = setup
    elsewhere = gitenv / "elsewhere" / "greeting"
    elsewhere.mkdir(parents=True)
    (elsewhere / "SKILL.md").write_text("---\nname: greeting\ndescription: d\n---\nx\n")
    (proj / ".agents" / "skills").mkdir(parents=True)
    (proj / ".agents" / "skills" / "greeting").symlink_to(elsewhere)
    write_lock(proj, {".agents/skills/greeting": entry("greeting", hash_dir(elsewhere))})
    assert run(["library", "uninstall", "greeting", "--project", str(proj)])[0] == 2
    assert (elsewhere / "SKILL.md").exists()


# Targets and names -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "target", ["..\\..\\evil", "C:\\Users\\x", "C:/x", "tools\x1bskills", "tools\x00x"]
)
def test_targets_with_windows_separators_drives_or_control_characters(setup, target):
    """Reproduced: ..\\..\\evil installed into a folder of that name on Linux, which on Windows
    would be outside the project."""
    _, proj, cfg = setup
    argv = ["library", "install", "greeting", "--target", target]
    assert run([*argv, "--config", str(cfg), "--project", str(proj)])[0] == 2
    assert sorted(p.name for p in proj.iterdir()) == ["src"]


@pytest.mark.parametrize(
    "name",
    ["../greeting", "greeting/../x", "Greeting", "gr" + chr(0x0435) + "eting", "greeting\\x", "-x"],
)
def test_skill_and_variant_names_from_any_input_are_checked(setup, name):
    _, proj, cfg = setup
    at = ["--project", str(proj)]
    for argv in (
        ["library", "install", name, *at],
        ["library", "install", "greeting", "--variant", name, *at],
        ["library", "show", name],
    ):
        code, _ = run([*argv, "--config", str(cfg)])
        assert code == 2, argv
    assert sorted(p.name for p in proj.iterdir()) == ["src"]


def test_versions_are_matched_not_used_as_paths(setup):
    _, proj, cfg = setup
    for version in ("../1.0.0", "1.0.0/../../x", "-1"):
        code, _ = run(
            [
                "library",
                "install",
                "greeting",
                "--version",
                version,
                "--config",
                str(cfg),
                "--project",
                str(proj),
            ]
        )
        assert code == 2


def test_names_that_collide_on_case_insensitive_file_systems(tmp_path):
    """Reproduced: SKILL.md beside skill.md, or Notes.md beside notes.md, passed validation,
    and would overwrite each other when installed on macOS or Windows."""
    folder = tmp_path / "demo"
    folder.mkdir()
    (folder / "SKILL.md").write_text("---\nname: demo\ndescription: d\n---\nx\n")
    (folder / "skill.md").write_text("other")
    (folder / ("caf" + chr(0xE9))).write_text("nfc")
    (folder / ("cafe" + chr(0x301))).write_text("nfd")
    errors = check_folder(folder, "demo").errors
    assert any("SKILL.md and skill.md" in e for e in errors)
    assert sum("differ only by case or Unicode form" in e for e in errors) == 2


def test_spec_valid_names_cant_collide_by_case():
    """Skill and variant names are lowercase ASCII, so no two valid names differ only by case."""
    from mordecai.library.versions import valid_name

    assert not valid_name("Greeting") and not valid_name("GREETING")


# Links in sources ------------------------------------------------------------------------------


def test_evidence_reached_through_a_link_is_never_read(setup, gitenv, monkeypatch):
    """Reproduced: an evidence/<version> folder that was a link out of the source had its
    card.json read."""
    repo, _, _ = setup
    outside = gitenv / "outside"
    outside.mkdir()
    (outside / "card.json").write_text('{"card": 1}')
    ev = repo / "library/greeting/base/evidence"
    ev.mkdir(parents=True)
    os.symlink(str(outside), ev / "1.1.0")
    commit(repo, "evidence link")
    import mordecai.library.evidence as evidence

    seen = []
    real = evidence.read_json
    monkeypatch.setattr(evidence, "read_json", lambda p, w: seen.append(p) or real(p, w))
    with lib_for(repo) as lib:
        r = lib.get("greeting", None)
        e = lib.evidence(r, lib.pick(r))
    assert e.state == "broken" and "link" in e.note
    assert seen == []


def test_materializing_never_writes_through_a_link(setup, gitenv):
    """Reproduced: a link already in the work folder (as a link "A" and a file "a/b" from one
    tree would meet on a case-insensitive file system) was written through."""
    repo, _, _ = setup
    dest, escaped = gitenv / "dest", gitenv / "escaped"
    dest.mkdir()
    escaped.mkdir()
    os.symlink(str(escaped), dest / "library")
    with pytest.raises(LibraryError, match="symbolic link"):
        gitio.materialize(repo, gitio.resolve(repo, "HEAD"), "library", dest, [10**9])
    assert list(escaped.iterdir()) == []


def test_links_inside_a_source_are_written_as_links_and_never_followed(setup, gitenv):
    repo, proj, cfg = setup
    (gitenv / "secret.txt").write_text("secret")
    (repo / "library/greeting/notes").symlink_to(gitenv / "secret.txt")
    commit(repo, "a link beside the skills")
    with lib_for(repo) as lib:
        link = lib.snapshots[0].root / "library/greeting/notes"
        assert link.is_symlink() and os.readlink(link) == str(gitenv / "secret.txt")
    assert (
        run(["library", "install", "greeting", "--config", str(cfg), "--project", str(proj)])[0]
        == 0
    )
    assert not any(b"secret" in p.read_bytes() for p in proj.rglob("*") if p.is_file())


def test_submodules_in_a_source_are_skipped(gitenv):
    repo = init(gitenv / "lib")
    write_copy(repo, "greeting")
    commit(repo)
    sha = git(repo, "rev-parse", "HEAD").strip()
    git(repo, "update-index", "--add", "--cacheinfo", f"160000,{sha},library/greeting/base/sub")
    git(repo, "commit", "--quiet", "-m", "a submodule entry")
    dest = gitenv / "dest"
    dest.mkdir()
    gitio.materialize(repo, gitio.resolve(repo, "HEAD"), "library", dest, [10**9])
    assert not (dest / "library/greeting/base/sub").exists()


def test_reading_a_source_runs_none_of_its_hooks_or_fsmonitor(setup, gitenv):
    repo, proj, cfg = setup
    marker = gitenv / "ran"
    script = f"#!/bin/sh\necho ran >> {marker}\n"
    hooks = repo / ".git" / "hooks"
    for name in (
        "reference-transaction",
        "post-checkout",
        "post-merge",
        "pre-commit",
        "post-index-change",
        "fsmonitor-watchman",
    ):
        (hooks / name).write_text(script)
        (hooks / name).chmod(0o755)
    git(repo, "config", "core.fsmonitor", str(hooks / "fsmonitor-watchman"))
    for argv in (
        ["library", "list"],
        ["library", "status", "--project", str(proj)],
        ["library", "install", "greeting", "--project", str(proj)],
    ):
        run([*argv, "--config", str(cfg)])
    assert not marker.exists()


# Git options and transports --------------------------------------------------------------------


@pytest.mark.parametrize("ref", ["--output=/tmp/x", "-c", "--upload-pack=touch x", "a\x00b"])
def test_refs_cant_be_read_as_options(setup, ref):
    repo, _, _ = setup
    doc = {"source": [{"name": "s", "path": str(repo), "ref": ref}]}
    with pytest.raises(LibraryError, match="will use"):
        Library(parse_config(doc, None, repo.parent))
    with pytest.raises(LibraryError):
        gitio.fetch_github("acme/skills", ref)


@pytest.mark.parametrize(
    "name",
    [
        "user:pw@github.com/x",
        "acme/skills@evil",
        "ext::sh -c touch% /tmp/x",
        "file:///etc/x",
        "acme/../x",
        "-acme/x",
        "acme/.git",
    ],
)
def test_github_names_cant_carry_credentials_or_another_transport(name):
    with pytest.raises(LibraryError):
        gitio.fetch_github(name, None)


def test_the_fetch_allows_only_https_and_no_submodules_or_hooks(monkeypatch, gitenv):
    seen = []
    real = subprocess.run

    def fake_run(cmd, **kw):
        if "fetch" not in cmd:
            return real(cmd, **kw)
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 1, b"", b"stopped")

    monkeypatch.setattr(gitio, "GITHUB", "https://github.com")
    monkeypatch.setattr(gitio.subprocess, "run", fake_run)
    with pytest.raises(LibraryError):
        gitio.fetch_github("acme/skills", "main")
    fetch = next(c for c in seen if "fetch" in c)
    assert "protocol.allow=never" in fetch and "protocol.https.allow=always" in fetch
    assert "--no-recurse-submodules" in fetch
    assert f"core.hooksPath={os.devnull}" in fetch
    assert "https://github.com/acme/skills.git" in fetch
    assert fetch.index("--") < fetch.index("https://github.com/acme/skills.git")


def test_git_calls_have_a_time_limit_and_reads_a_size_limit(setup, monkeypatch):
    import inspect

    assert "timeout=300" in inspect.getsource(gitio.git)
    repo, _, _ = setup
    with pytest.raises(LibraryError, match="too large"):
        gitio.materialize(repo, gitio.resolve(repo, "HEAD"), "library", repo.parent / "d", [10])


# The token -------------------------------------------------------------------------------------


FAKE = "ghp_FAKEtokenFAKEtokenFAKEtoken0123456789"


def test_a_fake_token_appears_in_no_output_file_argument_or_response(setup, gitenv, monkeypatch):
    import base64

    import anyio

    repo, proj, _ = setup
    monkeypatch.setenv("MORDECAI_GITHUB_TOKEN", FAKE)
    remote = gitenv / "remote" / "acme" / "skills.git"
    remote.parent.mkdir(parents=True)
    git(gitenv, "clone", "--quiet", "--bare", str(repo), str(remote))
    monkeypatch.setattr(gitio, "GITHUB", (gitenv / "remote").as_uri())
    cfg = gitenv / "gh.toml"
    cfg.write_text('[[source]]\nname = "org"\ngithub = "acme/skills"\n')
    argvs = []
    real_run, real_popen = subprocess.run, subprocess.Popen

    def spy_run(cmd, *a, **kw):
        argvs.append(list(cmd))
        return real_run(cmd, *a, **kw)

    class spy_popen(real_popen):
        def __init__(self, cmd, *a, **kw):
            argvs.append(list(cmd))
            super().__init__(cmd, *a, **kw)

    monkeypatch.setattr(gitio.subprocess, "run", spy_run)
    monkeypatch.setattr(gitio.subprocess, "Popen", spy_popen)
    outputs = []
    args = ["--config", str(cfg), "--project", str(proj)]
    for argv in (
        ["library", "list", "--config", str(cfg)],
        ["library", "show", "greeting", "--config", str(cfg)],
        ["library", "history", "greeting", "--config", str(cfg)],
        ["library", "install", "greeting", *args],
        ["library", "update", *args],
        ["library", "status", *args],
        ["library", "export", "--marketplace", str(gitenv / "market"), "--config", str(cfg)],
        ["library", "show", "missing", "--config", str(cfg)],
    ):
        outputs.append(run(argv)[1])
    from mcp import Client

    from mordecai.library.server import build

    async def mcp_calls():
        async with Client(build(cfg, proj)) as c:
            for tool, a in (
                ("list_skills", {}),
                ("get_skill", {"skill": "greeting"}),
                ("check_updates", {}),
                ("install_skill", {"skill": "nope"}),
            ):
                r = await c.call_tool(tool, a)
                outputs.append(json.dumps(r.model_dump(mode="json")))

    anyio.run(mcp_calls)
    # A fetch that fails says why without the token.
    monkeypatch.setattr(gitio, "GITHUB", (gitenv / "nowhere").as_uri())
    with pytest.raises(LibraryError) as e:
        gitio.fetch_github("acme/other", None)
    outputs.append(str(e.value))
    encoded = base64.b64encode(f"x-access-token:{FAKE}".encode()).decode()
    files = [p for p in (proj, gitenv / "market", gitenv / "cache") for p in p.rglob("*")]
    for text in outputs + [" ".join(a) for a in argvs]:
        assert FAKE not in text and encoded not in text
    for path in files:
        if path.is_file() and not path.is_symlink():
            data = path.read_bytes()
            assert FAKE.encode() not in data and encoded.encode() not in data, path


# The MCP server --------------------------------------------------------------------------------


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_mcp_errors_name_no_local_folder(setup, gitenv):
    from mcp import Client

    from mordecai.library.server import build

    _, proj, _ = setup
    cfg = gitenv / "bad.toml"
    cfg.write_text(f'[[source]]\nname = "org"\npath = "{gitenv / "no-such-folder"}"\n')
    async with Client(build(cfg, proj)) as c:
        r = await c.call_tool("list_skills", {})
    text = " ".join(b.text for b in r.content)
    assert r.is_error and "isn't a folder" in text
    assert str(gitenv) not in text and str(proj) not in text and "Traceback" not in text


@pytest.mark.anyio
async def test_mcp_arguments_are_checked(setup, gitenv):
    from mcp import Client

    from mordecai.library.server import build

    _, proj, cfg = setup
    async with Client(build(cfg, proj)) as c:
        tools = {t.name: t for t in (await c.list_tools()).tools}
        assert "allow" not in tools["install_skill"].input_schema["properties"]
        assert "project" not in tools["install_skill"].input_schema["properties"]
        for tool, a in (
            ("search_skills", {"query": "x" * 500}),
            ("get_skill", {"skill": "greeting", "version": "1" * 500}),
            ("get_skill", {"skill": "../etc"}),
            ("install_skill", {"skill": "greeting", "target": str(gitenv)}),
            ("install_skill", {"skill": "greeting", "target": "tools/skills"}),
            ("uninstall_skill", {"skill": "greeting", "target": "../.."}),
        ):
            r = await c.call_tool(tool, a)
            assert r.is_error, (tool, a)
    assert sorted(p.name for p in proj.iterdir()) == ["src"]


# Exports ---------------------------------------------------------------------------------------


def test_export_never_writes_through_a_link_left_in_its_folder(setup, gitenv):
    repo, _, _ = setup
    out, outside = gitenv / "market", gitenv / "outside"
    outside.mkdir()
    with lib_for(repo) as lib:
        export_marketplace(lib, out, "acme", "Acme")
        import shutil

        shutil.rmtree(out / "plugins")
        (out / "plugins").symlink_to(outside)
        export_marketplace(lib, out, "acme", "Acme")
        export_skills(lib, gitenv / "flat")
    assert list(outside.iterdir()) == []
    assert (out / "plugins").is_dir() and not (out / "plugins").is_symlink()


def test_export_refuses_a_folder_that_is_a_link(setup, gitenv):
    repo, _, _ = setup
    (gitenv / "real").mkdir()
    (gitenv / "market").symlink_to(gitenv / "real")
    with lib_for(repo) as lib:
        with pytest.raises(LibraryError, match="symbolic link"):
            export_marketplace(lib, gitenv / "market", "acme", "Acme")


def test_update_writes_only_where_the_lockfile_entry_can_be(setup):
    repo, proj, cfg = setup
    args = ["--config", str(cfg), "--project", str(proj)]
    assert run(["library", "install", "greeting", "--version", "1.0.0", *args])[0] == 0
    lock = Lock(proj / "mordecai-lock.json")
    good = lock.entries[".agents/skills/greeting"]
    with lib_for(repo) as lib:
        updates = inst.plan_updates(lib, inst.project(proj), lock)
    assert [u.key for u in updates] == [".agents/skills/greeting"]
    assert updates[0].plan.destinations[0].path == proj / ".agents/skills/greeting"
    assert good["hash"] == hash_dir(proj / ".agents/skills/greeting")
