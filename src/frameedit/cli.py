"""Command line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import ConfigError, load_config
from .pipeline import BatchError, run_batch


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="frameedit",
        description="Generate branded Instagram posts, reel covers, mosaics, and carousel assets locally.",
    )
    parser.add_argument(
        "input_dir",
        nargs="?",
        help="Optional input directory override. Defaults to input_dir from config.yaml.",
    )
    parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to YAML config file. Defaults to config.yaml.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and show planned outputs without writing files.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        if args.input_dir:
            input_dir = Path(args.input_dir).expanduser()
            if not input_dir.is_absolute():
                input_dir = Path.cwd() / input_dir
            config = config.with_input_dir(input_dir.resolve())

        result = run_batch(config, dry_run=args.dry_run)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2
    except BatchError as exc:
        print(f"Batch error: {exc}", file=sys.stderr)
        return 1

    for warning in result.warnings:
        print(f"Warning: {warning}", file=sys.stderr)

    if result.dry_run:
        print("Dry run: planned outputs")
    else:
        print("Generated outputs")

    if result.outputs:
        for output in result.outputs:
            print(f"- {output.kind}: {output.target}")
    else:
        print("- No outputs planned.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
