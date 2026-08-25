"""Shared mixins for ORM models."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, declarative_mixin

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@declarative_mixin  # ✅ أضف هذا الديكوريتور
class UUIDPkMixin:
    """UUID primary key column."""

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )


@declarative_mixin  # ✅ أضف هذا الديكوريتور
class TimestampMixin:
    """created_at / updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )
