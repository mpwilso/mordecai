"""mordecai identify: read an eval result (or a skill-creator benchmark.json) and print the card.
mordecai measure: run claude plugin eval with a pinned model and a cost cap, then identify.
mordecai check: say whether a card still matches the skill and cases it was measured on.
mordecai lint: run the case-quality warnings on a plugin's eval cases before an eval.
mordecai library and mordecai mcp: the skill library, in mordecai.library. They are handed over
before this module parses anything, so the engine never imports the library.

Exit codes: 0 for a clean result, 1 for what the command checks for (a --fail-on verdict, a
stale card, lint warnings), 2 for input Mordecai can't read or won't use, and 3 when measure's
eval didn't finish, so there is no result to read.
"""

import argparse
import os
import shutil
import subprocess
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
    i.add_argument(
        "result",
        type=Path,
        help="the JSON from claude plugin eval --json, or a skill-creator benchmark.json",
    )
    i.add_argument(
        "--skill",
        type=Path,
        help="the plugin directory, if it has moved or is outside the current directory",
    )
    _card_options(i)

    m = sub.add_parser(
        "measure",
        help="run claude plugin eval with a pinned model and a cost cap, then print the card",
    )
    m.add_argument("plugin", type=Path, help="the plugin directory claude plugin eval runs")
    m.add_argument("--model", help="the model to run on; required, since a live run spends money")
    m.add_argument(
        "--max-cost-usd",
        metavar="USD",
        help="the cost cap passed to claude plugin eval; required, for the same reason",
    )
    m.add_argument(
        "--result",
        type=Path,
        default=Path("result.json"),
        help="where the eval writes its result (default: result.json; an existing file is kept)",
    )
    m.add_argument(
        "--skill",
        type=Path,
        help="the skill directory to hash, if it isn't the plugin directory",
    )
    _card_options(m)

    c = sub.add_parser(
        "check", help="exit 1 if a card's skill, cases or (with --model) model have changed"
    )
    c.add_argument("card", type=Path, help="a card written by identify --card")
    c.add_argument(
        "--skill",
        type=Path,
        help="the plugin directory, if it has moved or is outside the current directory",
    )
    c.add_argument("--cases-root", type=Path, help="the directory holding the cases, if moved")
    c.add_argument(
        "--model", help="the model you use now; a card measured on another model is stale"
    )
    lt = sub.add_parser("lint", help="run the case-quality warnings on a plugin's eval cases")
    lt.add_argument("plugin", type=Path, nargs="+", help="plugin directories")
    # Listed for --help only: main() hands these to mordecai.library before parsing.
    sub.add_parser("library", help="keep, release and install skills, with each version's verdict")
    sub.add_parser("mcp", help="serve the skill library to MCP clients over stdio")
    return p


def _card_options(p: argparse.ArgumentParser) -> None:
    """The options identify and measure share: where the card goes, its mode, and --fail-on."""
    p.add_argument("--card", type=Path, help="also write the card as JSON here")
    p.add_argument("--markdown", type=Path, help="also write the card as Markdown here")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--crawl",
        action="store_true",
        default=os.environ.get("MORDECAI_MODE") == "crawl",
        help="dungeon mode: the same card, with loot and commentary (or MORDECAI_MODE=crawl)",
    )
    mode.add_argument(
        "--plain",
        dest="crawl",
        action="store_false",
        help="the plain card, even when MORDECAI_MODE=crawl is set",
    )
    p.add_argument(
        "--fail-on",
        default="",
        metavar="VERDICTS",
        help=f"exit 1 on these verdicts, comma-separated: {', '.join(VERDICTS)}",
    )


def _fail_on(args) -> set[str] | None:
    """The verdicts --fail-on names, or None after saying why they can't be used."""
    fail_on = {v.strip() for v in args.fail_on.split(",") if v.strip()}
    unknown = fail_on - set(VERDICTS)
    if unknown:
        print(
            f"mordecai: unknown verdict(s) for --fail-on: {clean(', '.join(sorted(unknown)))}. "
            f"Use {', '.join(VERDICTS)}.",
            file=sys.stderr,
        )
        return None
    return fail_on


def _color_ok(stream) -> bool:
    return stream.isatty() and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb"


def _open_box(stream, sleep=time.sleep) -> None:
    for frame in BOX:
        stream.write(f"\r  {frame}  opening the box...")
        stream.flush()
        sleep(0.18)
    stream.write("\r" + " " * 40 + "\r")


def identify(args, out) -> int:
    fail_on = _fail_on(args)
    if fail_on is None:
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


# What measure runs, with the plugin, model, result path and cap filled in: the command the
# README shows, so a measured card comes from the same run a person would make by hand.
EVAL = ("plugin", "eval", "--trust-plugin", "--no-publish")


def eval_argv(claude: str, plugin: Path, model: str, result: Path, cap: str) -> list[str]:
    return [claude, *EVAL, str(plugin), "--model", model, "--json", str(result)] + [
        "--max-cost-usd",
        cap,
    ]


def _cost_cap(text: str) -> str | None:
    """The cap as given, when it is a finite number above zero; None otherwise."""
    try:
        value = float(text)
    except ValueError:
        return None
    return text if 0 < value < float("inf") else None


def measure(args, out) -> int:
    """claude plugin eval with a pinned model and a cost cap, then identify on what it wrote.
    Everything that can refuse does so before the eval starts, since the eval spends money."""
    if not args.model or args.max_cost_usd is None:
        print(
            "mordecai: measure needs --model and --max-cost-usd, since a live run spends money.",
            file=sys.stderr,
        )
        return 2
    cap = _cost_cap(args.max_cost_usd)
    if cap is None:
        print(
            "mordecai: --max-cost-usd must be a number above zero, "
            f"not {clean(args.max_cost_usd)}.",
            file=sys.stderr,
        )
        return 2
    if _fail_on(args) is None:
        return 2
    if not args.plugin.is_dir():
        print(f"mordecai: {clean(str(args.plugin))} is not a directory.", file=sys.stderr)
        return 2
    if args.result.exists():
        print(
            f"mordecai: {clean(str(args.result))} already exists; move it, or name another "
            "file with --result.",
            file=sys.stderr,
        )
        return 2
    claude = shutil.which("claude")
    if claude is None:
        print(
            "mordecai: claude is not on PATH; install Claude Code, then measure.",
            file=sys.stderr,
        )
        return 3
    done = subprocess.run(eval_argv(claude, args.plugin, args.model, args.result, cap))
    if done.returncode != 0:
        print(
            f"mordecai: claude plugin eval exited {done.returncode}; no card was written.",
            file=sys.stderr,
        )
        return 3
    if not args.result.is_file():
        print(
            f"mordecai: claude plugin eval exited 0 but wrote no {clean(str(args.result))}; "
            "no card was written.",
            file=sys.stderr,
        )
        return 3
    if args.skill is None:
        args.skill = args.plugin
    return identify(args, out)


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


LIBRARY_MODULES = ("strictyaml", "mcp")


def _library(argv: list[str], out) -> int:
    try:
        from mordecai.library.cli import main as library_main
    except ImportError as e:
        if (e.name or "").split(".")[0] not in LIBRARY_MODULES:
            raise
        print(
            f"mordecai: {argv[0]} needs the optional library extra: uv sync --extra library",
            file=sys.stderr,
        )
        return 2
    return library_main(argv, out)


def main(argv: list[str] | None = None, out=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in ("library", "mcp"):
        return _library(argv, out)
    args = _parser().parse_args(argv)
    out = out or sys.stdout
    if args.command == "identify":
        return identify(args, out)
    if args.command == "measure":
        return measure(args, out)
    if args.command == "lint":
        return lint_plugins(args, out)
    return check_card(args, out)
