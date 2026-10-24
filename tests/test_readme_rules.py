"""The README keeps to the rules shared across the author's tools: short, no dashes, links that
resolve, no bare placeholders, and no "only", "first" or "best" in its prose. Ported from
Loupe's tests/readme.test.ts; standard library only."""

import re

from conftest import ROOT

README = (ROOT / "README.md").read_text(encoding="utf-8")
EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)
TAGS = {"p", "picture", "source", "img", "b", "details", "summary", "br", "a", "sub", "sup"}
MAX_LINES = 155


def prose(text: str) -> str:
    """The README without code blocks, code spans, HTML comments and quoted lines: what GitHub
    shows as the README's own words and tags."""
    text = re.sub(r"^```.*?^```$", "", text, flags=re.S | re.M)
    text = re.sub(r"`[^`\n]*`", "", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return re.sub(r"^>.*$", "", text, flags=re.M)


def slug(heading: str) -> str:
    """GitHub's heading anchor: lower case, punctuation dropped, spaces to hyphens."""
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def headings(text: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"^#{1,6} (.+)$", prose(text), re.M)]


def problems(text: str, base=ROOT) -> list[str]:
    found = []
    shown = re.sub(r"<details>.*?</details>", "<details></details>", text, flags=re.S)
    lines = shown.count("\n") + (0 if shown.endswith("\n") or not shown else 1)
    if lines >= MAX_LINES:
        found.append(f"{lines} lines; keep it under {MAX_LINES}")
    if EM_DASH in text:
        found.append("an em dash")
    if EN_DASH in text:
        found.append("an en dash")
    slugs = [slug(h) for h in headings(text)]
    for m in re.finditer(r"\]\(([^)\s]+)\)|\b(?:src|srcset|href)=\"([^\"]+)\"", text):
        link = m.group(1) or m.group(2)
        if link.startswith("#"):
            if link[1:] not in slugs:
                found.append(f"an anchor with no heading: {link}")
            continue
        if re.match(r"^(https?:|mailto:)", link):
            continue
        if not (base / re.split(r"[?#]", link)[0]).exists():
            found.append(f"a broken link: {link}")
    words = prose(text)
    for m in re.finditer(r"<(/?)([^\s>/]*)[^>]*>", words):
        if m.group(2).lower() not in TAGS:
            found.append(f"a bare angle-bracket placeholder: {m.group(0)}")
    # Tags drop out of the word check, and an alt text drops out with its tag.
    words = re.sub(r"<[^>]*>", "", words)
    for m in re.finditer(r"\b(only|first|best)\b", words, re.I):
        found.append(f'"{m.group(1)}" in the prose')
    return found


def test_the_readme_passes_every_rule():
    assert problems(README) == []


def test_each_rule_catches_what_it_should(tmp_path):
    assert problems("line\n" * 155, tmp_path) == ["155 lines; keep it under 155"]
    assert problems("<details>\n" + "line\n" * 155 + "</details>\n", tmp_path) == []
    assert problems(
        "## Setup\n\nJump to [setup](#setup) or [the end](#the-end).\n\n```\n## The end\n```\n",
        tmp_path,
    ) == ["an anchor with no heading: #the-end"]
    assert problems("A long pause" + EM_DASH + "then more.\n", tmp_path) == ["an em dash"]
    assert problems("From 2 " + EN_DASH + " 3.\n", tmp_path) == ["an en dash"]
    assert problems(
        'See [the notes](docs/nowhere.md) and <img src="brand/missing.svg">.\n', tmp_path
    ) == ["a broken link: docs/nowhere.md", "a broken link: brand/missing.svg"]
    assert problems("Show the draft under <the reason>.\n", tmp_path) == [
        "a bare angle-bracket placeholder: <the reason>"
    ]
    assert problems("Show the draft under `<the reason>`.\n\n```\n<folder>\n```\n", tmp_path) == []
    assert problems(
        'The first tool, and the best.\n<img src="x.svg" alt="Our only mark">\n', tmp_path
    ) == ["a broken link: x.svg", '"first" in the prose', '"best" in the prose']
    assert problems("```markdown\nFirst question: only the next box?\n```\n", tmp_path) == []
    assert problems("> The first and only quoted line.\n", tmp_path) == []
