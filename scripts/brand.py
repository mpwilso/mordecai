"""Draws Mordecai's logo lockups, the crawl mode card and the social preview.

    uv run python scripts/brand.py          write the files
    uv run python scripts/brand.py --check  exit 1 if a file differs from what this would write
    uv run --group visual python scripts/brand.py --png  also draw docs/brand/social-preview.png

Standard library only, plus Mordecai itself: the crawl card's text is printed by the same code
as `mordecai identify --crawl`, from a demo result built here, so the picture can't say
something the tool wouldn't. The one exception is --png, which renders the social preview in
headless Chromium from the visual dependency group. The PNG carries the hash of the SVG it was
drawn from, so --check can tell it's current without a browser. tests/test_brand.py runs the
check. docs/brand/README.md says what the mark means.
"""

import math
import os
import re
import struct
import sys
import tempfile
import zlib
from hashlib import sha256
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "src"))

from builder import make_result  # noqa: E402

from mordecai.card import build  # noqa: E402
from mordecai.render import crawl  # noqa: E402
from mordecai.result import parse  # noqa: E402

# One hue for Mordecai, a potion red, as each sibling project has its own.
PALETTE = {
    "light": {
        "ink": "#1c1c1a",  # the wordmark, as in the family's lockups
        "tint": "#FFF1F2",  # the badge's face
        "glass": "#9F1239",  # the flask
        "potion": "#E11D48",  # what's in it: the score with the skill
        "line": "#4C0519",  # the dashed line: the score without it
        "shine": "#FFFFFF",
        "ring": "#881337",  # the badge's rim
    },
    "dark": {
        "ink": "#EDEDEA",
        "tint": "#2A0A12",
        "glass": "#FB7185",
        "potion": "#F43F5E",
        "line": "#FFE4E6",
        "shine": "#FFE4E6",
        "ring": "#FB7185",
    },
}

SANS = 'ui-sans-serif,system-ui,"Segoe UI",Helvetica,Arial,sans-serif'
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
BASELINE_Y = 60  # the dashed line, through the bulb's middle
LEVEL_Y = 46  # the potion's surface, above the line
DRAINED = 24  # how far the loop drains it: to y=70, below the line
FILL_S = 7  # the loop's length in seconds
LOCKUP_ALT = "Mordecai: a potion flask on a round badge, filled above a dashed line across the bulb"


def ascii_xml(text: str) -> str:
    """Escapes text for SVG, with anything outside ASCII as a character reference."""
    return "".join(c if ord(c) < 128 else f"&#{ord(c)};" for c in escape(text, quote=True))


def lockup(theme: str, motion: bool = True) -> str:
    c = PALETTE[theme]
    style = (
        # The rect's place in the file is the full flask, for renderers without CSS animation.
        # The loop starts it below the dashed line, fills it above, holds, and drains again:
        # the score without the skill, then with it.
        f".fill{{animation:fill {FILL_S}s cubic-bezier(.45,0,.55,1) infinite}}"
        f"@keyframes fill{{0%,94%,100%{{transform:translateY({DRAINED}px)}}"
        "20%,78%{transform:translateY(0)}}"
        "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
        if motion
        else ""
    ) + f".word{{font-family:{SANS};font-weight:800;letter-spacing:3px}}"
    flask = "M44 25 V39.88 A21 21 0 1 0 56 39.88 V25"
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 410 100" width="410" height="100" '
        f'role="img" aria-label="{LOCKUP_ALT}"><title>{LOCKUP_ALT}</title><style>{style}</style>'
        '<defs><clipPath id="bulb"><circle cx="50" cy="60" r="18.5"/></clipPath></defs>'
        f'<circle cx="50" cy="50" r="44" fill="{c["tint"]}"/>'
        f'<g clip-path="url(#bulb)"><rect class="fill" x="28" y="{LEVEL_Y}" width="44" '
        f'height="40" fill="{c["potion"]}"/></g>'
        f'<path d="M32 {BASELINE_Y} H68" stroke="{c["line"]}" stroke-width="2" '
        'stroke-dasharray="3.5 3"/>'
        f'<path d="M36.5 55 A14 14 0 0 1 42 47.5" fill="none" stroke="{c["shine"]}" '
        'stroke-width="2.5" stroke-linecap="round" opacity=".7"/>'
        f'<path d="{flask}" fill="none" stroke="{c["glass"]}" stroke-width="4" '
        'stroke-linejoin="round"/>'
        f'<rect x="40" y="19" width="20" height="6" rx="2" fill="{c["glass"]}"/>'
        f'<circle cx="50" cy="50" r="44" fill="none" stroke="{c["ring"]}" stroke-width="5"/>'
        f'<text class="word" x="112" y="67" font-size="46" textLength="280" '
        f'lengthAdjust="spacing" fill="{c["ink"]}">MORDECAI</text></svg>\n'
    )


# The social preview ------------------------------------------------------------------------

PREVIEW = ROOT / "docs" / "brand" / "social-preview.png"
PREVIEW_SIZE = (1280, 640)
PREVIEW_BG = "#0d1117"  # GitHub's dark page
TAGLINE = ("Reads a skill's eval results and says", "what the skill can honestly claim.")


def social_preview() -> str:
    """The still dark lockup, centered, with the tagline below, for GitHub's link preview."""
    w, h = PREVIEW_SIZE
    scale = 2.2
    lw, lh = 410 * scale, 100 * scale
    mark = re.sub(
        r"^<svg [^>]*><title>[^<]*</title>",
        f'<svg x="{(w - lw) / 2:g}" y="130" width="{lw:g}" height="{lh:g}" viewBox="0 0 410 100">',
        lockup("dark", motion=False).rstrip("\n"),
    )
    tagline = "".join(
        f'<text x="{w / 2:g}" y="{450 + i * 50}" text-anchor="middle" font-family="{escape(SANS)}" '
        f'font-size="36" fill="{CARD["dim"]}">{ascii_xml(line)}</text>'
        for i, line in enumerate(TAGLINE)
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" '
        f'height="{h}"><rect width="{w}" height="{h}" fill="{PREVIEW_BG}"/>{mark}{tagline}</svg>\n'
    )


def png_source(png: bytes) -> tuple[tuple[int, int], str | None]:
    """A PNG's size, and the hash of the SVG it was drawn from, as stamped by stamp()."""
    size = struct.unpack(">II", png[16:24])
    pos, source = 8, None
    while pos < len(png):
        length, kind = struct.unpack(">I4s", png[pos : pos + 8])
        if kind == b"tEXt":
            key, _, value = png[pos + 8 : pos + 8 + length].partition(b"\0")
            if key == b"Source":
                source = value.decode("ascii")
        pos += 12 + length
    return size, source


def stamp(png: bytes, source: str) -> bytes:
    """The PNG with a tEXt chunk naming the SVG it was drawn from, right after its header."""
    data = b"Source\0" + source.encode("ascii")
    chunk = struct.pack(">I", len(data)) + b"tEXt" + data
    chunk += struct.pack(">I", zlib.crc32(b"tEXt" + data))
    return png[:33] + chunk + png[33:]


def render_preview() -> bytes:
    """Draws the preview in headless Chromium. Needs the visual dependency group and a browser
    in .playwright/, so CI only checks the stamp and never runs this."""
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".playwright"))
    from playwright.sync_api import sync_playwright

    w, h = PREVIEW_SIZE
    svg = social_preview()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": w, "height": h})
        page.set_content(f'<!doctype html><body style="margin:0">{svg}</body>')
        png = page.screenshot()
        browser.close()
    return stamp(png, sha256(svg.encode()).hexdigest())


def preview_is_current() -> bool:
    if not PREVIEW.exists():
        return False
    size, source = png_source(PREVIEW.read_bytes())
    return size == PREVIEW_SIZE and source == sha256(social_preview().encode()).hexdigest()


# The crawl card ----------------------------------------------------------------------------

CARD_ALT = (
    "Crawl mode: a pixel treasure chest shakes, opens and lifts out a red potion, beside the "
    "card mordecai identify --crawl prints for a demo skill that helps"
)
CARD = {
    "bg": "#15111C",
    "edge": "#3B2A4A",
    "text": "#D9D3E0",
    "dim": "#9A90A8",
    "gold": "#FBBF24",
    "rose": "#FB7185",
}
# Pixel art, one character per pixel. O outline, W wood, G gold band, L lock, K keyhole,
# I the lid's inside, D the open chest's dark mouth, C cork, S glass, R potion, Y ray.
LID = (
    "..OOOOOOOOOOOO..",
    ".OWWWWWWWWWWWWO.",
    "OWWWWWWWWWWWWWWO",
    "OGGGGGGGGGGGGGGO",
    "OWWWWWWWWWWWWWWO",
    "OGGGGGGLLGGGGGGO",
)
# The lid swung back, seen from the front: its inside face over the chest's open mouth. It is
# its own sprite rather than the closed lid rotated, since rotated pixel art leaves the grid.
OPEN_LID = (
    "...OOOOOOOOOO...",
    "..OGGGGGGGGGGO..",
    "..OIIIIIIIIIIO..",
    ".OIIIIIIIIIIIIO.",
    ".OGGGGGGGGGGGGO.",
    "OOOOOOOOOOOOOOOO",
    "ODDDDDDDDDDDDDDO",
    "ODDDDDDDDDDDDDDO",
)
BODY = (
    "OWWWWWWLLWWWWWWO",
    "OWWWWWWKKWWWWWWO",
    "OWWWWWWWWWWWWWWO",
    "OGGGGGGGGGGGGGGO",
    "OWWWWWWWWWWWWWWO",
    "OWWWWWWWWWWWWWWO",
    "OGGGGGGGGGGGGGGO",
    "OOOOOOOOOOOOOOOO",
)
POTION = (
    "...OO...",
    "...CC...",
    "..OSSO..",
    ".OSSSSO.",
    "OSRRRRSO",
    "ORRRRRRO",
    "ORRRRRRO",
    ".ORRRRO.",
    "..OOOO..",
)
RAYS = (
    "Y......Y......Y.",
    ".Y.....Y.....Y..",
    "..Y....Y....Y...",
)
PIXEL = {
    "O": "#1A0B07",
    "W": "#9A3412",
    "G": "#F59E0B",
    "L": "#FDE68A",
    "K": "#1A0B07",
    "I": "#7C2D12",
    "D": "#2B0F07",
    "C": "#A16207",
    "S": "#FECDD3",
    "R": "#E11D48",
    "Y": "#FDE68A",
}
PX = 6  # screen pixels per art pixel; every move is a whole number of these


def pixels(grid, x0: int, y0: int) -> str:
    """Rects for a grid, one per horizontal run of a color."""
    out = []
    for row, line in enumerate(grid):
        col = 0
        while col < len(line):
            ch = line[col]
            end = col
            while end < len(line) and line[end] == ch:
                end += 1
            if ch != ".":
                out.append(
                    f'<rect x="{x0 + col * PX}" y="{y0 + row * PX}" width="{(end - col) * PX}" '
                    f'height="{PX}" fill="{PIXEL[ch]}"/>'
                )
            col = end
    return "".join(out)


def demo_text() -> str:
    """The crawl card for a demo skill that helps, printed by Mordecai's own renderer."""
    pattern = [([1, 1, 1], [0, 0, 1]), ([1, 1, 0], [0, 0, 0]), ([1, 1, 1], [1, 0, 0])]
    cases = [
        {"name": f"case-{i}", "with": w, "without": b, "fired": [True, True, True]}
        for i, (w, b) in enumerate(pattern * 4)
    ]
    cases.append({"name": "quiet", "with": [1, 1, 1], "without": [1, 1, 1], "quiet": True})
    with tempfile.TemporaryDirectory() as tmp:
        plugin = Path(tmp) / "plugin"
        skill = plugin / "skills" / "release-notes"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("Demo skill for the brand card.\n")
        for case in cases:
            (plugin / "evals" / case["name"]).mkdir(parents=True)
            (plugin / "evals" / case["name"] / "prompt.md").write_text(case["name"] + "\n")
        doc = make_result(cases, plugin_path=str(plugin))
        doc["suite"]["plugins"][0].update(name="release-notes", version="1.4.0")
        trace = Path(tmp) / "trace.jsonl"  # clean, beside the plugin so the skill hash keeps
        trace.write_text('{"type":"result","permission_denials":[]}\n')
        for case in doc["cases"]:
            for runs in case["arms"].values():
                for run in runs:
                    run["tracePath"] = str(trace)
        card = build(parse(doc), b"demo", plugin, roots=[Path(tmp)])
    return crawl(card, width=60)


def crawl_card() -> str:
    lines = demo_text().rstrip("\n").split("\n")
    line_h, top, text_x = 19, 34, 180
    height = top + line_h * len(lines) + 10
    width = text_x + math.ceil(max(len(line) for line in lines) * 7.6) + 28
    chest_x, chest_y = 34, height - 34 - len(BODY) * PX
    lid_y = chest_y - len(LID) * PX
    open_y = chest_y - len(OPEN_LID) * PX
    potion_x = chest_x + (16 - 8) // 2 * PX
    potion_y = chest_y - len(POTION) * PX
    # Far enough down that the whole potion is below the rim, where the clip hides it.
    sunk = len(POTION) * PX
    style = (
        f".t{{font-family:{MONO};font-size:12.5px;fill:{CARD['text']};white-space:pre}}"
        f".d{{fill:{CARD['dim']}}}.g{{fill:{CARD['gold']};font-weight:700}}"
        f".r{{fill:{CARD['rose']}}}"
        # Text arrives once, line by line, and stays.
        ".t{animation:in .45s ease-out both}"
        "@keyframes in{from{opacity:0;transform:translateX(-6px)}to{opacity:1}}"
        # The chest loops: still, shake, open, potion up, potion bobs, close.
        ".chest{animation:shake 6s steps(1) infinite}"
        f"@keyframes shake{{0%,12%{{transform:none}}14%{{transform:translateX(-{PX}px)}}"
        f"16%{{transform:translateX({PX}px)}}18%{{transform:translateX(-{PX}px)}}"
        f"20%{{transform:translateX({PX}px)}}22%,100%{{transform:none}}}}"
        # The lid opens by swapping the closed sprite for the open one, and back.
        ".lid{animation:lid 6s steps(1) infinite}"
        "@keyframes lid{0%,24%{opacity:1}26%,82%{opacity:0}84%,100%{opacity:1}}"
        ".open{animation:open 6s steps(1) infinite}"
        "@keyframes open{0%,24%{opacity:0}26%,82%{opacity:1}84%,100%{opacity:0}}"
        # The potion rises out of the chest a pixel row at a time, bobs, and sinks back in. It
        # sits behind the body and is clipped at the rim, so it only shows above the chest.
        ".potion{animation:rise 6s steps(1) infinite}"
        f"@keyframes rise{{0%,26%,82%,100%{{transform:translateY({sunk}px)}}"
        "28%,80%{transform:translateY(42px)}30%,78%{transform:translateY(24px)}"
        "32%,76%{transform:translateY(6px)}34%,46%,58%,70%{transform:translateY(0)}"
        "40%,52%,64%{transform:translateY(-6px)}}"
        ".rays{animation:rays 6s steps(1) infinite}"
        "@keyframes rays{0%,26%{opacity:0}28%,36%,44%,52%,60%,68%{opacity:1}"
        "32%,40%,48%,56%,64%,72%{opacity:.35}76%,100%{opacity:0}}"
        ".loot{animation:shine 2.4s ease-in-out infinite}"
        f"@keyframes shine{{0%,100%{{fill:{CARD['gold']}}}50%{{fill:#FFF7D6}}}}"
        "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
    )
    texts = []
    for i, line in enumerate(lines):
        y = top + i * line_h
        delay = f' style="animation-delay:{0.3 + i * 0.12:.2f}s"'
        if i == 0:
            cls = "t g"
        elif line.startswith("Mordecai:"):
            cls = "t r"
        elif line.startswith("  release-notes"):
            head, loot = re.match(r"^(.*\.{3,}) (.+)$", line).groups()
            texts.append(
                f'<text class="t" x="{text_x}" y="{y}"{delay}>{ascii_xml(head)} '
                f'<tspan class="g loot">{ascii_xml(loot)}</tspan></text>'
            )
            continue
        elif line.startswith("  "):
            cls = "t d"
        else:
            cls = "t"
        texts.append(f'<text class="{cls}" x="{text_x}" y="{y}"{delay}>{ascii_xml(line)}</text>')
    # The finished picture, for renderers without CSS animation, is the chest open with the
    # potion out: the closed lid's opacity="0" and the potion's place are in the file itself.
    # Drawn back to front: rays, the two lids, potion, then the body in front of the potion.
    rim = (
        f'<defs><clipPath id="rim"><rect x="{chest_x + PX}" y="0" width="{14 * PX}" '
        f'height="{chest_y}"/></clipPath></defs>'
    )
    art = (
        f'<g class="rays">{pixels(RAYS, chest_x, potion_y - 5 * PX)}</g>'
        f'<g class="chest"><g class="lid" opacity="0">{pixels(LID, chest_x, lid_y)}</g>'
        f'<g class="open">{pixels(OPEN_LID, chest_x, open_y)}</g>'
        f'<g clip-path="url(#rim)"><g class="potion">{pixels(POTION, potion_x, potion_y)}</g></g>'
        f"{pixels(BODY, chest_x, chest_y)}</g>"
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
        f'height="{height}" shape-rendering="crispEdges" role="img" aria-label="{CARD_ALT}">'
        f"<title>{CARD_ALT}</title><style>{style}</style>"
        f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="10" fill="{CARD["bg"]}" '
        f'stroke="{CARD["edge"]}" stroke-width="2"/>' + rim + art + "".join(texts) + "</svg>\n"
    )


def outputs() -> dict[Path, str]:
    files = {ROOT / "docs" / "brand" / "crawl-card.svg": crawl_card()}
    for theme in ("light", "dark"):
        files[ROOT / "docs" / "brand" / f"lockup-{theme}.svg"] = lockup(theme)
    return files


def main(argv: list[str]) -> int:
    stale = []
    for path, text in outputs().items():
        if "--check" in argv:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(path.relative_to(ROOT).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
    if "--png" in argv:
        PREVIEW.write_bytes(render_preview())
    for name in stale:
        print(f"brand: {name} differs from scripts/brand.py; run it")
    if not preview_is_current():
        name = PREVIEW.relative_to(ROOT).as_posix()
        print(f"brand: {name} wasn't drawn from the current preview; run it with --png")
        return 1
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
