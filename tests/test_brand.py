"""The logo lockups and the crawl card are exactly what scripts/brand.py draws, and stay small,
ASCII and labelled for screen readers."""

import importlib.util
import re

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
    assert '<g class="lid" transform="translate(-8 -16) rotate(-10' in brand.crawl_card()


def test_the_crawl_card_is_what_the_tool_prints():
    card = brand.crawl_card()
    for line in brand.demo_text().splitlines():
        if line.strip() and not line.startswith("  release-notes"):
            assert brand.ascii_xml(line) in card, line
