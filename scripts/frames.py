"""Contact sheets of the brand animations, frame by frame, for looking at them.

    export PLAYWRIGHT_BROWSERS_PATH=.playwright
    uv run --group visual playwright install chromium-headless-shell
    uv run --group visual python scripts/frames.py NAME [SVG_OR_URL] [--label=L] [--crop=x,y,w,h]
    uv run --group visual python scripts/frames.py NAME URL --live

Each SVG is shown the way GitHub shows it, as an <img>, in headless Chromium. A frame at time t
is the same SVG with every animation paused t seconds in (a negative animation-delay), so
frames land on exact times: every 5% of the cycle, every keyframe boundary, and the still
frame with animation off. --crop cuts each frame to that box, at 2x. With --live the image is
loaded unchanged, from a file or a URL such as the one GitHub serves in the README, and
screenshotted as it plays, so the times are only as exact as the screenshots. Sheets go to
frames/, which git ignores. Not part of any check.
"""

import base64
import re
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "frames"
BG = {"light": "#ffffff", "dark": "#0d1117"}


def cycle_and_marks(svg: str) -> tuple[float, list[float]]:
    """The longest animation's duration, and every keyframe boundary in seconds within it."""
    durations = {
        name: float(d)
        for name, d in re.findall(r"animation:([a-z]+) ([0-9.]+)s", svg)
        if name not in ("none", "in")
    }
    cycle = max(durations.values())
    marks = set()
    for name, body in re.findall(r"@keyframes ([a-z]+)\{((?:[^{}]*\{[^{}]*\})*)\}", svg):
        if name not in durations:
            continue
        for sel in re.findall(r"([^{}]+)\{", body):
            for p in sel.split(","):
                p = p.strip()
                pct = {"from": 0.0, "to": 100.0}.get(p)
                pct = float(p.rstrip("%")) if pct is None else pct
                t = round(durations[name] * pct / 100, 4)
                if t <= cycle:
                    marks.add(t)
    return cycle, sorted(marks)


def frozen(svg: str, t: float | None) -> str:
    """The SVG paused t seconds in, or with animation off when t is None."""
    if t is None:
        rule = "*{animation:none!important}"
    else:
        rule = f"*{{animation-delay:{-t:.4f}s!important;animation-play-state:paused!important}}"

        def shift(m):
            return f"animation-delay:{float(m.group(1)) - t:.4f}s!important"

        svg = re.sub(r"animation-delay:([0-9.]+)s", shift, svg)
    return svg.replace("</style>", rule + "</style>", 1)


def data_uri(mime: str, data: bytes) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def sheet(page, cells, width: int, bg: str, title: str, path: Path, cols: int, crop=None) -> None:
    """One screenshot of a grid of captioned images, each cut to crop (x, y, w, h) if given."""
    box, img = "", f'width="{width}"'
    if crop:
        x, y, w, h = crop
        box = f'style="width:{w}px;height:{h}px;overflow:hidden"'
        img += f' style="display:block;margin:{-y}px 0 0 {-x}px"'
        width = w
    items = "".join(
        f'<figure><div {box}><img src="{src}" {img}></div><figcaption>{cap}</figcaption></figure>'
        for src, cap in cells
    )
    page.set_content(
        "<!doctype html><style>body{margin:12px;font:12px monospace;background:#888}"
        f"main{{display:grid;grid-template-columns:repeat({cols},{width}px);gap:10px}}"
        f"figure{{margin:0;background:{bg};padding:6px}}"
        "figcaption{color:#888;padding-top:4px}h1{font-size:14px}</style>"
        f"<h1>{title}</h1><main>{items}</main>"
    )
    page.wait_for_timeout(300)
    page.screenshot(path=str(path), full_page=True)


def times(cycle: float, marks: list[float]) -> list[float]:
    grid = [round(cycle * i / 20, 4) for i in range(21)]
    return sorted(set(grid) | set(marks))


def frozen_sheet(page, name: str, svg: str, label: str, bg: str, crop=None) -> Path:
    width = int(re.search(r'width="(\d+)"', svg).group(1))
    cycle, marks = cycle_and_marks(svg)
    cells = [(data_uri("image/svg+xml", frozen(svg, None).encode()), "still (animation off)")]
    for t in times(cycle, marks):
        tag = " key" if t in marks else ""
        cap = f"t={t:.2f}s {100 * t / cycle:.0f}%{tag}"
        cells.append((data_uri("image/svg+xml", frozen(svg, t).encode()), cap))
    path = OUT / f"{name}-{label}{'-crop' if crop else ''}.png"
    cols = 4 if width < 500 or crop else 2
    sheet(page, cells, width, bg, f"{name} {label}: cycle {cycle}s", path, cols, crop)
    return path


def live_sheet(page, name: str, src: str, label: str, bg: str, seconds: float) -> Path:
    """Screenshots of the unchanged image as it plays, with the time each was taken."""
    if src.startswith("http"):
        with urllib.request.urlopen(src, timeout=30) as r:
            data, mime = r.read(), r.headers.get_content_type()
    else:
        data, mime = Path(src).read_bytes(), "image/svg+xml"
    page.set_content(
        f'<!doctype html><body style="margin:0;background:{bg}">'
        f'<img id="i" src="{data_uri(mime, data)}"></body>'
    )
    page.wait_for_function("document.getElementById('i').complete")
    img = page.locator("#i")
    width = int(img.evaluate("e => e.naturalWidth"))
    start = time.monotonic()
    shots, seen = [], set()
    while time.monotonic() - start < seconds:
        t = time.monotonic() - start
        png = img.screenshot()
        seen.add(png)
        shots.append((data_uri("image/png", png), f"~{t:.2f}s"))
        time.sleep(max(0.0, 0.25 - (time.monotonic() - start - t)))
    title = f"{name} {label}: {mime}, {len(shots)} shots, {len(seen)} distinct"
    path = OUT / f"{name}-{label}.png"
    sheet(page, shots, width, bg, title, path, 4 if width < 500 else 2)
    print(title)
    return path


def main(argv: list[str]) -> int:
    live = "--live" in argv
    args = [a for a in argv if not a.startswith("--")]
    name = args[0]
    src = args[1] if len(args) > 1 else str(ROOT / "docs" / "brand" / f"{name}.svg")
    label = next((a.split("=", 1)[1] for a in argv if a.startswith("--label=")), "now")
    bg = BG["dark"] if "dark" in name else BG["light"]
    crop = next((a.split("=", 1)[1] for a in argv if a.startswith("--crop=")), None)
    crop = tuple(int(n) for n in crop.split(",")) if crop else None
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(device_scale_factor=2 if "lockup" in name or crop else 1)
        if live:
            path = live_sheet(page, name, src, label, bg, 9.0)
        else:
            svg = Path(src).read_text(encoding="utf-8")
            path = frozen_sheet(page, name, svg, label, bg, crop)
        browser.close()
    print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
