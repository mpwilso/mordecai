"""The logo lockups and the crawl card are exactly what scripts/brand.py draws, and stay small,
ASCII and labelled for screen readers."""

import importlib.util
import math
import re
import xml.etree.ElementTree as ET

from conftest import ROOT

spec = importlib.util.spec_from_file_location("brand", ROOT / "scripts" / "brand.py")
brand = importlib.util.module_from_spec(spec)
spec.loader.exec_module(brand)


def test_files_match_the_script():
    assert brand.main(["--check"]) == 0


def test_files_are_small_ascii_and_labelled():
    for path, text in brand.outputs().items():
        assert text.isascii(), path
        assert len(text.encode()) < 16000, path
        label = re.search(r'aria-label="([^"]+)"', text).group(1)
        assert f"<title>{label}</title>" in text, path
        assert "@media (prefers-reduced-motion: reduce){*{animation:none!important}}" in text


def test_the_still_frame_is_the_finished_picture():
    """Without animation the flask is full and the chest is open, because those states are in
    the file itself rather than only in the animation."""
    for theme in ("light", "dark"):
        svg = brand.lockup(theme)
        assert f'<rect class="fill" x="28" y="{brand.LEVEL_Y}"' in svg
        # The loop starts below the dashed line and fills above it.
        assert f"0%,94%,100%{{transform:translateY({brand.DRAINED}px)}}" in svg
        assert brand.LEVEL_Y + brand.DRAINED > brand.BASELINE_Y > brand.LEVEL_Y
        assert "infinite" in svg
    assert '<g class="lid" opacity="0">' in brand.crawl_card()  # the open lid shows instead


def test_the_crawl_card_is_what_the_tool_prints():
    card = brand.crawl_card()
    for line in brand.demo_text().splitlines():
        if line.strip() and not line.startswith("  release-notes"):
            assert brand.ascii_xml(line) in card, line


# The crawl card's art, frame by frame ------------------------------------------------------

SVG_NS = "{http://www.w3.org/2000/svg}"


def _matrix(text: str):
    """A CSS or SVG transform list as an affine matrix (a, b, c, d, e, f)."""
    m = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for fn, args in re.findall(r"(\w+)\(([^)]*)\)", text or ""):
        v = [float(x) for x in re.findall(r"-?[\d.]+", args)]
        if fn == "translateX":
            step = [(1, 0, 0, 1, v[0], 0)]
        elif fn == "translateY":
            step = [(1, 0, 0, 1, 0, v[0])]
        elif fn == "translate":
            step = [(1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)]
        elif fn == "rotate":
            r = math.radians(v[0])
            turn = (math.cos(r), math.sin(r), -math.sin(r), math.cos(r), 0, 0)
            cx, cy = (v[1], v[2]) if len(v) == 3 else (0, 0)
            step = [(1, 0, 0, 1, cx, cy), turn, (1, 0, 0, 1, -cx, -cy)]
        else:
            raise AssertionError(fn)
        for s in step:
            m = _mul(m, s)
    return m


def _mul(p, q):
    a, b, c, d, e, f = p
    a2, b2, c2, d2, e2, f2 = q
    return (
        a * a2 + c * b2,
        b * a2 + d * b2,
        a * c2 + c * d2,
        b * c2 + d * d2,
        a * e2 + c * f2 + e,
        b * e2 + d * f2 + f,
    )


def _box(m, x, y, w, h):
    pts = [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]
    xs = [m[0] * px + m[2] * py + m[4] for px, py in pts]
    ys = [m[1] * px + m[3] * py + m[5] for px, py in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _keyframes(svg: str) -> dict[str, list[tuple[float, str]]]:
    """Each stepped animation's transform keyframes, by the class it runs on."""
    names = dict(re.findall(r"\.(\w+)\{animation:(\w+) 6s steps\(1\) infinite\}", svg))
    frames = {}
    for cls, name in names.items():
        body = re.search(r"@keyframes " + name + r"\{((?:[^{}]*\{[^{}]*\})*)\}", svg).group(1)
        steps = []
        for sel, decl in re.findall(r"([^{}]+)\{([^{}]*)\}", body):
            t = re.search(r"transform:([^;]+)", decl)
            if t:
                steps += [(float(p.strip().rstrip("%")), t.group(1)) for p in sel.split(",")]
        frames[cls] = sorted(steps)
    return frames


def _transform_at(steps, pct: float, still: str) -> str:
    if pct is None or not steps:
        return still
    return [t for p, t in steps if p <= pct][-1]


def _art_boxes(svg: str, pct: float | None):
    """Where each pixel of art is drawn at pct of the loop (None: the still frame), and the
    class of the group it belongs to. A clip-path cuts the box to the clip's rectangle."""
    root = ET.fromstring(svg)
    frames = _keyframes(svg)
    clips = {
        c.get("id"): [float(r.get(k)) for k in ("x", "y", "width", "height")]
        for c in root.iter(SVG_NS + "clipPath")
        for r in c
    }
    out = []

    def walk(el, m, clip, owner):
        cls = el.get("class")
        if el.tag == SVG_NS + "g":
            if cls in frames or el.get("transform"):
                t = _transform_at(frames.get(cls), pct, el.get("transform") or "none")
                m = _mul(m, _matrix(t))
            if el.get("clip-path"):
                x, y, w, h = clips[el.get("clip-path")[5:-1]]
                clip = _box(m, x, y, w, h)
            owner = cls or owner
            for child in el:
                walk(child, m, clip, owner)
        elif el.tag == SVG_NS + "rect" and owner:
            x0, y0, x1, y1 = _box(m, *(float(el.get(k)) for k in ("x", "y", "width", "height")))
            if clip:
                x0, y0 = max(x0, clip[0]), max(y0, clip[1])
                x1, y1 = min(x1, clip[2]), min(y1, clip[3])
            if x1 > x0 and y1 > y0:
                out.append((owner, el, (x0, y0, x1, y1)))

    for child in root:
        if child.tag == SVG_NS + "g":
            walk(child, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0), None, None)
    return out


def _bounds(boxes):
    return (
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )


def test_the_crawl_art_stays_inside_the_card_at_every_keyframe():
    """At the still frame and at every keyframe of the chest's loop, every pixel of art is at
    least 8px inside the card's border and 8px clear of the text column, where text starts 6px
    left of its x as it slides in. The potion never shows below the chest's rim."""
    svg = brand.crawl_card()
    width, height = (float(v) for v in re.search(r'viewBox="0 0 (\d+) (\d+)"', svg).groups())
    border = 2  # the card's rect runs from 0 to 2 with its stroke
    text_x = min(float(x) for x in re.findall(r'<text class="[^"]*" x="([\d.]+)"', svg))
    allowed = (border + 8, border + 8, text_x - 6 - 8, height - border - 8)
    chest = next(g for g in ET.fromstring(svg).iter(SVG_NS + "g") if g.get("class") == "chest")
    rim = min(float(r.get("y")) for r in chest.findall(SVG_NS + "rect"))  # the body's top
    pcts = sorted({p for steps in _keyframes(svg).values() for p, _ in steps})
    assert len(pcts) > 20
    for pct in [None, *pcts]:
        boxes = _art_boxes(svg, pct)
        x0, y0, x1, y1 = _bounds([b for _, _, b in boxes])
        where = "still frame" if pct is None else f"{pct}%"
        assert x0 >= allowed[0] and y0 >= allowed[1], where
        assert x1 <= allowed[2] and y1 <= allowed[3], where
        potion = [b for owner, _, b in boxes if owner == "potion"]
        assert all(b[3] <= rim for b in potion), where
    # The still frame is the open chest with the whole potion out above the rim.
    still = _art_boxes(svg, None)
    assert sum(owner == "potion" for owner, _, _ in still) == sum(
        1 for _ in re.finditer("<rect", re.search(r'<g class="potion">(.*?)</g>', svg).group(1))
    )


def test_the_potion_is_drawn_behind_the_chest_body_and_in_front_of_the_lid():
    chest = next(
        g for g in ET.fromstring(brand.crawl_card()).iter(SVG_NS + "g") if g.get("class") == "chest"
    )
    order = [c.get("class") or c.get("clip-path") or c.tag[len(SVG_NS) :] for c in chest]
    assert order[:3] == ["lid", "open", "url(#rim)"] and set(order[3:]) == {"rect"}
    assert chest[2][0].get("class") == "potion"


def test_the_social_preview_is_drawn_from_the_current_lockup():
    """The PNG is 1280x640 and stamped with the hash of the SVG scripts/brand.py draws now."""
    size, source = brand.png_source(brand.PREVIEW.read_bytes())
    assert size == (1280, 640)
    assert source == brand.sha256(brand.social_preview().encode()).hexdigest()
    assert "animation" not in brand.social_preview()


def test_a_stamp_is_read_back():
    png = brand.PREVIEW.read_bytes()
    restamped = brand.stamp(png[:33] + png[33 + 12 + len(b"Source\0") + 64 :], "abc")
    assert brand.png_source(restamped) == ((1280, 640), "abc")


def _opacity_frames(svg: str) -> dict[str, list[tuple[float, float]]]:
    """Each stepped animation's opacity keyframes, by the class it runs on."""
    names = dict(re.findall(r"\.(\w+)\{animation:(\w+) 6s steps\(1\) infinite\}", svg))
    frames = {}
    for cls, name in names.items():
        body = re.search(r"@keyframes " + name + r"\{((?:[^{}]*\{[^{}]*\})*)\}", svg).group(1)
        steps = []
        for sel, decl in re.findall(r"([^{}]+)\{([^{}]*)\}", body):
            o = re.search(r"opacity:([\d.]+)", decl)
            if o:
                steps += [(float(p.strip().rstrip("%")), float(o.group(1))) for p in sel.split(",")]
        frames[cls] = sorted(steps)
    return frames


def test_the_crawl_art_stays_on_its_pixel_grid():
    """Pixel art only looks right whole pixels at a time: at the still frame and at every
    keyframe, every pixel of the chest, lid, potion and rays sits on the chest's PX grid. A
    rotated lid or a shake of less than a pixel breaks that."""
    svg = brand.crawl_card()
    chest = next(g for g in ET.fromstring(svg).iter(SVG_NS + "g") if g.get("class") == "chest")
    body = chest.findall(SVG_NS + "rect")
    x0 = min(float(r.get("x")) for r in body)
    y0 = min(float(r.get("y")) for r in body)
    pcts = sorted({p for steps in _keyframes(svg).values() for p, _ in steps})
    for pct in [None, *pcts]:
        where = "still frame" if pct is None else f"{pct}%"
        for owner, _, (a, b, c, d) in _art_boxes(svg, pct):
            for v in ((a - x0), (b - y0), (c - a), (d - b)):
                assert abs(v / brand.PX - round(v / brand.PX)) < 1e-6, (where, owner, v)


def test_one_lid_shows_at_a_time_and_the_still_frame_is_open():
    svg = brand.crawl_card()
    frames = _opacity_frames(svg)
    closed, opened = frames["lid"], frames["open"]
    assert [p for p, _ in closed] == [p for p, _ in opened]
    assert all(a + b == 1 for (_, a), (_, b) in zip(closed, opened, strict=True))
    assert '<g class="lid" opacity="0">' in svg and '<g class="open">' in svg
    # Open while the potion is out: from the lid's opening to its closing.
    assert dict(opened)[26] == 1 and dict(opened)[82] == 1 and dict(opened)[84] == 0
