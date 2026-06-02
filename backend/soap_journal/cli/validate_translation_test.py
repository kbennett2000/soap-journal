"""Tests for the validate-translation CLI.

Mirrors the CLI-surface tests in load_translation_test.py, but asserts the
command performs a pure schema check with no database side effects.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from soap_journal.cli.load_translation_test import _full_translation
from soap_journal.cli.validate_translation import validate_translation_command
from soap_journal.config import Settings


def test_cli_validates_good_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    good = tmp_path / "good.json"
    good.write_text(_full_translation().model_dump_json())

    rc = validate_translation_command(str(good))

    assert rc == 0
    out = capsys.readouterr().out.strip()
    assert out == "Valid TST: 66 books, 66 chapters, 66 verses"


def test_cli_rejects_invalid_canonical_json(
    tmp_path: Path,
    settings: Settings,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"code":"X","name":"X","language":"en","copyright":"x","books":[]}')

    rc = validate_translation_command(str(bad))

    assert rc == 1
    assert capsys.readouterr().err.strip() != ""
    # Validation must be a pure schema check: no engine, no DB written.
    assert not (settings.data_dir / "soap_journal.db").exists()


def test_cli_rejects_missing_file(tmp_path: Path) -> None:
    rc = validate_translation_command(str(tmp_path / "nope.json"))
    assert rc == 2
