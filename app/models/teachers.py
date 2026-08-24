"""
Teacher models.

Teacher is the person record (linked to a User for login).
TeacherAssignment tracks which subject/section a teacher is assigned to,
preserving history when assignments change.
"""
from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models._mixins import TimestampMixin, UUIDPkMixin


class Teacher(UUIDPkMixin, TimestampMixin):
    __tablename__ = "teachers"

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    employee_number: Mapped[str] = mapped_column(String(50), index=True)
    national_id: Mapped[str | None] = mapped_column(String(50))
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(10))
    phone: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))
    specialization: Mapped[str | None] = mapped_column(String(200))
    qualification: Mapped[str | None] = mapped_column(String(200))
    hire_date: Mapped[str | None] = mapped_column(String(20))
    photo_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    assignments: Mapped[list["TeacherAssignment"]] = relationship(
        "TeacherAssignment", back_populates="teacher", cascade="all, delete-orphan"
    )


class TeacherAssignment(UUIDPkMixin, TimestampMixin):
    """Tracks a teacher's assignment to a subject + section for a year."""
    __tablename__ = "teacher_assignments"
    __table_args__ = (
        UniqueConstraint("teacher_id", "subject_id", "section_id", "year_id", name="uq_teacher_assign"),
    )

    teacher_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teachers.id", ondelete="CASCADE"), index=True
    )
    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    subject_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )
    section_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sections.id", ondelete="CASCADE"), index=True
    )
    year_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("academic_years.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active")  # active/ended
    assigned_at: Mapped[str] = mapped_column(String(20))
    ended_at: Mapped[str | None] = mapped_column(String(20))

    teacher: Mapped["Teacher"] = relationship("Teacher", back_populates="assignments")
