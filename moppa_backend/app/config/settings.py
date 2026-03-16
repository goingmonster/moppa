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
    source_db_host: str
    source_db_port: int
    source_db_name: str
    source_db_schema: str
    source_db_user: str
    source_db_password: str
    source_system_name: str
    source_fetch_limit: int
    source_bootstrap_limit: int
    source_overlap_minutes: int
    scheduler_enabled: bool
    auto_review_enabled: bool
    auto_review_cron: str
    auto_review_model: str
    auto_review_base_url: str
    auto_review_api_key: str
    auto_review_batch_size: int
    auto_review_timeout_seconds: int
    log_level: str
    auth_enabled: bool
    auth_access_token_expire_minutes: int
    auth_refresh_token_expire_days: int
    auth_jwt_secret: str
    auth_jwt_issuer: str
    integration_api_token: str
    cors_allowed_origins: list[str]

    @property
    def database_url(self) -> str:
        user = quote_plus(self.db_user)
        password = quote_plus(self.db_password)
        return f"postgresql://{user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def source_database_url(self) -> str:
        user = quote_plus(self.source_db_user)
        password = quote_plus(self.source_db_password)
        return f"postgresql://{user}:{password}@{self.source_db_host}:{self.source_db_port}/{self.source_db_name}"


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


def env_csv(key: str, default: str) -> list[str]:
    value = os.getenv(key, default)
    return [item.strip() for item in value.split(",") if item.strip()]


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
        source_db_host=os.getenv("SOURCE_DB_HOST", "127.0.0.1"),
        source_db_port=env_int("SOURCE_DB_PORT", 5432),
        source_db_name=os.getenv("SOURCE_DB_NAME", "news_event"),
        source_db_schema=os.getenv("SOURCE_DB_SCHEMA", "public"),
        source_db_user=os.getenv("SOURCE_DB_USER", "postgres"),
        source_db_password=os.getenv("SOURCE_DB_PASSWORD", ""),
        source_system_name=os.getenv("SOURCE_SYSTEM_NAME", "news_event_crawler"),
        source_fetch_limit=env_int("SOURCE_FETCH_LIMIT", 200),
        source_bootstrap_limit=env_int("SOURCE_BOOTSTRAP_LIMIT", 500),
        source_overlap_minutes=env_int("SOURCE_OVERLAP_MINUTES", 10),
        scheduler_enabled=env_bool("SCHEDULER_ENABLED", True),
        auto_review_enabled=env_bool("AUTO_REVIEW_ENABLED", False),
        auto_review_cron=os.getenv("AUTO_REVIEW_CRON", "0 * * * *"),
        auto_review_model=os.getenv("AUTO_REVIEW_MODEL", "GLM-4.6-FP8"),
        auto_review_base_url=os.getenv("AUTO_REVIEW_BASE_URL", ""),
        auto_review_api_key=os.getenv("AUTO_REVIEW_API_KEY", ""),
        auto_review_batch_size=env_int("AUTO_REVIEW_BATCH_SIZE", 100),
        auto_review_timeout_seconds=env_int("AUTO_REVIEW_TIMEOUT_SECONDS", 60),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        auth_enabled=env_bool("AUTH_ENABLED", False),
        auth_access_token_expire_minutes=env_int("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES", 30),
        auth_refresh_token_expire_days=env_int("AUTH_REFRESH_TOKEN_EXPIRE_DAYS", 14),
        auth_jwt_secret=os.getenv("AUTH_JWT_SECRET", "change-me-in-production"),
        auth_jwt_issuer=os.getenv("AUTH_JWT_ISSUER", "moppa-backend"),
        integration_api_token=os.getenv("INTEGRATION_API_TOKEN", ""),
        cors_allowed_origins=env_csv(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ),
    )


settings = load_settings()
