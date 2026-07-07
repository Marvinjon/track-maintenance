import pytest

from app.config import Settings, validate_production_settings


def test_production_validation_passes_with_valid_settings():
    settings = Settings(
        app_env="production",
        database_url="mysql+pymysql://maint_user:secret@127.0.0.1:3306/track_maintenance",
        traccar_admin_token="admin-token",
        webhook_secret="webhook-secret",
        session_cookie_secure=True,
        cors_origins="https://fleet.example.com",
    )
    validate_production_settings(settings)


def test_production_validation_rejects_missing_secrets():
    settings = Settings(
        app_env="production",
        database_url="mysql+pymysql://maint_user:secret@127.0.0.1:3306/track_maintenance",
        traccar_admin_token="",
        webhook_secret="",
        session_cookie_secure=True,
        cors_origins="https://fleet.example.com",
    )
    with pytest.raises(RuntimeError, match="TRACCAR_ADMIN_TOKEN"):
        validate_production_settings(settings)


def test_production_validation_rejects_default_db_password():
    settings = Settings(
        app_env="production",
        database_url="mysql+pymysql://maint_user:change-me@127.0.0.1:3306/track_maintenance",
        traccar_admin_token="admin-token",
        webhook_secret="webhook-secret",
        session_cookie_secure=True,
        cors_origins="https://fleet.example.com",
    )
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        validate_production_settings(settings)


def test_development_skips_production_validation():
    settings = Settings(
        app_env="development",
        traccar_admin_token="",
        webhook_secret="",
        session_cookie_secure=False,
        cors_origins="",
    )
    validate_production_settings(settings)
