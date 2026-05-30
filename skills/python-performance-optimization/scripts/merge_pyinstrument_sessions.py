#!/usr/bin/env python3
"""Merge pyinstrument session files into a single combined report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

from pyinstrument.renderers import (
    ConsoleRenderer,
    HTMLRenderer,
    JSONRenderer,
    SpeedscopeRenderer,
)
from pyinstrument.session import Session


FORMAT_BY_SUFFIX = {
    ".html": "html",
    ".htm": "html",
    ".txt": "text",
    ".json": "json",
    ".pyisession": "pyisession",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge multiple pyinstrument .pyisession files into one report."
    )
    parser.add_argument(
        "sessions",
        nargs="+",
        type=Path,
        help="Input .pyisession files to merge in the provided order.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output path. Required for non-text formats.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "html", "json", "speedscope", "pyisession"),
        help="Output format. Defaults to text if --output is omitted, or is inferred from --output.",
    )
    parser.add_argument(
        "--timeline",
        action="store_true",
        help="Render in timeline mode instead of aggregating repeated calls.",
    )
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="Show all frames instead of hiding library frames.",
    )
    parser.add_argument(
        "--text-time",
        choices=("seconds", "percent_of_total"),
        default="seconds",
        help="Time display mode for text output.",
    )
    parser.add_argument(
        "--flat",
        action="store_true",
        help="Render text output as a flat profile.",
    )
    parser.add_argument(
        "--short-mode",
        action="store_true",
        help="Render text output in pyinstrument short mode.",
    )
    parser.add_argument(
        "--resample-interval",
        type=float,
        default=None,
        help="HTML renderer resample interval. Leave unset for pyinstrument's automatic behavior.",
    )
    return parser.parse_args()


def infer_format(args: argparse.Namespace) -> str:
    if args.format:
        return args.format
    if args.output is None:
        return "text"

    if args.output.name.endswith(".speedscope.json"):
        return "speedscope"

    inferred = FORMAT_BY_SUFFIX.get(args.output.suffix.lower())
    if inferred is None:
        raise SystemExit(
            "Could not infer output format from the output path. "
            "Use --format explicitly."
        )
    return inferred


def load_and_combine(paths: Iterable[Path]) -> Session:
    iterator = iter(paths)
    first_path = next(iterator, None)
    if first_path is None:
        raise SystemExit("At least one input session is required.")

    combined = Session.load(first_path)
    for path in iterator:
        combined = Session.combine(combined, Session.load(path))
    return combined


def render_report(session: Session, args: argparse.Namespace, output_format: str) -> str | None:
    common_kwargs = {"show_all": args.show_all, "timeline": args.timeline}

    if output_format == "pyisession":
        if args.output is None:
            raise SystemExit("--output is required for pyisession output.")
        session.save(args.output)
        return None

    if output_format == "html":
        renderer = HTMLRenderer(
            resample_interval=args.resample_interval,
            **common_kwargs,
        )
        return renderer.render(session)

    if output_format == "json":
        return JSONRenderer(**common_kwargs).render(session)

    if output_format == "speedscope":
        return SpeedscopeRenderer(**common_kwargs).render(session)

    if output_format == "text":
        renderer = ConsoleRenderer(
            time=args.text_time,
            flat=args.flat,
            short_mode=args.short_mode,
            unicode=False,
            color=False,
            **common_kwargs,
        )
        return renderer.render(session)

    raise SystemExit(f"Unsupported format: {output_format}")


def main() -> int:
    args = parse_args()
    output_format = infer_format(args)

    for path in args.sessions:
        if not path.is_file():
            raise SystemExit(f"Input session does not exist: {path}")

    session = load_and_combine(args.sessions)
    rendered = render_report(session, args, output_format)

    if rendered is None:
        return 0

    if args.output is None:
        sys.stdout.write(rendered)
        if not rendered.endswith("\n"):
            sys.stdout.write("\n")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
