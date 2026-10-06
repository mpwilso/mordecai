"""Results, cards and skill directories may come from someone else. Paths read from them must
lead inside the current directory or one the user named, and the directory hash never follows a
link, so a crafted file can't make Mordecai read or hang on anything outside."""

import io
import json
import os
import shutil

import pytest
from conftest import FIXTURES, make_result, same

from mordecai.card import CardError, build, check, to_json
from mordecai.cli import main
from mordecai.provenance import PathError, hash_cases, hash_dir
from mordecai.result import load, parse


def run(argv):
    return main(argv, out=io.StringIO())


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A working directory holding the probe plugin and its card, with a secret outside it."""
    work = tmp_path / "work"
    shutil.copytree(FIXTURES / "probe", work / "probe")
    (tmp_path / "outside").mkdir()
    (tmp_path / "outside" / "secret.txt").write_text("secret")
    monkeypatch.chdir(work)
    assert (
        run(
            [
                "identify",
                str(FIXTURES / "probe-result.json"),
                "--skill",
                "probe",
                "--card",
                "card.json",
            ]
        )
        == 0
    )
    return work


def edit_card(path, **paths):
    doc = json.loads(path.read_text())
    doc["paths"].update(paths)
    path.write_text(json.dumps(doc))


@pytest.mark.parametrize("skill", ["../outside", "{outside}", "../../../../../../../../etc"])
def test_check_refuses_a_card_whose_skill_leads_outside(repo, skill, capsys):
    edit_card(repo / "card.json", skill=skill.format(outside=repo.parent / "outside"))
    assert run(["check", "card.json"]) == 2
    err = capsys.readouterr().err
    assert "leads outside" in err and "--skill" in err


@pytest.mark.parametrize(
    "case_dir", ["../../outside", "/etc", "C:\\\\Windows", "evals/../../x", "."]
)
def test_check_refuses_case_dirs_that_leave_the_suite(repo, case_dir, capsys):
    edit_card(repo / "card.json", caseDirs=[case_dir])
    assert run(["check", "card.json"]) == 2
    assert "isn't a relative path inside the suite" in capsys.readouterr().err


def test_check_still_reads_a_skill_passed_on_the_command_line(repo, tmp_path):
    """--skill is the user's own choice, so it may be anywhere."""
    moved = tmp_path / "moved"
    shutil.move(str(repo / "probe"), str(moved))
    assert run(["check", "card.json"]) == 1
    assert run(["check", "card.json", "--skill", str(moved)]) == 0


def test_a_card_with_wrong_types_is_refused(repo, capsys):
    for change in (
        {"paths": "x"},
        {"hashes": {"skill": 5}},
        {"paths": {"caseDirs": "evals/goodbye"}},
        {"tested": {"model": ["a"]}},
    ):
        doc = json.loads((repo / "card.json").read_text())
        doc.update(change)
        (repo / "bad.json").write_text(json.dumps(doc))
        assert run(["check", "bad.json"]) == 2
        assert "should be" in capsys.readouterr().err
    with pytest.raises(CardError, match="not a Mordecai card"):
        check([1, 2])


def test_identify_refuses_a_result_whose_paths_lead_outside(tmp_path, monkeypatch, capsys):
    outside = tmp_path / "outside"
    shutil.copytree(FIXTURES / "probe", outside)
    (tmp_path / "work").mkdir()
    monkeypatch.chdir(tmp_path / "work")
    doc = make_result(same(6, [1, 1, 1], [0, 0, 0]), plugin_path=str(outside))
    (tmp_path / "r.json").write_text(json.dumps(doc))
    assert run(["identify", str(tmp_path / "r.json")]) == 2
    assert "The result's plugin path" in capsys.readouterr().err
    # Naming the plugin directory yourself is allowed, and so is a root inside it.
    assert run(["identify", str(tmp_path / "r.json"), "--skill", str(outside)]) == 0
    # A plugin path that doesn't exist is never read, so it only warns, as before.
    doc["suite"]["root"] = doc["suite"]["plugins"][0]["path"] = str(tmp_path / "gone")
    (tmp_path / "r.json").write_text(json.dumps(doc))
    assert run(["identify", str(tmp_path / "r.json")]) == 0


def test_identify_refuses_case_dirs_that_leave_the_suite(tmp_path, capsys):
    doc = make_result(same(6, [1, 1, 1], [0, 0, 0]))
    for case in doc["cases"]:
        case["dir"] = "../../../../../../etc"
    (tmp_path / "r.json").write_text(json.dumps(doc))
    assert run(["identify", str(tmp_path / "r.json"), "--skill", str(FIXTURES / "probe")]) == 2
    assert "isn't a relative path inside the suite" in capsys.readouterr().err


def test_a_case_dir_that_is_a_link_out_of_the_suite_is_refused(tmp_path):
    (tmp_path / "suite" / "evals").mkdir(parents=True)
    (tmp_path / "elsewhere").mkdir()
    os.symlink(tmp_path / "elsewhere", tmp_path / "suite" / "evals" / "c")
    with pytest.raises(PathError, match="leads outside"):
        hash_cases(tmp_path / "suite", ["evals/c"])


def test_links_are_hashed_as_links_and_never_followed(tmp_path):
    skill = tmp_path / "skill"
    shutil.copytree(FIXTURES / "probe", skill)
    target = tmp_path / "outside.txt"
    target.write_text("one")
    link = skill / "skills" / "team-signoff" / "shared.md"
    os.symlink(target, link)
    before = hash_dir(skill)
    # The target's contents don't matter, and it needn't even exist: it is never opened.
    target.write_text("two")
    assert hash_dir(skill) == before
    target.unlink()
    assert hash_dir(skill) == before
    # Pointing the link somewhere else does change the hash.
    link.unlink()
    os.symlink(tmp_path / "other.txt", link)
    assert hash_dir(skill) != before


def test_a_link_to_a_parent_directory_is_not_walked(tmp_path):
    skill = tmp_path / "skill"
    shutil.copytree(FIXTURES / "probe", skill)
    os.symlink("..", skill / "skills" / "loop")
    os.symlink("/", skill / "root")
    assert hash_dir(skill).startswith("sha256:")


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs named pipes")
def test_a_pipe_is_left_out_and_never_opened(tmp_path):
    skill = tmp_path / "skill"
    shutil.copytree(FIXTURES / "probe", skill)
    before = hash_dir(skill)
    os.mkfifo(skill / "pipe")
    assert hash_dir(skill) == before


def test_a_skill_without_links_hashes_as_it_always_has():
    """The recorded cards' hashes don't move: the probe's skill hash is the one in the README."""
    suite, data = load(FIXTURES / "probe-result.json")
    card = build(suite, data, FIXTURES / "probe")
    assert card.skill_hash.startswith("sha256:c9b400d7538f")
    assert card.cases_hash.startswith("sha256:a5b22319b5ee")


def test_build_and_check_take_explicit_roots(tmp_path):
    skill = tmp_path / "skill"
    shutil.copytree(FIXTURES / "probe", skill)
    doc = make_result(same(6, [1, 1, 1], [0, 0, 0]), plugin_path=str(skill))
    card = build(parse(doc), b"x", roots=[tmp_path])
    assert card.skill_hash is not None
    with pytest.raises(PathError):
        build(parse(doc), b"x", roots=[tmp_path / "elsewhere"])
    saved = json.loads(to_json(card, tmp_path))
    # The builder's case directories aren't on disk, so only the skill can be checked.
    assert check(saved, tmp_path, roots=[tmp_path]) == [
        "The card has no cases hash, so it can't be checked."
    ]
    with pytest.raises(PathError):
        check(saved, tmp_path, roots=[tmp_path / "elsewhere"])
