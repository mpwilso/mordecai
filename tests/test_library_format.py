"""Names, versions, tags, changelogs and SKILL.md frontmatter, including input written to break
them."""

import pytest

pytest.importorskip("strictyaml")

from mordecai.library import LibraryError  # noqa: E402
from mordecai.library import changelog as cl  # noqa: E402
from mordecai.library.skillmd import check_folder, frontmatter, set_stamps  # noqa: E402
from mordecai.library.versions import (  # noqa: E402
    Version,
    check_name,
    parse_tag,
    parse_version,
    tag_name,
)


@pytest.mark.parametrize("name", ["a", "pr-description", "x1-2y", "a" * 64])
def test_valid_names(name):
    assert check_name(name) == name


@pytest.mark.parametrize(
    "name", ["", "A", "-a", "a-", "a--b", "a_b", "a.b", "a" * 65, "../x", "caf" + chr(0xE9), 3]
)
def test_invalid_names(name):
    with pytest.raises(LibraryError):
        check_name(name)


def test_base_is_not_a_variant_name():
    with pytest.raises(LibraryError, match="reserved"):
        check_name("base", "variant")


def test_versions_order_and_bump():
    v = parse_version("1.9.3")
    assert v < parse_version("1.10.0")
    assert str(v.bump("patch")) == "1.9.4"
    assert str(v.bump("minor")) == "1.10.0"
    assert str(v.bump("major")) == "2.0.0"
    for bad in ("1.0", "01.0.0", "1.0.0-rc1", "v1.0.0", " 1.0.0", None):
        with pytest.raises(LibraryError):
            parse_version(bad)


def test_tags_round_trip_and_stay_out_of_v_globs():
    assert tag_name("vue-tools", None, Version(1, 2, 0)) == "skill/vue-tools@1.2.0"
    assert tag_name("pr", "mobile", Version(0, 1, 0)) == "skill/pr.mobile@0.1.0"
    assert parse_tag("skill/pr.mobile@0.1.0") == ("pr", "mobile", Version(0, 1, 0))
    assert parse_tag("skill/pr@2.0.0") == ("pr", None, Version(2, 0, 0))
    for other in ("v0.3.0", "skill/pr.base@1.0.0", "skill/Pr@1.0.0", "skill/pr@1.0", "pr@1.0.0"):
        assert parse_tag(other) is None
    import fnmatch

    # GitHub's tag filters don't let * match /, which fnmatch on each part models.
    assert not fnmatch.fnmatch("skill/vue-tools@1.2.0".split("/")[0], "v*")


def test_tags_are_valid_git_refs():
    import subprocess

    for tag in ("skill/pr.mobile@0.1.0", "skill/vue-tools@10.20.30"):
        subprocess.run(["git", "check-ref-format", f"refs/tags/{tag}"], check=True)


VARIANT_LOG = """# Changelog

## Unreleased

Based on base 1.2.0.

- Pending.

## 1.1.0 - 2026-10-06

Based on base 1.2.0.

- Shorter.

## 1.0.0 - 2026-10-01

Based on base 1.0.0.

- First.
"""


def test_changelog_round_trips_and_reports_versions():
    log = cl.parse(VARIANT_LOG, variant=True)
    assert str(log.version) == "1.1.0"
    assert str(log.based_on) == "1.2.0"
    assert log.unreleased.notes == ("- Pending.",)
    assert cl.render(log) == VARIANT_LOG
    assert cl.parse("# Changelog\n", variant=False).version == parse_version("0.0.0")


@pytest.mark.parametrize(
    "text,match",
    [
        ("Changelog\n", "should start"),
        ("# Changelog\n\n## 1.0 - 2026-10-01\n", "in the heading"),
        ("# Changelog\n\n## 1.0.0 - 2026-13-01\n", "isn't a date"),
        ("# Changelog\n\n## 1.0.0 - 2026-10-01\n\n## 1.1.0 - 2026-10-02\n", "newest first"),
        ("# Changelog\n\n## 1.0.0 - 2026-10-01\n\n## Unreleased\n", "Unreleased must"),
        ("# Changelog\n\n### deeper\n", "only ##"),
        ("# Changelog\nstray\n", "before the first"),
        ("# Changelog\n\n## 1.0.0 - 2026-10-01\n\nBased on base 1.0.0.\n", "base's changelog"),
    ],
)
def test_bad_base_changelogs(text, match):
    with pytest.raises(LibraryError, match=match):
        cl.parse(text, variant=False)


def test_a_variant_section_must_say_its_base():
    with pytest.raises(LibraryError, match="Based on base"):
        cl.parse("# Changelog\n\n## 1.0.0 - 2026-10-01\n\n- First.\n", variant=True)


def test_cut_release_needs_notes():
    log = cl.parse("# Changelog\n\n## Unreleased\n", variant=False)
    with pytest.raises(LibraryError, match="nothing to release"):
        cl.cut_release(log, Version(1, 0, 0), "2026-10-06", None, [])
    new = cl.cut_release(log, Version(1, 0, 0), "2026-10-06", None, ["Added it."])
    assert new.releases[0].notes == ("- Added it.",)
    assert cl.parse(cl.render(new), variant=False).version == Version(1, 0, 0)


def make(tmp_path, text, name="demo", extra=None):
    folder = tmp_path / name
    folder.mkdir()
    (folder / "SKILL.md").write_text(text)
    for rel, data in (extra or {}).items():
        (folder / rel).parent.mkdir(parents=True, exist_ok=True)
        (folder / rel).write_text(data)
    return folder


GOOD = "---\nname: demo\ndescription: Use when demoing.\n---\n\nDo the demo.\n"


def test_a_good_folder(tmp_path):
    r = check_folder(make(tmp_path, GOOD), "demo")
    assert r.errors == [] and r.warnings == []
    assert r.files == ["SKILL.md"]


@pytest.mark.parametrize(
    "text,match",
    [
        ("name: demo\n", "should start"),
        ("---\nname: demo\ndescription: x\n", "no closing"),
        ("---\nname: other\ndescription: x\n---\nbody\n", "doesn't match its folder"),
        ("---\nname: Demo\ndescription: x\n---\nbody\n", "isn't valid"),
        ("---\nname: demo\n---\nbody\n", "no description"),
        ("---\nname: demo\ndescription: " + "x" * 1025 + "\n---\nbody\n", "1 to 1024"),
        ("---\nname: demo\ndescription: [a, b]\n---\nbody\n", "validator accepts"),
        ("---\nname: demo\nname: demo\ndescription: x\n---\nbody\n", "validator accepts"),
        ("---\nname: &a demo\ndescription: *a\n---\nbody\n", "validator accepts"),
        ("---\nname: demo\ndescription: !!str x\n---\nbody\n", "validator accepts"),
        ("---\n- a\n- b\n---\nbody\n", "key: value"),
        ("---\nname: demo\ndescription: x\nmetadata:\n  a:\n    b: c\n---\nb\n", "nothing nested"),
        ("---\nname: demo\ndescription: x\ncompatibility: ''\n---\nb\n", "1 to 500"),
    ],
)
def test_bad_frontmatter(tmp_path, text, match):
    r = check_folder(make(tmp_path, text), "demo")
    assert any(match in e for e in r.errors), r.errors


def test_unknown_fields_and_long_files_warn(tmp_path):
    text = GOOD.replace("---\n\n", "when_to_use: often\n---\n\n") + "line\n" * 600
    r = check_folder(make(tmp_path, text), "demo")
    assert r.errors == []
    assert any("outside the spec" in w for w in r.warnings)
    assert any("under 500" in w for w in r.warnings)


def test_links_and_odd_names_are_refused(tmp_path):
    folder = make(tmp_path, GOOD)
    (tmp_path / "secret").write_text("x")
    (folder / "link.md").symlink_to(tmp_path / "secret")
    (folder / "bad\x1bname").write_text("x")
    r = check_folder(folder, "demo")
    assert any("symbolic link" in e for e in r.errors)
    assert any("control character" in e for e in r.errors)


def test_a_folder_that_is_a_link_is_refused(tmp_path):
    real = make(tmp_path, GOOD, name="real")
    (tmp_path / "demo").symlink_to(real)
    assert check_folder(tmp_path / "demo", "demo").errors


def test_file_count_limit(tmp_path, monkeypatch):
    import mordecai.library.skillmd as sm

    monkeypatch.setattr(sm, "MAX_FILES", 3)
    folder = make(tmp_path, GOOD, extra={f"r/{i}.md": "x" for i in range(5)})
    with pytest.raises(LibraryError, match="more than 3 files"):
        check_folder(folder, "demo")


def test_scripts_are_flagged(tmp_path):
    r = check_folder(make(tmp_path, GOOD, extra={"scripts/run.sh": "echo"}), "demo")
    assert r.executable


def test_set_stamps_rewrites_and_adds_only_metadata():
    text = '---\nname: demo\ndescription: d\nmetadata:\n  owner: "me"\n  mordecai-version: "1.0.0"\n---\n\nBody\n'
    out = set_stamps(text, {"mordecai-version": "1.1.0", "mordecai-variant": "fast"})
    fields, body = frontmatter(out)
    assert fields["metadata"] == {
        "owner": "me",
        "mordecai-version": "1.1.0",
        "mordecai-variant": "fast",
    }
    assert body == "Body\n"
    with pytest.raises(LibraryError, match="no metadata"):
        set_stamps(GOOD, {"mordecai-version": "1.0.0"})
