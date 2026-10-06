"""Releasing and forking in a library repository, validating it, and reading libraries from
several sources: config, precedence, refs, tags and GitHub (through a local remote)."""

import io
import json

import pytest

pytest.importorskip("strictyaml")

from libkit import commit, git, greeting_library, init, note, write_copy  # noqa: E402

from mordecai.cli import main  # noqa: E402
from mordecai.library import LibraryError, catalog, gitio  # noqa: E402
from mordecai.library.release import fork, release  # noqa: E402
from mordecai.library.sources import Library, load_config, parse_config  # noqa: E402


def run(argv, cwd=None, monkeypatch=None):
    if monkeypatch and cwd:
        monkeypatch.chdir(cwd)
    out = io.StringIO()
    code = main(argv, out=out)
    return code, out.getvalue()


def test_release_writes_the_changelog_commits_and_tags(gitenv):
    repo = init(gitenv / "lib")
    base = write_copy(repo, "greeting", stamps=True)
    commit(repo, "start")
    r = release(repo / "library", "greeting", None, "minor", message="Trailer: yes")
    assert r.tag == "skill/greeting@0.1.0"
    assert git(repo, "rev-parse", "HEAD").strip() == r.commit
    assert git(repo, "cat-file", "-t", r.tag).strip() == "tag"  # annotated
    log = (base / "CHANGELOG.md").read_text()
    assert "## 0.1.0 - " in log and "- First version." in log
    assert 'mordecai-version: "0.1.0"' in (base / "greeting" / "SKILL.md").read_text()
    assert "Trailer: yes" in git(repo, "log", "-1", "--format=%B")
    assert git(repo, "status", "--porcelain") == ""
    assert git(repo, "remote") == ""


def test_release_refuses_other_changes_and_empty_notes(gitenv):
    repo = init(gitenv / "lib")
    write_copy(repo, "greeting")
    (repo / "other.txt").write_text("x")
    commit(repo)
    release(repo / "library", "greeting", None, "major")
    (repo / "other.txt").write_text("changed")
    with pytest.raises(LibraryError, match="outside"):
        release(repo / "library", "greeting", None, "patch")
    git(repo, "checkout", "--", "other.txt")
    with pytest.raises(LibraryError, match="nothing to release"):
        release(repo / "library", "greeting", None, "patch")


def test_a_variant_release_needs_a_real_base_release(gitenv):
    repo = greeting_library(gitenv / "lib")
    note(repo / "library/greeting/variants/brief", "- More.")
    with pytest.raises(LibraryError, match="no release 9.9.9"):
        release(repo / "library", "greeting", "brief", "patch", based_on="9.9.9")
    with pytest.raises(LibraryError, match="only for variants"):
        release(repo / "library", "greeting", None, "patch", based_on="1.0.0")


def test_fork_copies_the_released_base_not_the_working_copy(gitenv):
    repo = greeting_library(gitenv / "lib")
    md = repo / "library/greeting/base/greeting/SKILL.md"
    md.write_text(md.read_text().replace("warmly", "UNRELEASED"))
    dest = fork(repo / "library", "greeting", "kids")
    text = (dest / "greeting" / "SKILL.md").read_text()
    assert "warmly" in text and "UNRELEASED" not in text
    assert 'mordecai-based-on: "greeting@1.1.0"' in text
    assert "Based on base 1.1.0." in (dest / "CHANGELOG.md").read_text()
    with pytest.raises(LibraryError, match="already exists"):
        fork(repo / "library", "greeting", "kids")


def test_validate_reports_layout_and_lineage_errors(gitenv, monkeypatch):
    repo = greeting_library(gitenv / "lib")
    code, text = run(["library", "validate"], repo, monkeypatch)
    assert code == 0, text
    assert "3 copies of 1 skills, 0 error(s)" in text
    (repo / "library/greeting/stray").mkdir()
    (repo / "library/greeting/base/notes.txt").write_text("x")
    log = repo / "library/greeting/variants/brief/CHANGELOG.md"
    log.write_text(log.read_text().replace("Based on base 1.1.0.", "Based on base 1.5.0.", 1))
    md = repo / "library/greeting/variants/formal/greeting/SKILL.md"
    md.write_text(md.read_text().replace("name: greeting", "name: greetings"))
    code, text = run(["library", "validate"], repo, monkeypatch)
    assert code == 1
    assert "only base/ and variants/" in text
    assert "only the skill folder, CHANGELOG.md and evidence/" in text
    assert "never released" in text
    assert "doesn't match its folder" in text


def test_validate_checks_stamps_against_the_changelog(gitenv, monkeypatch):
    repo = greeting_library(gitenv / "lib")
    md = repo / "library/greeting/base/greeting/SKILL.md"
    md.write_text(md.read_text().replace('"1.1.0"', '"1.2.0"'))
    code, text = run(["library", "validate"], repo, monkeypatch)
    assert code == 1 and "mordecai-version is '1.2.0'" in text


def config(tmp_path, text):
    path = tmp_path / "mordecai-library.toml"
    path.write_text(text)
    return load_config(path)


def test_config_errors(tmp_path):
    for text, match in [
        ("[[source]]\nname = 'a'\n", "exactly one of"),
        ("[[source]]\nname = 'a'\npath = '.'\ngithub = 'x/y'\n", "exactly one of"),
        ("[[source]]\nname = 'a'\npath = '.'\n[[source]]\nname = 'a'\npath = '.'\n", "two"),
        ("[[source]]\nname = 'a'\npath = '.'\nlibrary = '../x'\n", "relative folder"),
        ("[[source]]\nname = 'A'\npath = '.'\n", "isn't valid"),
        ("[[source]]\nname = 'a'\npath = '.'\ntoken = 'x'\n", "unknown key"),
        ("[policy]\nrefuse = ['bad']\n", "refuse should list"),
        ("[install]\ntargets = ['/etc']\n", "targets should list"),
        ("[variants]\nx = 'Bad'\n", "isn't valid"),
        ("not toml [", "isn't valid TOML"),
    ]:
        with pytest.raises(LibraryError, match=match):
            config(tmp_path, text)


def test_no_config_means_the_current_folder(tmp_path):
    cfg = load_config(None, tmp_path)
    assert [s.path for s in cfg.sources] == [tmp_path]
    assert cfg.refuse == ("hurts", "invalid", "broken")


def test_later_sources_win_per_copy_and_shadowed_copies_are_reported(gitenv, monkeypatch):
    org = greeting_library(gitenv / "org")
    team = init(gitenv / "team")
    write_copy(team, "greeting", "formal", body="Team formal.", based_on="1.1.0")
    write_copy(team, "greeting", "team-only", body="Team only.", based_on="1.1.0")
    (team / "library/greeting/base").mkdir(parents=True, exist_ok=True)
    commit(team)
    cfg = parse_config(
        {"source": [{"name": "org", "path": str(org)}, {"name": "team", "path": str(team)}]},
        None,
        gitenv,
    )
    with Library(cfg) as lib:
        assert lib.get("greeting", None).source.spec.name == "org"
        formal = lib.get("greeting", "formal")
        assert formal.source.spec.name == "team" and formal.shadowed == ["org"]
        assert lib.get("greeting", "brief").source.spec.name == "org"
        assert lib.get("greeting", "team-only").source.spec.name == "team"
        found = catalog.status(lib)
        assert any(f["kind"] == "shadowed" and f["copy"] == "greeting.formal" for f in found)
        assert any(f["kind"] == "layout" and "team" in f["message"] for f in found)
        with pytest.raises(LibraryError, match="has no variant 'nope'"):
            lib.get("greeting", "nope")
        with pytest.raises(LibraryError, match="no source has"):
            lib.get("missing", None)


def test_sources_read_commits_not_working_trees(gitenv):
    repo = greeting_library(gitenv / "lib")
    md = repo / "library/greeting/base/greeting/SKILL.md"
    md.write_text(md.read_text() + "UNCOMMITTED\n")
    cfg = parse_config({"source": [{"name": "s", "path": str(repo)}]}, None, gitenv)
    with Library(cfg) as lib:
        r = lib.get("greeting", None)
        assert "UNCOMMITTED" not in (r.source.root / r.copy.folder / "SKILL.md").read_text()
        assert r.source.sha == git(repo, "rev-parse", "HEAD").strip()


def test_a_ref_caps_the_versions_install_sees(gitenv):
    repo = greeting_library(gitenv / "lib")
    first = git(repo, "rev-list", "-n1", "skill/greeting@1.0.0").strip()
    cfg = parse_config({"source": [{"name": "s", "path": str(repo), "ref": first}]}, None, gitenv)
    with Library(cfg) as lib:
        picked = lib.pick(lib.get("greeting", None))
        assert str(picked.version) == "1.0.0"
        with pytest.raises(LibraryError, match="has no release 1.1.0"):
            lib.pick(lib.get("greeting", None), "1.1.0")


def test_a_tag_whose_changelog_disagrees_is_refused(gitenv):
    repo = greeting_library(gitenv / "lib")
    git(repo, "tag", "-a", "skill/greeting@1.5.0", "-m", "wrong")
    cfg = parse_config({"source": [{"name": "s", "path": str(repo)}]}, None, gitenv)
    with Library(cfg) as lib:
        with pytest.raises(LibraryError, match="won't trust it"):
            lib.pick(lib.get("greeting", None))


def test_untagged_copies_are_read_at_the_ref(gitenv):
    repo = init(gitenv / "lib")
    write_copy(repo, "greeting")
    commit(repo)
    cfg = parse_config({"source": [{"name": "s", "path": str(repo)}]}, None, gitenv)
    with Library(cfg) as lib:
        picked = lib.pick(lib.get("greeting", None))
        assert picked.tag is None and str(picked.version) == "0.0.0"


def test_a_plain_folder_source_is_unpinned(gitenv):
    folder = gitenv / "plain"
    write_copy(folder, "greeting")
    cfg = parse_config({"source": [{"name": "p", "path": str(folder)}]}, None, gitenv)
    with Library(cfg) as lib:
        assert not lib.get("greeting", None).source.pinned
    with pytest.raises(LibraryError, match="needs a Git repository"):
        Library(
            parse_config(
                {"source": [{"name": "p", "path": str(folder), "ref": "main"}]}, None, gitenv
            )
        )


def github_remote(gitenv, monkeypatch):
    """A bare repository standing in for github.com/acme/skills."""
    repo = greeting_library(gitenv / "lib")
    remote = gitenv / "remote" / "acme" / "skills.git"
    remote.parent.mkdir(parents=True)
    git(gitenv, "clone", "--quiet", "--bare", str(repo), str(remote))
    git(remote, "config", "uploadpack.allowAnySHA1InWant", "true")
    monkeypatch.setattr(gitio, "GITHUB", (gitenv / "remote").as_uri())
    return repo, remote


def test_github_sources_fetch_the_ref_and_library_tags(gitenv, monkeypatch):
    repo, _ = github_remote(gitenv, monkeypatch)
    for ref in (None, "main", git(repo, "rev-parse", "HEAD").strip()):
        spec = {"name": "org", "github": "acme/skills"} | ({"ref": ref} if ref else {})
        with Library(parse_config({"source": [spec]}, None, gitenv)) as lib:
            r = lib.get("greeting", "formal")
            assert str(lib.pick(r).version) == "1.0.0"
            assert r.source.sha == git(repo, "rev-parse", "HEAD").strip()
    assert (gitenv / "cache" / "git" / "acme" / "skills.git").is_dir()


def test_github_repo_names_are_checked(gitenv, monkeypatch):
    monkeypatch.setattr(gitio, "GITHUB", (gitenv / "nowhere").as_uri())
    for bad in ("acme", "acme/../x", "-x/y", "a/b/c", "a/b;rm"):
        with pytest.raises(LibraryError):
            gitio.fetch_github(bad, None)
    with pytest.raises(LibraryError, match="will use"):
        gitio.fetch_github("acme/skills", "--upload-pack=evil")


def test_the_token_goes_to_git_in_the_environment_and_nowhere_else(gitenv, monkeypatch):
    secret = "ghp_" + "s3cr3t" * 6
    monkeypatch.setenv("MORDECAI_GITHUB_TOKEN", secret)
    monkeypatch.setattr(gitio, "GITHUB", "https://github.com")
    env = gitio._env(auth=True)
    assert env["GIT_CONFIG_KEY_0"] == "http.https://github.com/.extraheader"
    assert secret not in env["GIT_CONFIG_VALUE_0"]  # base64, inside a header value
    assert not any(secret in v for k, v in env.items() if k != "MORDECAI_GITHUB_TOKEN")
    assert "GIT_CONFIG_COUNT" not in gitio._env(auth=False)
    # A failing fetch's message never carries it.
    monkeypatch.setattr(gitio, "GITHUB", (gitenv / "nowhere").as_uri())
    with pytest.raises(LibraryError) as e:
        gitio.fetch_github("acme/skills", None)
    assert secret not in str(e.value)


def test_the_token_is_never_written_or_printed(gitenv, monkeypatch, capsys):
    secret = "ghp_" + "t0k3n" * 7
    monkeypatch.setenv("GITHUB_TOKEN", secret)
    repo, _ = github_remote(gitenv, monkeypatch)
    cfg = gitenv / "mordecai-library.toml"
    cfg.write_text('[[source]]\nname = "org"\ngithub = "acme/skills"\n')
    proj = gitenv / "proj"
    proj.mkdir()
    for argv in (
        ["library", "list", "--config", str(cfg)],
        ["library", "install", "greeting", "--config", str(cfg), "--project", str(proj)],
        ["library", "status", "--config", str(cfg), "--project", str(proj)],
    ):
        _, text = run(argv)
        assert secret not in text
    assert secret not in capsys.readouterr().err
    assert secret not in (proj / "mordecai-lock.json").read_text()
    for path in (gitenv / "cache").rglob("*"):
        if path.is_file():
            assert secret.encode() not in path.read_bytes()


def test_history_lists_releases_notes_and_lineage(gitenv, monkeypatch):
    repo = greeting_library(gitenv / "lib")
    code, text = run(["library", "history", "greeting", "--json"], repo, monkeypatch)
    assert code == 0
    d = json.loads(text)
    assert [v["version"] for v in d["versions"]] == ["1.1.0", "1.0.0"]
    assert d["versions"][0]["tag"] == "skill/greeting@1.1.0"
    assert d["versions"][0]["notes"] == ["- Warmer."]
    code, text = run(["library", "history", "greeting", "--variant", "formal"], repo, monkeypatch)
    assert "based on base 1.0.0" in text
