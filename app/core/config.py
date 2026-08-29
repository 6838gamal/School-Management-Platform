"""Application configuration loaded from environment variables."""
import os
from functools import lru_cache
from typing import Literal


class Settings:
    """Application settings from environment variables."""
    
    # Application
    APP_NAME: str = os.getenv("APP_NAME", "School Management System")
    APP_ENV: Literal["development", "staging", "production"] = os.getenv("APP_ENV", "development")  # type: ignore
    APP_DEBUG: bool = os.getenv("APP_DEBUG", "True").lower() == "true"
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    APP_URL: str = os.getenv("APP_URL", "http://localhost:8000")
    APP_LANGUAGE: Literal["ar", "en"] = os.getenv("APP_LANGUAGE", "ar")  # type: ignore
    APP_DEFAULT_TIMEZONE: str = os.getenv("APP_DEFAULT_TIMEZONE", "Asia/Riyadh")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-to-a-long-random-string-in-production")
    SESSION_COOKIE_NAME: str = os.getenv("SESSION_COOKIE_NAME", "sms_session")
    
    # ✅ زيادة مدة صلاحية الجلسة إلى 7 أيام (604800 ثانية)
    SESSION_MAX_AGE: int = int(os.getenv("SESSION_MAX_AGE", "604800"))  # 7 أيام
    
    # ✅ تفعيل تجديد الجلسة مع كل طلب
    SESSION_REFRESH_EACH_REQUEST: bool = os.getenv("SESSION_REFRESH_EACH_REQUEST", "True").lower() == "true"
    
    # ✅ جعل الكوكيز آمنة في الإنتاج
    SESSION_SECURE: bool = os.getenv("SESSION_SECURE", "False").lower() == "true"
    SESSION_HTTPONLY: bool = os.getenv("SESSION_HTTPONLY", "True").lower() == "true"
    SESSION_SAMESITE: str = os.getenv("SESSION_SAMESITE", "lax")
    PASSWORD_HASH_SCHEME: str = os.getenv("PASSWORD_HASH_SCHEME", "bcrypt")

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://sms_user:sms_password@localhost:5432/sms_db"
    )
    DATABASE_SSL: bool = os.getenv("DATABASE_SSL", "False").lower() == "true"
    DATABASE_POOL_SIZE: int = int(os.getenv("DATABASE_POOL_SIZE", "10"))
    DATABASE_MAX_OVERFLOW: int = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "False").lower() == "true"

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_ENABLED: bool = os.getenv("REDIS_ENABLED", "False").lower() == "true"

    # Email
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@school.edu")

    # Uploads
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))

    # Pagination
    DEFAULT_PAGE_SIZE: int = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))
    MAX_PAGE_SIZE: int = int(os.getenv("MAX_PAGE_SIZE", "100"))

    # Reports
    REPORT_LINK_EXPIRY_DAYS: int = int(os.getenv("REPORT_LINK_EXPIRY_DAYS", "7"))
    REPORT_LINK_SECRET: str = os.getenv("REPORT_LINK_SECRET", "change-me-report-secret")

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
