"""Tests for the PDFMaker translations registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from soap_journal.parsers._pdfmaker_translations import (
    PDFMAKER_CONFIGS,
    get_config,
)


def test_registry_has_12_entries() -> None:
    assert len(PDFMAKER_CONFIGS) == 12


def test_all_codes_uppercase_and_match_keys() -> None:
    for key, cfg in PDFMAKER_CONFIGS.items():
        assert key == cfg.code
        assert key == key.upper()


def test_codes_are_unique() -> None:
    codes = [cfg.code for cfg in PDFMAKER_CONFIGS.values()]
    assert len(set(codes)) == len(codes)


def test_all_configs_have_nonempty_fields() -> None:
    for cfg in PDFMAKER_CONFIGS.values():
        assert cfg.code, f"{cfg.code} has empty code"
        assert cfg.name, f"{cfg.code} has empty name"
        assert cfg.language, f"{cfg.code} has empty language"
        assert cfg.copyright, f"{cfg.code} has empty copyright"
        assert cfg.footer_marker, f"{cfg.code} has empty footer_marker"


def test_footer_markers_follow_pattern() -> None:
    for cfg in PDFMAKER_CONFIGS.values():
        assert cfg.footer_marker == f"{cfg.code}  [Online]", (
            f"{cfg.code} footer_marker {cfg.footer_marker!r} doesn't match pattern"
        )


def test_get_config_returns_correct_config() -> None:
    cfg = get_config("KJV")
    assert cfg.code == "KJV"
    assert cfg.name == "King James Version"


def test_get_config_raises_for_unknown() -> None:
    with pytest.raises(KeyError):
        get_config("NONEXISTENT")


def test_source_directories_exist() -> None:
    sources_dir = Path(__file__).parents[3] / "bible-sources"
    for cfg in PDFMAKER_CONFIGS.values():
        code_dir = sources_dir / cfg.code.lower()
        assert code_dir.is_dir(), f"missing directory: {code_dir}"
