"""Entry point: `python -m soap_journal.cli <subcommand> ...`."""

from __future__ import annotations

import argparse
import sys

from soap_journal.cli.load_translation import load_translation_command
from soap_journal.cli.validate_translation import validate_translation_command


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m soap_journal.cli",
        description="Operator CLI for soap-journal.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    load_parser = subparsers.add_parser(
        "load-translation",
        help="Load a canonical Bible JSON file into the database.",
    )
    load_parser.add_argument("path", help="Path to a canonical translation JSON file.")

    validate_parser = subparsers.add_parser(
        "validate-translation",
        help="Validate a canonical Bible JSON file against the schema (no DB writes).",
    )
    validate_parser.add_argument("path", help="Path to a canonical translation JSON file.")

    args = parser.parse_args(argv)
    if args.command == "load-translation":
        return load_translation_command(args.path)
    if args.command == "validate-translation":
        return validate_translation_command(args.path)
    parser.error(f"unknown command {args.command!r}")
    return 2  # pragma: no cover - argparse.error raises before this


if __name__ == "__main__":  # pragma: no cover - thin shell
    sys.exit(main())
