"""Report and AuditLog models."""
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base  # ✅ أضف هذا الاستيراد
from app.models._mixins import TimestampMixin, UUIDPkMixin


class ReportLink(UUIDPkMixin, TimestampMixin, Base):  # ✅ أضف Base
    """Secure share link for a generated report."""
    __tablename__ = "report_links"

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    token: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    parameters: Mapped[str | None] = mapped_column(Text)  # JSON
    expires_at: Mapped[str] = mapped_column(String(30), nullable=False)
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    is_active: Mapped[bool] = mapped_column(default=True)


class AuditLog(UUIDPkMixin, TimestampMixin, Base):  # ✅ أضف Base
    __tablename__ = "audit_logs"

    school_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="SET NULL"), index=True
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[str | None] = mapped_column(String(36))
    details: Mapped[str | None] = mapped_column(Text)  # JSON
    ip_address: Mapped[str | None] = mapped_column(String(45))


# ✅ أضف هذا في نهاية الملف
__all__ = [
    "ReportLink",
    "AuditLog"
]
