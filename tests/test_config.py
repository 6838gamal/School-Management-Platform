"""Unit tests for application settings defaults and env parsing."""

from app.core.config import Settings, settings


def test_default_app_name():
    assert settings.APP_NAME == "School Management System"


def test_settings_read_env_at_instantiation(monkeypatch):
    monkeypatch.setenv("APP_NAME", "Test School")
    s = Settings()
    assert s.APP_NAME == "Test School"


def test_max_upload_bytes():
    s = Settings()
    assert s.max_upload_bytes == s.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def test_default_session_max_age_is_seven_days():
    assert settings.SESSION_MAX_AGE == 604800


def test_session_cookie_defaults_are_safe():
    assert settings.SESSION_HTTPONLY is True
    assert settings.SESSION_SAMESITE == "lax"
