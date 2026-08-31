"""Substitute assignments — تكليف معلم بديل عند غياب المعلم الأساسي."""
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._mixins import TimestampMixin, UUIDPkMixin


# Allowed transitions for a substitute assignment:
#   pending → accepted | rejected | cancelled
#   accepted → completed | cancelled
SUBSTITUTE_STATUSES = (
    "pending",
    "accepted",
    "rejected",
    "completed",
    "cancelled",
)


class SubstituteAssignment(UUIDPkMixin, TimestampMixin, Base):
    """تكليف معلم بديل — يمر بحالات: pending → accepted → completed."""
    __tablename__ = "substitute_assignments"

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    schedule_entry_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("schedule_entries.id", ondelete="CASCADE"),
        index=True,
    )
    absent_teacher_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teachers.id", ondelete="CASCADE"), index=True
    )
    substitute_teacher_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teachers.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="pending")
    reason: Mapped[str | None] = mapped_column(String(500))
    requested_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    accepted_at: Mapped[str | None] = mapped_column(String(20))
    rejected_at: Mapped[str | None] = mapped_column(String(20))
    completed_at: Mapped[str | None] = mapped_column(String(20))
    cancel_reason: Mapped[str | None] = mapped_column(String(500))

    __all__ = ["SubstituteAssignment", "SUBSTITUTE_STATUSES"]
