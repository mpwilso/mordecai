"""Install, update and uninstall, the evidence gate, and the lockfile, including hostile sources
and targets. The central property: an installed folder is byte for byte its stored copy, so a
card's skill hash verifies against it."""

import io
import json
import os

import pytest

pytest.importorskip("strictyaml")

from libkit import add_card, commit, git, greeting_library, note  # noqa: E402

from mordecai.cli import main  # noqa: E402
from mordecai.library import LibraryError  # noqa: E402
from mordecai.library import install as inst  # noqa: E402
from mordecai.library.lock import Lock  # noqa: E402
from mordecai.library.release import release  # noqa: E402
from mordecai.library.sources import Library, parse_config  # noqa: E402
from mordecai.provenance import hash_dir, hash_skill  # noqa: E402


@pytest.fixture
def setup(gitenv):
    repo = greeting_library(gitenv / "lib")
    add_card(repo, repo / "library/greeting/variants/brief", "1.0.0", "hurts")
    add_card(repo, repo / "library/greeting/base", "1.1.0", "helps")
    commit(repo, "cards")
    proj = gitenv / "proj"
    proj.mkdir()
    cfg = gitenv / "mordecai-library.toml"
    cfg.write_text(f'[[source]]\nname = "org"\npath = "{repo}"\n')
    return repo, proj, cfg


def run(argv):
    out = io.StringIO()
    code = main(argv, out=out)
    return code, out.getvalue()


def lib_for(repo, **extra):
    return Library(
        parse_config({"source": [{"name": "org", "path": str(repo)}], **extra}, None, repo.parent)
    )


def test_install_is_byte_for_byte_and_the_card_verifies_against_it(setup):
    repo, proj, cfg = setup
    code, text = run(
        [
            "library",
            "install",
            "greeting",
            "--config",
            str(cfg),
            "--project",
            str(proj),
            "--target",
            "agents",
            "--target",
            "claude",
        ]
    )
    assert code == 0, text
    assert "Installed greeting (base) 1.1.0 (helps)" in text
    stored = repo / "library/greeting/base/greeting"
    card = json.loads((repo / "library/greeting/base/evidence/1.1.0/card.json").read_text())
    for target in (".agents/skills/greeting", ".claude/skills/greeting"):
        installed = proj / target
        assert hash_dir(installed) == hash_dir(stored)
        assert hash_skill(installed, card["paths"]["caseDirs"]) == card["hashes"]["skill"]
        for f in stored.rglob("*"):
            if f.is_file():
                assert (installed / f.relative_to(stored)).read_bytes() == f.read_bytes()
    lock = json.loads((proj / "mordecai-lock.json").read_text())
    entry = lock["installed"][".agents/skills/greeting"]
    assert entry["commit"] == git(repo, "rev-list", "-n1", "skill/greeting@1.1.0").strip()
    assert entry["tag"] == "skill/greeting@1.1.0"
    assert entry["verdict"] == "helps" and entry["evidence"] == "current"
    assert entry["hash"] == hash_dir(stored)
    assert entry["source"] == {"name": "org", "path": str(repo)}


def test_hurts_is_refused_unless_allowed_and_the_override_is_recorded(setup):
    repo, proj, cfg = setup
    argv = [
        "library",
        "install",
        "greeting",
        "--variant",
        "brief",
        "--config",
        str(cfg),
        "--project",
        str(proj),
    ]
    code, text = run(argv)
    assert code == 1
    assert "Refused" in text and "hurts" in text and "--allow hurts" in text
    assert not (proj / ".agents").exists() and not (proj / "mordecai-lock.json").exists()
    code, text = run(argv + ["--allow", "hurts"])
    assert code == 0
    lock = json.loads((proj / "mordecai-lock.json").read_text())
    assert lock["installed"][".agents/skills/greeting"]["allowed"] == ["hurts"]


def test_a_config_can_add_refusals_but_not_drop_the_defaults(setup):
    repo, proj, _ = setup
    with lib_for(repo, policy={"refuse": ["unmeasured"]}) as lib:
        assert lib.config.refuse == ("hurts", "invalid", "broken", "unmeasured")
        p = inst.plan(lib, inst.project(proj), Lock(proj / "x.json"), "greeting", "formal")
        assert p.refused and "unmeasured" in p.refused
        p = inst.plan(lib, inst.project(proj), Lock(proj / "x.json"), "greeting", "brief")
        assert p.refused and "hurts" in p.refused


def edit_card(path, **changes):
    doc = json.loads(path.read_text())
    for dotted, value in changes.items():
        part, key = dotted.split(".") if "." in dotted else (None, dotted)
        (doc[part] if part else doc)[key] = value
    path.write_text(json.dumps(doc))


@pytest.mark.parametrize(
    "tamper,state",
    [
        (lambda d: edit_card(d / "card.json", verdict="helps"), "broken"),
        (lambda d: (d / "result.json").write_text("{}"), "broken"),
        (lambda d: (d / "result.json").unlink(), "broken"),
        (lambda d: (d / "card.json").write_text("not json"), "broken"),
        (lambda d: edit_card(d / "card.json", **{"rules.min_cases": 7}), "broken"),
        (lambda d: edit_card(d / "card.json", **{"hashes.skill": "sha256:00"}), "stale"),
        (
            lambda d: edit_card(d / "card.json", **{"paths.casesRoot": "../../nowhere"}),
            "cases-changed",
        ),
    ],
)
def test_a_card_that_doesnt_match_its_version_or_result(setup, tamper, state):
    repo, proj, _ = setup
    tamper(repo / "library/greeting/variants/brief/evidence/1.0.0")
    commit(repo, "tamper")
    with lib_for(repo) as lib:
        r = lib.get("greeting", "brief")
        e = lib.evidence(r, lib.pick(r))
        assert e.state == state, e
        p = inst.plan(lib, inst.project(proj), Lock(proj / "x.json"), "greeting", "brief")
        # Broken is refused; stale only warns; a current Hurts with changed cases still refuses.
        assert bool(p.refused) == (state in ("broken", "cases-changed"))


@pytest.mark.parametrize(
    "rules",
    [
        {"resamples": 0},  # was IndexError
        {"resamples": 10**9},  # was a hang
        {"resamples": 2000.5},  # was TypeError
        {"min_cases": 0},  # was ZeroDivisionError on quiet cases
        {"min_effect": 0, "min_cases": 1},  # looser rules: the verdict may even agree
        {"confidence": 0.5},
    ],
)
def test_a_card_with_other_rules_is_broken_and_fast(setup, rules):
    """D20: only the engine's own rules are accepted, so a hostile card can't crash, hang or
    shop for an easier verdict."""
    import time

    repo, _, _ = setup
    edit_card(
        repo / "library/greeting/variants/brief/evidence/1.0.0/card.json",
        **{f"rules.{k}": v for k, v in rules.items()},
    )
    commit(repo, "other rules")
    start = time.monotonic()
    with lib_for(repo) as lib:
        r = lib.get("greeting", "brief")
        e = lib.evidence(r, lib.pick(r))
    assert e.state == "broken" and "rules" in e.note, e
    assert time.monotonic() - start < 5


@pytest.mark.parametrize(
    "changes,state,verdict",
    [
        ({"numbers.blockedRuns": 1, "verdict": "invalid"}, "current", "invalid"),
        ({"numbers.blockedRuns": 1}, "broken", None),  # its verdict no longer follows
        ({"numbers.blockedRuns": -1}, "broken", None),
        ({"numbers.blockedRuns": True}, "broken", None),
        ({"numbers.blockedRuns": 10**6}, "broken", None),
    ],
)
def test_the_check_takes_the_cards_blocked_runs(setup, changes, state, verdict):
    """D19: a library card doesn't ship its traces, so the check reruns the verdict with the
    count of blocked runs the card recorded."""
    repo, _, _ = setup
    edit_card(repo / "library/greeting/variants/brief/evidence/1.0.0/card.json", **changes)
    commit(repo, "blocked runs")
    with lib_for(repo) as lib:
        r = lib.get("greeting", "brief")
        e = lib.evidence(r, lib.pick(r))
    assert e.state == state, e
    if verdict:
        assert e.verdict == verdict


def test_a_card_for_other_files_is_stale_after_a_release(setup):
    repo, proj, _ = setup
    md = repo / "library/greeting/variants/brief/greeting/SKILL.md"
    md.write_text(md.read_text().replace("Say hello", "Say hi"))
    note(repo / "library/greeting/variants/brief", "- Shorter.")
    release(repo / "library", "greeting", "brief", "patch")
    os.rename(
        repo / "library/greeting/variants/brief/evidence/1.0.0",
        repo / "library/greeting/variants/brief/evidence/1.0.1",
    )
    commit(repo, "move the old card")
    with lib_for(repo) as lib:
        r = lib.get("greeting", "brief")
        e = lib.evidence(r, lib.pick(r))
        assert e.state == "stale" and e.verdict == "hurts"
        p = inst.plan(lib, inst.project(proj), Lock(proj / "x.json"), "greeting", "brief")
        assert p.refused is None
        assert any("says hurts, but it was made for other files" in w for w in p.warnings)


def test_reinstalling_the_same_files_is_a_no_op_and_a_new_variant_needs_the_diff(setup):
    repo, proj, cfg = setup
    base = ["library", "install", "greeting", "--config", str(cfg), "--project", str(proj)]
    assert run(base)[0] == 0
    assert run(base)[0] == 0
    code, text = run(base + ["--variant", "formal"])
    assert code == 1
    assert "would change" in text and "-Say hello warmly." in text and "+Say good day" in text
    assert "--yes" in text
    assert "warmly." in (proj / ".agents/skills/greeting/SKILL.md").read_text()
    code, text = run(base + ["--variant", "formal", "--yes"])
    assert code == 0
    lock = json.loads((proj / "mordecai-lock.json").read_text())
    assert lock["installed"][".agents/skills/greeting"]["variant"] == "formal"
    assert len(lock["installed"]) == 1  # one active variant per target


def test_update_shows_the_diff_and_needs_yes(setup):
    repo, proj, cfg = setup
    first = git(repo, "rev-list", "-n1", "skill/greeting@1.0.0").strip()
    args = ["--config", str(cfg), "--project", str(proj)]
    assert run(["library", "install", "greeting", "--version", "1.0.0", *args])[0] == 0
    code, text = run(["library", "update", *args])
    assert code == 1
    assert "1.0.0 -> 1.1.0 (helps)" in text and "+Say hello warmly." in text
    assert "Nothing was changed" in text
    lock = json.loads((proj / "mordecai-lock.json").read_text())
    assert lock["installed"][".agents/skills/greeting"]["commit"] == first
    code, text = run(["library", "update", "--yes", *args])
    assert code == 0, text
    assert "warmly" in (proj / ".agents/skills/greeting/SKILL.md").read_text()
    code, text = run(["library", "update", *args])
    assert code == 0 and "up to date (1.1.0)" in text


def test_edited_installs_are_never_replaced_or_removed_silently(setup):
    repo, proj, cfg = setup
    args = ["--config", str(cfg), "--project", str(proj)]
    run(["library", "install", "greeting", "--version", "1.0.0", *args])
    md = proj / ".agents/skills/greeting/SKILL.md"
    md.write_text(md.read_text() + "my edit\n")
    code, text = run(["library", "update", "--yes", *args])
    assert code == 1 and "has changed since Mordecai installed it" in text
    assert "my edit" in md.read_text()
    code, text = run(["library", "status", *args])
    assert "install-changed" in text
    at = ["--project", str(proj)]
    assert run(["library", "uninstall", "greeting", *at])[0] == 2
    assert md.exists()
    code, text = run(["library", "uninstall", "greeting", "--force", *at])
    assert code == 0 and not md.parent.exists()
    assert json.loads((proj / "mordecai-lock.json").read_text())["installed"] == {}


def test_install_never_touches_another_tools_folder(setup, capsys):
    repo, proj, cfg = setup
    other = proj / ".agents/skills/greeting"
    other.mkdir(parents=True)
    (other / "SKILL.md").write_text("from npx skills\n")
    code, _ = run(["library", "install", "greeting", "--config", str(cfg), "--project", str(proj)])
    assert code == 2
    assert "Mordecai didn't install it" in capsys.readouterr().err
    assert (other / "SKILL.md").read_text() == "from npx skills\n"
    link = proj / ".claude/skills/greeting"
    link.parent.mkdir(parents=True)
    link.symlink_to(other)
    code, _ = run(
        [
            "library",
            "install",
            "greeting",
            "--target",
            "claude",
            "--config",
            str(cfg),
            "--project",
            str(proj),
        ]
    )
    assert code == 2


@pytest.mark.parametrize("target", ["../outside", "/tmp", ".", "sub/../../out"])
def test_targets_must_stay_inside_the_project(setup, target):
    repo, proj, cfg = setup
    code, _ = run(
        [
            "library",
            "install",
            "greeting",
            "--target",
            target,
            "--config",
            str(cfg),
            "--project",
            str(proj),
        ]
    )
    assert code == 2
    assert not (proj.parent / "outside").exists()


def test_a_target_through_a_link_is_refused(setup):
    repo, proj, cfg = setup
    elsewhere = proj.parent / "elsewhere"
    elsewhere.mkdir()
    (proj / ".agents").symlink_to(elsewhere)
    code, _ = run(["library", "install", "greeting", "--config", str(cfg), "--project", str(proj)])
    assert code == 2
    assert list(elsewhere.iterdir()) == []


def test_a_path_target_inside_the_project_works(setup):
    repo, proj, cfg = setup
    code, _ = run(
        [
            "library",
            "install",
            "greeting",
            "--target",
            "tools/skills",
            "--config",
            str(cfg),
            "--project",
            str(proj),
        ]
    )
    assert code == 0
    assert (proj / "tools/skills/greeting/SKILL.md").is_file()


def test_a_source_with_a_link_or_traversal_in_a_skill_is_refused(setup, capsys):
    repo, proj, cfg = setup
    folder = repo / "library/greeting/base/greeting"
    (folder / "escape").symlink_to("../../../../../etc/passwd")
    note(repo / "library/greeting/base", "- Link.")
    commit(repo, "a link")
    git(repo, "tag", "-a", "skill/greeting@1.2.0", "-m", "x")
    log = repo / "library/greeting/base/CHANGELOG.md"
    log.write_text(
        log.read_text().replace("## Unreleased", "## Unreleased\n\n## 1.2.0 - 2026-10-06", 1)
    )
    commit(repo, "bump")
    git(repo, "tag", "-f", "-a", "skill/greeting@1.2.0", "-m", "x")
    code, text = run(
        ["library", "install", "greeting", "--config", str(cfg), "--project", str(proj)]
    )
    assert code == 2
    assert "symbolic link" in capsys.readouterr().err
    assert not (proj / ".agents/skills/greeting").exists()
    from mordecai.library import gitio

    with pytest.raises(LibraryError):
        gitio.safe_path("../x")
    for bad in ("/etc/x", "a/../b", ".git/config", "a\x1bb", "a\\b"):
        with pytest.raises(LibraryError):
            gitio.safe_path(bad)


def test_malformed_skill_at_the_version_is_refused(setup):
    repo, proj, cfg = setup
    md = repo / "library/greeting/base/greeting/SKILL.md"
    md.write_text("---\nname: greeting\n---\nno description\n")
    note(repo / "library/greeting/base", "- Broke it.")
    with pytest.raises(LibraryError):
        release(repo / "library", "greeting", None, "patch")
    commit(repo, "broken but committed")
    with lib_for(repo) as lib:
        # The newest release is still the good 1.1.0, so install works...
        p = inst.plan(lib, inst.project(proj), Lock(proj / "x.json"), "greeting")
        assert str(p.picked.version) == "1.1.0"


def test_scripts_get_a_warning(setup):
    repo, proj, cfg = setup
    folder = repo / "library/greeting/base/greeting"
    (folder / "scripts").mkdir()
    (folder / "scripts/run.sh").write_text("echo hi\n")
    (folder / "scripts/run.sh").chmod(0o755)
    note(repo / "library/greeting/base", "- A script.")
    release(repo / "library", "greeting", None, "minor")
    code, text = run(
        ["library", "install", "greeting", "--config", str(cfg), "--project", str(proj)]
    )
    assert code == 0
    assert "never runs them" in text and "your permissions" in text
    installed = proj / ".agents/skills/greeting/scripts/run.sh"
    assert os.stat(installed).st_mode & 0o111
    assert hash_dir(installed.parent.parent) == hash_dir(folder)


def test_user_installs_go_under_home_with_their_own_lock(setup, monkeypatch, gitenv):
    repo, proj, cfg = setup
    home = gitenv / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    code, _ = run(
        ["library", "install", "greeting", "--user", "--target", "github", "--config", str(cfg)]
    )
    assert code == 0
    assert (home / ".copilot/skills/greeting/SKILL.md").is_file()
    lock = gitenv / "xdg-state" / "mordecai" / "lock.json"
    assert ".copilot/skills/greeting" in json.loads(lock.read_text())["installed"]


def test_a_malformed_lockfile_is_refused(setup):
    repo, proj, cfg = setup
    (proj / "mordecai-lock.json").write_text('{"lockfileVersion": 1, "installed": {"x": {}}}')
    code, _ = run(["library", "install", "greeting", "--config", str(cfg), "--project", str(proj)])
    assert code == 2
    (proj / "mordecai-lock.json").write_text(
        '{"lockfileVersion": 1, "installed": {"../../x": '
        + json.dumps(
            {
                k: v
                for k, v in {
                    "skill": "greeting",
                    "variant": None,
                    "version": "1.0.0",
                    "tag": None,
                    "source": {},
                    "commit": None,
                    "path": "p",
                    "hash": "h",
                    "verdict": "v",
                    "evidence": "e",
                    "allowed": [],
                }.items()
            }
        )
        + "}}"
    )
    code, _ = run(["library", "uninstall", "greeting", "--project", str(proj)])
    assert code == 2


def test_status_reports_behind_base_blocked_and_unmeasured(setup):
    repo, proj, cfg = setup
    code, text = run(["library", "status", "--config", str(cfg), "--project", str(proj)])
    assert code == 1
    assert "behind-base" in text and "based on base 1.0.0; the base is at 1.1.0" in text
    assert "blocked" in text and "brief" in text
    assert "unmeasured" in text and "formal" in text


def test_list_shows_verdicts_and_lineage(setup):
    repo, proj, cfg = setup
    code, text = run(["library", "list", "--config", str(cfg)])
    assert code == 0
    lines = {
        line.split()[1] if line.startswith("  variant") else line.split()[0]: line
        for line in text.splitlines()
        if line.startswith("  ")
    }
    assert "helps" in lines["base"]
    assert "hurts" in lines["brief"]
    assert "behind base 1.1.0" in lines["formal"]
