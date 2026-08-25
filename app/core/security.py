"""Password hashing and session-token signing utilities."""
from datetime import datetime, timedelta, timezone
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(
    schemes=[settings.PASSWORD_HASH_SCHEME],
    deprecated="auto",
)

_serializer: URLSafeTimedSerializer | None = None


def _serializer() -> URLSafeTimedSerializer:
    global _serializer
    if _serializer is None:
        _serializer = URLSafeTimedSerializer(
            settings.SECRET_KEY,
            salt="sms-session",
        )
    return _serializer


def hash_password(raw: str) -> str:
    """Hash a password using bcrypt with automatic truncation to 72 bytes."""
    # bcrypt limit is 72 bytes
    if len(raw.encode('utf-8')) > 72:
        raw = raw[:72]
    return pwd_context.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    """Verify a password against its hash with automatic truncation to 72 bytes."""
    # bcrypt limit is 72 bytes
    if len(raw.encode('utf-8')) > 72:
        raw = raw[:72]
    return pwd_context.verify(raw, hashed)


def encode_session(payload: dict[str, Any], max_age: int | None = None) -> str:
    """Sign a session payload into a tamper-proof token for the cookie."""
    age = max_age if max_age is not None else settings.SESSION_MAX_AGE
    return _serializer().dumps(payload)


def decode_session(token: str, max_age: int | None = None) -> dict[str, Any] | None:
    """Verify and decode a session token. Returns None if invalid/expired."""
    age = max_age if max_age is not None else settings.SESSION_MAX_AGE
    try:
        return _serializer().loads(token, max_age=age)
    except (BadSignature, SignatureExpired):
        return None


def generate_report_link_token(report_id: str, extra: dict[str, Any] | None = None) -> str:
    payload: dict[str, Any] = {"rid": report_id, "exp": _report_expiry()}
    if extra:
        payload.update(extra)
    return URLSafeTimedSerializer(settings.REPORT_LINK_SECRET, salt="sms-report").dumps(payload)


def verify_report_link_token(token: str) -> dict[str, Any] | None:
    try:
        return URLSafeTimedSerializer(
            settings.REPORT_LINK_SECRET, salt="sms-report"
        ).loads(token, max_age=settings.REPORT_LINK_EXPIRY_DAYS * 86400)
    except (BadSignature, SignatureExpired):
        return None


def _report_expiry() -> str:
    return (
        datetime.now(timezone.utc) + timedelta(days=settings.REPORT_LINK_EXPIRY_DAYS)
    ).isoformat()
