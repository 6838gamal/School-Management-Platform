"""Attendance models for students and teachers."""
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base  # ✅ أضف هذا الاستيراد
from app.models._mixins import TimestampMixin, UUIDPkMixin


class StudentAttendance(UUIDPkMixin, TimestampMixin, Base):  # ✅ أضف Base
    __tablename__ = "student_attendance"
    __table_args__ = (
        UniqueConstraint("student_id", "date", "period_id", name="uq_student_att_day_period"),
    )

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"), index=True
    )
    section_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sections.id", ondelete="SET NULL"), index=True
    )
    schedule_entry_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("schedule_entries.id", ondelete="SET NULL"), index=True
    )
    period_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("periods.id", ondelete="SET NULL"), index=True
    )
    date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # YYYY-MM-DD
    status: Mapped[str] = mapped_column(String(15), nullable=False)  # present/absent/late/excused
    note: Mapped[str | None] = mapped_column(String(500))
    recorded_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )


class TeacherAttendance(UUIDPkMixin, TimestampMixin, Base):  # ✅ أضف Base
    __tablename__ = "teacher_attendance"
    __table_args__ = (
        UniqueConstraint("teacher_id", "date", name="uq_teacher_att_day"),
    )

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    teacher_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teachers.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False)  # present/absent/late/leave
    note: Mapped[str | None] = mapped_column(String(500))
    recorded_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )


# ✅ أضف هذا في نهاية الملف
__all__ = [
    "StudentAttendance",
    "TeacherAttendance"
]
