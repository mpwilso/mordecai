# Mordecai brand

Every SVG here is drawn by `scripts/brand.py`. To change one, edit the script and run `uv run python scripts/brand.py`. `tests/test_brand.py` fails if a file and the script disagree.

## The mark

A potion flask on a round badge, in the family's shape: a face, a rim, and one idea inside. The dashed line across the bulb is how the model scores without the skill. The potion is how it scores with it. On a 7-second loop it starts below the line, fills above it, holds for about four seconds, and drains again. Viewers who ask for reduced motion, and renderers without CSS animation, see the full flask.

## The lockup

The mark and the word MORDECAI. Use [lockup-light.svg](lockup-light.svg) on light pages and [lockup-dark.svg](lockup-dark.svg) on dark ones. An image can't see the page's theme, so a web page picks the file:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="lockup-dark.svg">
  <img src="lockup-light.svg" alt="Mordecai: a potion flask on a round badge, filled above a dashed line across the bulb" height="72">
</picture>

## The crawl card

[crawl-card.svg](crawl-card.svg) is crawl mode, for the README. A pixel chest shakes, opens and lifts out a potion, and the card's lines arrive one by one. The text is the output of `mordecai identify --crawl` for a demo skill with simulated results, printed by the tool's own code when the script runs. With reduced motion, the chest is shown open with the potion out.

## Looking at the animations

`scripts/frames.py` makes contact sheets of an SVG shown as an `<img>`, the way GitHub shows it: one frame every 5% of the loop and at every keyframe, plus the still frame. With `--live` it screenshots the image unchanged as it plays, from a file or a URL. Sheets go to `frames/`, which git ignores.

## Palette

One hue, a potion red. The light and dark values are in `PALETTE` in `scripts/brand.py`, and the crawl card's colors are in `CARD` and `PIXEL`.

| Name | Light | Dark | Use |
|---|---|---|---|
| ring | `#881337` | `#FB7185` | The badge's rim. |
| glass | `#9F1239` | `#FB7185` | The flask. |
| potion | `#E11D48` | `#F43F5E` | The score with the skill. |
| line | `#4C0519` | `#FFE4E6` | The dashed line: the score without it. |
| tint | `#FFF1F2` | `#2A0A12` | The badge's face. |
| ink | `#1c1c1a` | `#EDEDEA` | The word. |

## Type

The word is set in the reader's own sans-serif system font, weight 800, so the files carry no font. Its spacing is fixed with `textLength`, so it fits whatever font draws it. The crawl card uses the reader's monospace font, like a terminal.
