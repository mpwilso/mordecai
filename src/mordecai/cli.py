"""mordecai identify: read an eval result and print the card.
mordecai check: say whether a card still matches the skill and cases it was measured on.
"""

import argparse
import os
import sys
import time
from pathlib import Path

from mordecai import __version__
from mordecai.card import CardError, build, check, to_json
from mordecai.lint import LintError, lint
from mordecai.provenance import PathError
from mordecai.render import clean, crawl, markdown, plain
from mordecai.result import ResultError, load, read_json
from mordecai.verdict import VERDICTS

# A loot box opening, one line redrawn in place. Shown only in crawl mode, on a terminal.
BOX = ("[  ?  ]", "[ ?!? ]", "[\\ * /]", "[* | *]")


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mordecai", description="Says what a skill's eval results let it claim."
    )
    p.add_argument("--version", action="version", version=f"mordecai {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    i = sub.add_parser("identify", help="read a claude plugin eval result and print the card")
    i.add_argument("result", type=Path, help="the JSON from claude plugin eval --json")
    i.add_argument("--skill", type=Path, help="the plugin directory, if not where it was run")
    i.add_argument("--card", type=Path, help="also write the card as JSON here")
    i.add_argument("--markdown", type=Path, help="also write the card as Markdown here")
    i.add_argument(
        "--crawl",
        action="store_true",
        default=os.environ.get("MORDECAI_MODE") == "crawl",
        help="dungeon mode: the same card, with loot and commentary (or MORDECAI_MODE=crawl)",
    )
    i.add_argument(
        "--fail-on",
        default="",
        metavar="VERDICTS",
        help=f"exit 1 on these verdicts, comma-separated: {', '.join(VERDICTS)}",
    )

    c = sub.add_parser("check", help="exit 1 if a card's skill or cases have changed")
    c.add_argument("card", type=Path)
    c.add_argument("--skill", type=Path, help="the plugin directory, if it has moved")
    c.add_argument("--cases-root", type=Path, help="the directory holding the cases, if moved")
    c.add_argument(
        "--model", help="the model you use now; a card measured on another model is stale"
    )
    lt = sub.add_parser("lint", help="run the case-quality warnings on a plugin's eval cases")
    lt.add_argument("plugin", type=Path, nargs="+", help="plugin directories")
    return p


def _color_ok(stream) -> bool:
    return stream.isatty() and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb"


def _open_box(stream, sleep=time.sleep) -> None:
    for frame in BOX:
        stream.write(f"\r  {frame}  opening the box...")
        stream.flush()
        sleep(0.18)
    stream.write("\r" + " " * 40 + "\r")


def identify(args, out) -> int:
    fail_on = {v.strip() for v in args.fail_on.split(",") if v.strip()}
    unknown = fail_on - set(VERDICTS)
    if unknown:
        print(
            f"mordecai: unknown verdict(s) for --fail-on: {clean(', '.join(sorted(unknown)))}",
            file=sys.stderr,
        )
        return 2
    try:
        suite, data = load(args.result)
        card = build(suite, data, args.skill)
        if args.card:
            args.card.write_text(to_json(card, args.card.parent), encoding="utf-8", newline="\n")
        if args.markdown:
            args.markdown.write_text(markdown(card), encoding="utf-8", newline="\n")
    except (ResultError, PathError, OSError) as e:
        print(f"mordecai: {clean(str(e))}", file=sys.stderr)
        return 2
    if args.crawl:
        color = _color_ok(out)
        if color:
            _open_box(out)
        out.write(crawl(card, color=color))
    else:
        out.write(plain(card))
    return 1 if card.reading.verdict in fail_on else 0


def check_card(args, out) -> int:
    try:
        doc, _ = read_json(args.card, "a card")
        changes = check(doc, args.card.parent, args.skill, args.cases_root, args.model)
    except (ResultError, CardError, PathError, OSError) as e:
        print(f"mordecai: can't check {clean(str(args.card))}: {clean(str(e))}", file=sys.stderr)
        return 2
    name = clean(str(args.card))
    if not changes:
        out.write(f"Current: {name} matches the skill and cases it was measured on.\n")
        return 0
    out.write(f"Stale: {name}\n" + "".join(f"  - {clean(c)}\n" for c in changes))
    return 1


def lint_plugins(args, out) -> int:
    worst = 0
    for plugin in args.plugin:
        try:
            files, warnings = lint(plugin)
        except LintError as e:
            print(f"mordecai: {clean(str(e))}", file=sys.stderr)
            worst = 2
            continue
        quiet = sum(1 for f in files if f.case.trigger == "should-not-fire")
        out.write(
            f"{clean(str(plugin))}: {len(files)} cases ({len(files) - quiet} compared, "
            f"{quiet} quiet), {len(warnings)} warning(s)\n"
        )
        out.write("".join(f"  - {clean(w)}\n" for w in warnings))
        worst = max(worst, 1 if warnings else 0)
    return worst


def main(argv: list[str] | None = None, out=None) -> int:
    args = _parser().parse_args(argv)
    out = out or sys.stdout
    if args.command == "identify":
        return identify(args, out)
    if args.command == "lint":
        return lint_plugins(args, out)
    return check_card(args, out)
