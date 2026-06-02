"""Builder: Bible source file -> validated canonical JSON, in one step.

Usage:
    python -m soap_journal.cli build-translation --code ESV <source> [--out <path>]

Behavior:
- Subprocesses the matching parser CLI
  (`python -m soap_journal.parsers.<lowercase-code> <source> --out <tmp>`),
  exactly as scripts/docker-entrypoint.sh drives the parsers, then validates
  the produced JSON in-process and moves it to `--out` only if it passes.
- Touches NO database.
- Exit codes match the sibling CLI commands: 0 success; 2 for invocation
  problems (unknown code, missing source file, bad args); 1 if the build
  fails (parser error, or the produced JSON fails canonical validation).
- On any failure, no `--out` file is written — parsing happens in a temp
  directory and the result is moved into place only after validation passes.

This collapses the previous two-command flow (parse, then validate) into one
so a non-expert can turn their own PDF into an import-ready, schema-valid file
with a single command.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from pydantic import ValidationError

from soap_journal.cli.load_translation import translation_counts
from soap_journal.parsers.schema import CanonicalTranslation

# Supported translation code -> parser module. Every parser module is named
# for the lowercased code (matching scripts/docker-entrypoint.sh): BSB is the
# plain-text parser, the 12 public-domain translations share the PDFMaker
# engine, and ESV/NKJV/NLT are the user-supplied copyrighted parsers.
PARSER_MODULES: dict[str, str] = {
    code: f"soap_journal.parsers.{code.lower()}"
    for code in (
        "BSB",
        "KJV",
        "AKJV",
        "ASV",
        "CPDV",
        "DBT",
        "DRB",
        "ERV",
        "JPS",
        "SLT",
        "WBT",
        "WEB",
        "YLT",
        "ESV",
        "NKJV",
        "NLT",
    )
}


def _run_parser(module: str, source: Path, out: Path) -> subprocess.CompletedProcess[str]:
    """Invoke a parser CLI as a subprocess, writing canonical JSON to `out`."""
    return subprocess.run(
        [sys.executable, "-m", module, str(source), "--out", str(out)],
        capture_output=True,
        text=True,
        check=False,
    )


def build_translation_command(code: str, source_str: str, out_str: str | None) -> int:
    code = code.upper()
    module = PARSER_MODULES.get(code)
    if module is None:
        valid = ", ".join(sorted(PARSER_MODULES))
        print(
            f"error: unknown translation code {code!r}; valid codes: {valid}",
            file=sys.stderr,
        )
        return 2

    source = Path(source_str)
    if not source.exists():
        print(f"error: {source} does not exist", file=sys.stderr)
        return 2

    out_path = Path(out_str) if out_str else Path(f"{code.lower()}.json")

    # Parse into a temp dir; nothing is written to --out until validation passes.
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_out = Path(tmpdir) / f"{code.lower()}.json"
        result = _run_parser(module, source, tmp_out)
        if result.returncode != 0:
            if result.stderr:
                print(result.stderr, file=sys.stderr, end="")
            print(f"error: failed to parse {source} as {code}", file=sys.stderr)
            return 1

        try:
            raw = tmp_out.read_text(encoding="utf-8")
            payload = CanonicalTranslation.model_validate_json(raw)
        except (OSError, ValidationError) as exc:
            print(f"error: canonical schema validation failed:\n{exc}", file=sys.stderr)
            return 1

        out_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(tmp_out), str(out_path))

    books, chapters, verses = translation_counts(payload)
    print(
        f"Built {payload.code}: {books} books, {chapters} chapters, {verses} verses -> {out_path}"
    )
    return 0
