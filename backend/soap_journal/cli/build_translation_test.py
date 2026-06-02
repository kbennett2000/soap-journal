"""Tests for the build-translation CLI.

Orchestration only — the per-parser tests already cover real Bible parsing, so
here the parser step is stubbed via `_run_parser` to keep the suite fast and
DB-free. Asserts the registry, exit codes, output handling, and the
"failure writes no --out file" guarantee.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from soap_journal.cli import build_translation as build_mod
from soap_journal.cli.build_translation import build_translation_command
from soap_journal.cli.load_translation_test import _full_translation


def _stub_parser_writing(payload_json: str):
    """Return a _run_parser stub that writes payload_json to `out` and succeeds."""

    def _stub(module: str, source: Path, out: Path) -> subprocess.CompletedProcess[str]:
        out.write_text(payload_json)
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    return _stub


def test_cli_rejects_unknown_code(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = build_translation_command("ZZZ", str(tmp_path / "src.txt"), None)

    assert rc == 2
    err = capsys.readouterr().err
    # Error lists the valid codes.
    assert "BSB" in err
    assert "ESV" in err


def test_cli_rejects_missing_source(tmp_path: Path) -> None:
    rc = build_translation_command("BSB", str(tmp_path / "nope.txt"), None)
    assert rc == 2


def test_cli_builds_validated_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "src.txt"
    source.write_text("ignored — parser is stubbed")
    out = tmp_path / "out.json"
    monkeypatch.setattr(
        build_mod,
        "_run_parser",
        _stub_parser_writing(_full_translation(code="BSB").model_dump_json()),
    )

    rc = build_translation_command("BSB", str(source), str(out))

    assert rc == 0
    assert out.exists()
    # The written file is itself schema-valid.
    build_mod.CanonicalTranslation.model_validate_json(out.read_text())
    assert capsys.readouterr().out.strip() == (
        f"Built BSB: 66 books, 66 chapters, 66 verses -> {out}"
    )


def test_cli_parser_failure_writes_no_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "src.txt"
    source.write_text("ignored")
    out = tmp_path / "out.json"

    def _failing(module: str, source: Path, out: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="boom\n")

    monkeypatch.setattr(build_mod, "_run_parser", _failing)

    rc = build_translation_command("BSB", str(source), str(out))

    assert rc == 1
    assert not out.exists()


def test_cli_schema_invalid_output_writes_no_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "src.txt"
    source.write_text("ignored")
    out = tmp_path / "out.json"
    monkeypatch.setattr(
        build_mod,
        "_run_parser",
        _stub_parser_writing('{"code":"X","name":"X","language":"en","copyright":"x","books":[]}'),
    )

    rc = build_translation_command("BSB", str(source), str(out))

    assert rc == 1
    assert not out.exists()


def test_cli_defaults_out_path_from_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "src.txt"
    source.write_text("ignored")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        build_mod,
        "_run_parser",
        _stub_parser_writing(_full_translation(code="BSB").model_dump_json()),
    )

    rc = build_translation_command("BSB", str(source), None)

    assert rc == 0
    assert (tmp_path / "bsb.json").exists()
