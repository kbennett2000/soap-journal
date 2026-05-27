import stat
from pathlib import Path

from soap_journal.config import SECRET_KEY_FILENAME, resolve_secret_key


def test_resolve_secret_key_creates_file_with_0600(tmp_path: Path) -> None:
    key = resolve_secret_key(tmp_path)
    key_file = tmp_path / SECRET_KEY_FILENAME

    assert key
    assert len(key) >= 64
    assert key_file.exists()
    assert key_file.read_text() == key

    mode = stat.S_IMODE(key_file.stat().st_mode)
    assert mode == 0o600


def test_resolve_secret_key_reads_existing_file(tmp_path: Path) -> None:
    existing = "pre-existing-key-value"
    (tmp_path / SECRET_KEY_FILENAME).write_text(existing)

    assert resolve_secret_key(tmp_path) == existing


def test_resolve_secret_key_creates_data_dir_if_missing(tmp_path: Path) -> None:
    nested = tmp_path / "fresh" / "data"
    assert not nested.exists()

    key = resolve_secret_key(nested)

    assert nested.is_dir()
    assert (nested / SECRET_KEY_FILENAME).exists()
    assert key
