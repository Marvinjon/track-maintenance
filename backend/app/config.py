"""Application settings, loaded from environment variables (see .env.example)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

NOTES_MAX_LENGTH = 10_000

# .env lives at the repo root; uvicorn is usually started from backend/.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _REPO_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.is_file() else ".env",
        extra="ignore",
    )

    app_env: str = "development"
    database_url: str = "mysql+pymysql://maint_user:change-me@127.0.0.1:3306/track_maintenance"
    traccar_url: str = "http://127.0.0.1:8082"
    # User-facing Traccar hostname for deep links (e.g. https://gps.example.com).
    traccar_public_url: str = ""
    traccar_admin_token: str = ""
    webhook_secret: str = ""
    bind_host: str = "127.0.0.1"
    bind_port: int = 8000
    due_soon_km: int = 500
    due_soon_days: int = 14
    due_soon_hours: int = 50
    cors_origins: str = ""
    # Set true in production (HTTPS) so the login session cookie is Secure-only.
    session_cookie_secure: bool = False
    # SMTP email notifications for due/overdue maintenance (optional).
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    notification_cooldown_hours: int = 24

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host)

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"


def validate_production_settings(settings: Settings) -> None:
    """Fail fast when production is misconfigured."""
    if not settings.is_production:
        return

    errors: list[str] = []
    if not settings.traccar_admin_token.strip():
        errors.append("TRACCAR_ADMIN_TOKEN must be set in production")
    if not settings.webhook_secret.strip():
        errors.append("WEBHOOK_SECRET must be set in production")
    if "change-me" in settings.database_url:
        errors.append("DATABASE_URL must not use the default password in production")
    if not settings.session_cookie_secure:
        errors.append("SESSION_COOKIE_SECURE must be true in production")
    if not settings.cors_origin_list:
        errors.append("CORS_ORIGINS must be set in production")

    if errors:
        raise RuntimeError(
            "Production configuration errors:\n- " + "\n- ".join(errors)
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
