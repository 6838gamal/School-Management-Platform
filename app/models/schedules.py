"""Schedule models."""
from sqlalchemy import ForeignKey, Integer, String, Boolean, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import TimestampMixin, UUIDPkMixin


class Schedule(UUIDPkMixin, TimestampMixin, Base):
    """جدول دراسي"""
    __tablename__ = "schedules"
    __table_args__ = (
        UniqueConstraint("school_id", "section_id", "year_id", name="uq_schedule_section_year"),
    )

    school_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    section_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    # ✅ العمود الفعلي في قاعدة البيانات هو year_id
    year_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # العلاقة مع المدخلات
    entries: Mapped[list["ScheduleEntry"]] = relationship(
        "ScheduleEntry", back_populates="schedule", cascade="all, delete-orphan"
    )

    # ============= Property للتوافق مع الكود =============
    @property
    def academic_year_id(self) -> str:
        """Alias للتوافق مع الكود الذي يستخدم academic_year_id"""
        return self.year_id
    
    @academic_year_id.setter
    def academic_year_id(self, value: str) -> None:
        """Setter للتوافق مع الكود الذي يستخدم academic_year_id"""
        self.year_id = value


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
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    period_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    subject_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    teacher_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    room_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # العلاقات
    schedule: Mapped["Schedule"] = relationship("Schedule", back_populates="entries")
