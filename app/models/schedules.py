"""Schedule models: Schedule (weekly grid) and ScheduleEntry (a lesson slot)."""
from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base  # ✅ أضف هذا الاستيراد
from app.models._mixins import TimestampMixin, UUIDPkMixin


class Schedule(UUIDPkMixin, TimestampMixin, Base):  # ✅ أضف Base
    """A named schedule grid for a section (or teacher view)."""
    __tablename__ = "schedules"

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    year_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("academic_years.id", ondelete="CASCADE"), index=True
    )
    section_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sections.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    entries: Mapped[list["ScheduleEntry"]] = relationship(
        "ScheduleEntry", back_populates="schedule", cascade="all, delete-orphan"
    )


class ScheduleEntry(UUIDPkMixin, TimestampMixin, Base):  # ✅ أضف Base
    """A single lesson in the weekly grid."""
    __tablename__ = "schedule_entries"
    __table_args__ = (
        UniqueConstraint("schedule_id", "day_of_week", "period_id", name="uq_entry_slot"),
    )

    schedule_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schedules.id", ondelete="CASCADE"), index=True
    )
    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Sun .. 6=Sat
    period_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("periods.id", ondelete="CASCADE"), index=True
    )
    subject_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )
    teacher_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teachers.id", ondelete="CASCADE"), index=True
    )
    room_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("rooms.id", ondelete="SET NULL"), index=True
    )
    section_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sections.id", ondelete="CASCADE"), index=True
    )

    schedule: Mapped["Schedule"] = relationship("Schedule", back_populates="entries")


# ✅ أضف هذا في نهاية الملف
__all__ = [
    "Schedule",
    "ScheduleEntry"
]
