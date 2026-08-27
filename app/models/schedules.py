"""Schedule models."""
from sqlalchemy import ForeignKey, Integer, String, Boolean, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import TimestampMixin, UUIDPkMixin


class Schedule(UUIDPkMixin, TimestampMixin, Base):
    """جدول دراسي"""
    __tablename__ = "schedules"
    __table_args__ = (
        UniqueConstraint("school_id", "section_id", "academic_year_id", name="uq_schedule_section_year"),
    )

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    section_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sections.id", ondelete="CASCADE"), index=True
    )
    academic_year_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("academic_years.id", ondelete="CASCADE"), index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # العلاقات
    entries: Mapped[list["ScheduleEntry"]] = relationship(
        "ScheduleEntry", back_populates="schedule", cascade="all, delete-orphan"
    )


class ScheduleEntry(UUIDPkMixin, TimestampMixin, Base):
    """مدخل في الجدول الدراسي (حصة واحدة)"""
    __tablename__ = "schedule_entries"
    __table_args__ = (
        UniqueConstraint(
            "schedule_id", "day_of_week", "period_id", 
            name="uq_schedule_day_period"
        ),
    )

    schedule_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schedules.id", ondelete="CASCADE"), index=True
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=الأحد, 1=الإثنين, ...
    period_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("periods.id", ondelete="CASCADE"), index=True
    )
    subject_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )
    teacher_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    room_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rooms.id", ondelete="CASCADE"), index=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # العلاقات
    schedule: Mapped["Schedule"] = relationship("Schedule", back_populates="entries")
