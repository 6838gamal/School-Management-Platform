"""Audit log model — append-only history for sensitive operations."""
from sqlalchemy import ForeignKey, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._mixins import TimestampMixin, UUIDPkMixin


class AuditLog(UUIDPkMixin, TimestampMixin, Base):
    """سجل تدقيق — غير قابل للتعديل بعد الكتابة."""
    __tablename__ = "audit_log"

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    actor_role: Mapped[str | None] = mapped_column(String(50), index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), index=True)
    details: Mapped[str | None] = mapped_column(Text)
    extra: Mapped[dict | None] = mapped_column(JSON)

    __all__ = ["AuditLog"]
