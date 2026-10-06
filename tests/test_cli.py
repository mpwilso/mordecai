import io
import json
import shutil

from conftest import FIXTURES, ROOT, make_result, same

from mordecai.cli import main


def run(argv):
    out = io.StringIO()
    code = main(argv, out=out)
    return code, out.getvalue()


def test_identify_prints_the_card_and_writes_files(tmp_path):
    card, md = tmp_path / "card.json", tmp_path / "card.md"
    code, text = run(
        [
            "identify",
            str(FIXTURES / "probe-result.json"),
            "--skill",
            str(FIXTURES / "probe"),
            "--card",
            str(card),
            "--markdown",
            str(md),
        ]
    )
    assert code == 0
    assert text.startswith("schema-probe 0.0.1: Inconclusive\n")
    assert json.loads(card.read_text())["verdict"] == "inconclusive"
    assert md.read_text().startswith("### schema-probe 0.0.1: Inconclusive")


def test_fail_on(tmp_path):
    result = tmp_path / "r.json"
    result.write_text(json.dumps(make_result(same(6, [0, 0, 0], [1, 1, 1]))))
    assert run(["identify", str(result), "--fail-on", "hurts,invalid"])[0] == 1
    assert run(["identify", str(result), "--fail-on", "invalid"])[0] == 0
    assert run(["identify", str(result), "--fail-on", "bad"])[0] == 2


def test_crawl_mode_off_a_terminal_has_no_animation_or_color(monkeypatch):
    monkeypatch.setenv("MORDECAI_MODE", "crawl")
    code, text = run(["identify", str(FIXTURES / "probe-result.json")])
    assert code == 0
    assert text.startswith("NEW ACHIEVEMENT!")
    assert "\033[" not in text and "\r" not in text


def test_unreadable_result():
    code, _ = run(["identify", str(ROOT / "pyproject.toml")])
    assert code == 2


def test_check(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    probe = tmp_path / "probe"
    shutil.copytree(FIXTURES / "probe", probe)
    card = tmp_path / "card.json"
    run(
        [
            "identify",
            str(FIXTURES / "probe-result.json"),
            "--skill",
            str(probe),
            "--card",
            str(card),
        ]
    )
    assert run(["check", str(card)])[0] == 0
    (probe / "skills" / "team-signoff" / "SKILL.md").write_text("changed")
    code, text = run(["check", str(card)])
    assert code == 1
    assert "The skill's files changed" in text
    assert run(["check", str(tmp_path / "missing.json")])[0] == 2


def test_check_model_on_the_suite_2_pair():
    """The worked example: suite 2's skill measured on Haiku 4.5 and on Sonnet 5.5. Both cards
    match the files, so only --model can tell them apart."""
    cards = ROOT / "docs" / "planted-results"
    haiku, sonnet = cards / "2-commits.card.json", cards / "2-commits-sonnet.card.json"
    assert run(["check", str(haiku)])[0] == 0
    assert run(["check", str(sonnet)])[0] == 0
    code, text = run(["check", str(haiku), "--model", "claude-sonnet-5-5"])
    assert code == 1
    assert "The card was measured on claude-haiku-4-5-20251001, not claude-sonnet-5-5." in text
    assert run(["check", str(sonnet), "--model", "claude-sonnet-5-5"])[0] == 0
    assert run(["check", str(haiku), "--model", "claude-haiku-4-5-20251001"])[0] == 0
