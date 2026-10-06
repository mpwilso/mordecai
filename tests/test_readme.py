"""The README's example cards are what the tool prints for the commands shown above them."""

import io
import json
import re

from conftest import ROOT

from mordecai.cli import main

README = (ROOT / "README.md").read_text(encoding="utf-8")


def examples() -> list[tuple[list[str], str]]:
    blocks = re.findall(r"```\n\$ uv run mordecai (identify [^\n]+)\n(.*?)\n```", README, re.S)
    return [(cmd.split(), shown + "\n") for cmd, shown in blocks]


def printed(argv: list[str], monkeypatch) -> str:
    monkeypatch.chdir(ROOT)
    out = io.StringIO()
    assert main(argv, out=out) == 0
    return out.getvalue()


def test_the_planted_card_is_printed_exactly(monkeypatch):
    argv, shown = examples()[0]
    assert argv == [
        "identify",
        "tests/fixtures/suite1-result.json",
        "--skill",
        "evals/planted/1-convention",
    ]
    assert printed(argv, monkeypatch) == shown
    assert shown.startswith("planted-convention 1.0.0: Helps\n")


def test_the_probe_card_is_the_start_of_what_the_tool_prints(monkeypatch):
    """Only its warnings are cut, as the README says."""
    argv, shown = examples()[1]
    assert argv[1] == "tests/fixtures/probe-result.json"
    assert printed(argv, monkeypatch).startswith(shown + "\nWarnings\n")
    assert "Its warnings are cut here." in README


def test_the_planted_card_matches_the_recorded_one_but_for_the_result_hash(monkeypatch):
    """The fixture is suite 1's raw result with local paths replaced."""
    recorded = json.loads((ROOT / "docs/planted-results/1-convention.card.json").read_text())
    shown = examples()[0][1]
    for key in ("skill", "cases"):
        assert recorded["hashes"][key][:19] in shown
    assert recorded["hashes"]["result"][:19] not in shown
    assert recorded["hashes"]["result"][7:19] in README
    assert recorded["verdict"] == "helps"
