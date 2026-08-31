"""Excused (early) leave — استئذان — recorded only by the deputy."""
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._mixins import TimestampMixin, UUIDPkMixin


class ExcusedLeave(UUIDPkMixin, TimestampMixin, Base):
    """استئذان — صلاحية حصرية للوكيل."""
    __tablename__ = "excused_leaves"

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"), index=True
    )
    section_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sections.id", ondelete="SET NULL"), index=True
    )
    date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    requested_at: Mapped[str] = mapped_column(String(20), nullable=False)
    exit_time: Mapped[str] = mapped_column(String(10), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    guardian_name: Mapped[str] = mapped_column(String(255), nullable=False)
    guardian_relation: Mapped[str] = mapped_column(String(30), nullable=False)
    guardian_phone: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1000))
    recorded_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )


__all__ = ["ExcusedLeave"]
