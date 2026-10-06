"""Text from a result or card is printed so it can't drive the terminal or forge a line, and the
crawl card's own colors still come through."""

import io
import json
import re
import shutil

from conftest import FIXTURES, make_result, same

from mordecai.card import build
from mordecai.cli import main
from mordecai.render import COLOR, RARITY, UNSAFE, _pts, clean, crawl, markdown, plain
from mordecai.result import parse

ESC = chr(0x1B)
RLO = chr(0x202E)
HOSTILE = f"x{ESC}[2J{ESC}]0;title{chr(7)}\rFAKE: Helps\nnext line{RLO}reversed{chr(0x85)}"


def hostile_card():
    doc = make_result(same(6, [1, 1, 1], [0, 0, 0], fired=[True] * 3), model=HOSTILE)
    doc["suite"]["plugins"][0].update(name=HOSTILE, version=HOSTILE)
    doc["suite"]["judgeModel"] = HOSTILE
    doc["claudeVersion"] = doc["startedAt"] = HOSTILE
    doc["partial"], doc["partialReason"] = True, HOSTILE
    doc["cases"][0]["name"] = HOSTILE
    doc["cases"][0]["promptMarkdown"] = "Use demo-skill."
    return build(parse(doc), b"x", roots=[])


def unsafe_in(text):
    return sorted({hex(ord(c)) for line in text.split("\n") for c in line if ord(c) in UNSAFE})


def test_clean_escapes_controls_and_bidi_marks_and_is_idempotent():
    assert clean(HOSTILE) == (
        "x\\x1b[2J\\x1b]0;title\\x07\\x0dFAKE: Helps\\x0anext line\\u202ereversed\\x85"
    )
    assert clean(clean(HOSTILE)) == clean(HOSTILE)
    assert clean("plain text " + chr(0xB7) + " caf" + chr(0xE9)) == "plain text " + chr(
        0xB7
    ) + " caf" + chr(0xE9)


def test_no_mode_prints_a_control_character_from_the_result():
    card = hostile_card()
    clean_card = build(
        parse(make_result(same(6, [1, 1, 1], [0, 0, 0]), partial=True)), b"x", roots=[]
    )
    for render in (plain, markdown, crawl):
        text = render(card)
        assert unsafe_in(text) == [], render.__name__
        # Nothing in the result added a line: the hostile card has as many as a plain one,
        # apart from the warning about a case prompt naming the skill.
        assert text.count("\n") <= render(clean_card).count("\n") + 1, render.__name__
    assert plain(card).split("\n")[0].endswith(": Invalid")


def test_crawl_keeps_only_its_own_colors():
    card = hostile_card()
    text = crawl(card, color=True)
    codes = re.findall(ESC + r"\[([0-9;]*)m", text)
    assert codes == [COLOR["invalid"], "0"]
    assert text.count(ESC) == 2


def test_every_verdict_gets_its_rarity_color_on_a_terminal():
    """The rarity is colored in crawl mode only when color is on, for every verdict, and the
    colored card is the plain-text crawl card with the color codes added."""
    from test_card import cards

    for verdict, card in cards().items():
        colored, uncolored = crawl(card, color=True), crawl(card)
        change = card.reading.change
        rarity = RARITY[verdict].format(pts=_pts(change) if change is not None else "+0")
        assert f"{ESC}[{COLOR[verdict]}m{rarity}{ESC}[0m" in colored, verdict
        assert re.sub(ESC + r"\[[0-9;]*m", "", colored) == uncolored, verdict
        assert ESC not in uncolored and ESC not in plain(card), verdict


def test_check_lint_and_errors_are_cleaned(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    shutil.copytree(FIXTURES / "probe", tmp_path / "probe")
    out = io.StringIO()
    main(
        ["identify", str(FIXTURES / "probe-result.json"), "--skill", "probe", "--card", "c.json"],
        out=out,
    )
    doc = json.loads((tmp_path / "c.json").read_text())
    doc["tested"]["model"] = HOSTILE
    (tmp_path / "c.json").write_text(json.dumps(doc))
    out = io.StringIO()
    assert main(["check", "c.json", "--model", "claude-x"], out=out) == 1
    assert ESC not in out.getvalue() and "\\x1b[2J" in out.getvalue()

    (tmp_path / "probe" / "evals" / "goodbye" / "prompt.md").write_text(
        f"---\nname: {ESC}[2Jevil\nmodel: {ESC}]0;x{chr(7)}\n---\nhello\n"
    )
    out = io.StringIO()
    main(["lint", "probe"], out=out)
    assert ESC not in out.getvalue() and chr(7) not in out.getvalue()

    bad = tmp_path / f"bad{ESC}[2J.json"
    bad.write_text("{")
    assert main(["identify", str(bad)], out=io.StringIO()) == 2
    assert main(["check", str(bad)], out=io.StringIO()) == 2
    assert main(["identify", "x.json", "--fail-on", f"{ESC}[2J"], out=io.StringIO()) == 2
    assert ESC not in capsys.readouterr().err
