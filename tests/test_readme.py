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


def _slugs(text: str) -> set[str]:
    """GitHub's heading anchors: lowercase, punctuation dropped, spaces as hyphens, and -1, -2
    on repeats."""
    seen: dict[str, int] = {}
    out = set()
    for heading in re.findall(r"^#{1,6} (.+)$", text, re.M):
        slug = re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")
        n = seen.get(slug, 0)
        seen[slug] = n + 1
        out.add(slug if n == 0 else f"{slug}-{n}")
    return out


def test_every_anchor_link_in_the_readme_has_a_heading():
    links = set(re.findall(r"\]\(#([^)]+)\)", README))
    assert links and links <= _slugs(README), links - _slugs(README)


def test_the_readme_links_all_four_sibling_tools():
    for tool in ("loupe", "parallax", "isr", "polarizer"):
        assert f"https://github.com/mpwilso/{tool})" in README


def test_no_em_or_en_dashes_in_the_readme_and_library_docs():
    docs = [
        "README.md",
        "examples/README.md",
        "docs/research.md",
        "docs/library-design.md",
        "docs/library-demo.md",
        "docs/decisions.md",
        "docs/build-log.md",
    ]
    for doc in docs:
        text = (ROOT / doc).read_text(encoding="utf-8")
        assert chr(0x2014) not in text and chr(0x2013) not in text, doc


def test_every_relative_link_and_image_resolves():
    """Links and images in the README and the docs lead to files that exist; a #fragment on a
    Markdown file must be one of its headings."""
    docs = [ROOT / "README.md", ROOT / "CHANGELOG.md", ROOT / "examples" / "README.md"]
    docs += sorted((ROOT / "docs").glob("*.md"))
    bad = []
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        targets = re.findall(r"\]\(([^)\s]+)\)", text) + re.findall(
            r'(?:src|srcset)="([^"]+)"', text
        )
        for target in targets:
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            path, _, fragment = target.partition("#")
            resolved = (doc.parent / path).resolve()
            if not resolved.exists():
                bad.append(f"{doc.name}: {target}")
            elif fragment and resolved.suffix == ".md":
                if fragment not in _slugs(resolved.read_text(encoding="utf-8")):
                    bad.append(f"{doc.name}: {target}")
    assert bad == []
