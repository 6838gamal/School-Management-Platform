"""
Student models.

Student is the person record. StudentEnrollment tracks the history of
which section/grade a student belongs to over time, enabling transfers
without losing history.
"""
from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base  # ✅ أضف هذا الاستيراد
from app.models._mixins import TimestampMixin, UUIDPkMixin


class Student(UUIDPkMixin, TimestampMixin, Base):  # ✅ أضف Base
    __tablename__ = "students"

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    student_number: Mapped[str] = mapped_column(String(50), index=True)
    national_id: Mapped[str | None] = mapped_column(String(50))
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(10))  # male / female
    birth_date: Mapped[str | None] = mapped_column(String(20))
    guardian_name: Mapped[str | None] = mapped_column(String(255))
    guardian_phone: Mapped[str | None] = mapped_column(String(50))
    guardian_email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(String(500))
    photo_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    enrollments: Mapped[list["StudentEnrollment"]] = relationship(
        "StudentEnrollment", back_populates="student", cascade="all, delete-orphan"
    )


class StudentEnrollment(UUIDPkMixin, TimestampMixin, Base):  # ✅ أضف Base
    """Tracks a student's placement in a section for a given academic year."""
    __tablename__ = "student_enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "year_id", name="uq_enrollment_student_year"),
    )

    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"), index=True
    )
    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    year_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("academic_years.id", ondelete="CASCADE"), index=True
    )
    section_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sections.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active")  # active/transferred/graduated/left
    enrolled_at: Mapped[str] = mapped_column(String(20))
    ended_at: Mapped[str | None] = mapped_column(String(20))

    student: Mapped["Student"] = relationship("Student", back_populates="enrollments")


# ✅ أضف هذا في نهاية الملف
__all__ = [
    "Student",
    "StudentEnrollment"
]
