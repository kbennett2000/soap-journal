import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT: Path = Path(__file__).resolve().parents[2]

SECRET_KEY_FILENAME = ".secret_key"
SECRET_KEY_BYTES = 64


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    port: int = 8080
    data_dir: Path = Path("./data")
    secret_key: str = ""
    bind_host: str = "0.0.0.0"
    frontend_dist_dir: Path | None = None

    @field_validator("data_dir")
    @classmethod
    def _resolve_data_dir(cls, value: Path) -> Path:
        if not value.is_absolute():
            value = REPO_ROOT / value
        return value.resolve()

    @field_validator("frontend_dist_dir", mode="before")
    @classmethod
    def _coerce_frontend_dist_dir(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @property
    def database_url(self) -> str:
        db_path = self.data_dir / "soap_journal.db"
        return f"sqlite+aiosqlite:///{db_path}"


def resolve_secret_key(data_dir: Path) -> str:
    """Return a SECRET_KEY value, generating and persisting one if missing.

    Reads or creates `{data_dir}/.secret_key`. The file is created with
    mode 0600 so it isn't world-readable on a multi-user host.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    key_path = data_dir / SECRET_KEY_FILENAME
    if key_path.exists():
        existing = key_path.read_text().strip()
        if existing:
            return existing
    token = secrets.token_urlsafe(SECRET_KEY_BYTES)
    key_path.write_text(token)
    key_path.chmod(0o600)
    return token


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()  # type: ignore[call-arg]
    if not settings.secret_key:
        settings.secret_key = resolve_secret_key(settings.data_dir)
    return settings
