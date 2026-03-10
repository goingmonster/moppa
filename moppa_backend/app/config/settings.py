import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus


def load_dotenv_file(file_path: Path) -> None:
    if not file_path.exists():
        return

    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        _ = os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    app_debug: bool
    host: str
    port: int
    db_host: str
    db_port: int
    db_name: str
    db_schema: str
    db_user: str
    db_password: str

    @property
    def database_url(self) -> str:
        user = quote_plus(self.db_user)
        password = quote_plus(self.db_password)
        return f"postgresql://{user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}"


def env_bool(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(key: str, default: int) -> int:
    value = os.getenv(key)
    if value is None:
        return default
    return int(value)


def load_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv_file(project_root / ".env")

    return Settings(
        app_name=os.getenv("APP_NAME", "MOPPA Backend"),
        app_env=os.getenv("APP_ENV", "development"),
        app_debug=env_bool("APP_DEBUG", True),
        host=os.getenv("HOST", "0.0.0.0"),
        port=env_int("PORT", 8000),
        db_host=os.getenv("DB_HOST", "127.0.0.1"),
        db_port=env_int("DB_PORT", 5432),
        db_name=os.getenv("DB_NAME", "moppa"),
        db_schema=os.getenv("DB_SCHEMA", "public"),
        db_user=os.getenv("DB_USER", "postgres"),
        db_password=os.getenv("DB_PASSWORD", ""),
    )


settings = load_settings()
