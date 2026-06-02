"""Validator: canonical Bible JSON file -> schema check, no database.

Usage:
    python -m soap_journal.cli validate-translation <path.json>

Behavior:
- Validates the input against `CanonicalTranslation`. Touches NO database,
  creates no engine, writes nothing — it only reads the file.
- Prints a one-line summary on success, identical in shape to the loader's
  (reusing the same counting logic, so validate and load always agree).
- Schema-validation failure: prints the validation error to stderr, exits 1.
- Missing/unreadable file: exits 2, matching the loader's file-error convention.

This is the reference implementation a future TypeScript validator (for the
phone app that consumes parser output) is checked against: same schema, same
counts as `load-translation`, but with zero side effects.
"""

from __future__ import annotations

import sys
from pathlib import Path

from pydantic import ValidationError

from soap_journal.cli.load_translation import translation_counts
from soap_journal.parsers.schema import CanonicalTranslation


def validate_translation_command(path_str: str) -> int:
    path = Path(path_str)
    if not path.exists():
        print(f"error: {path} does not exist", file=sys.stderr)
        return 2
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    try:
        payload = CanonicalTranslation.model_validate_json(raw)
    except ValidationError as exc:
        print(f"error: canonical schema validation failed:\n{exc}", file=sys.stderr)
        return 1

    books, chapters, verses = translation_counts(payload)
    print(f"Valid {payload.code}: {books} books, {chapters} chapters, {verses} verses")
    return 0
