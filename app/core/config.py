"""Application configuration loaded from environment variables."""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    # Application
    APP_NAME: str = "School Management System"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_URL: str = "http://localhost:8000"
    APP_LANGUAGE: Literal["ar", "en"] = "ar"
    APP_DEFAULT_TIMEZONE: str = "Asia/Riyadh"

    # Security
    SECRET_KEY: str = "change-me-to-a-long-random-string-in-production"
    SESSION_COOKIE_NAME: str = "sms_session"
    SESSION_MAX_AGE: int = 86400
    SESSION_SECURE: bool = False
    SESSION_HTTPONLY: bool = True
    SESSION_SAMESITE: str = "lax"
    PASSWORD_HASH_SCHEME: str = "bcrypt"

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://sms_user:sms_password@localhost:5432/sms_db"
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = False

    # Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@school.edu"

    # Uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # Reports
    REPORT_LINK_EXPIRY_DAYS: int = 7
    REPORT_LINK_SECRET: str = "change-me-report-secret"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
