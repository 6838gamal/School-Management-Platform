"""Grade models: Assessment (definition) and GradeRecord (student score)."""
from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base  # ✅ أضف هذا الاستيراد
from app.models._mixins import TimestampMixin, UUIDPkMixin


class Assessment(UUIDPkMixin, TimestampMixin, Base):  # ✅ أضف Base
    """An assessment definition: exam, quiz, assignment, homework, participation, activity."""
    __tablename__ = "assessments"

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    year_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("academic_years.id", ondelete="CASCADE"), index=True
    )
    section_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sections.id", ondelete="CASCADE"), index=True
    )
    subject_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )
    teacher_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("teachers.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    assessment_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # exam / quiz / assignment / homework / activity / participation
    max_score: Mapped[float] = mapped_column(Numeric(6, 2), default=100)
    passing_score: Mapped[float] = mapped_column(Numeric(6, 2), default=50)
    weight: Mapped[float] = mapped_column(Numeric(5, 2), default=1.0)
    date: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(String(1000))

    grade_records: Mapped[list["GradeRecord"]] = relationship(
        "GradeRecord", back_populates="assessment", cascade="all, delete-orphan"
    )


class GradeRecord(UUIDPkMixin, TimestampMixin, Base):  # ✅ أضف Base
    __tablename__ = "grade_records"
    __table_args__ = (
        UniqueConstraint("assessment_id", "student_id", name="uq_grade_assessment_student"),
    )

    assessment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assessments.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"), index=True
    )
    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    note: Mapped[str | None] = mapped_column(String(500))
    graded_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )

    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="grade_records")


# ✅ أضف هذا في نهاية الملف
__all__ = [
    "Assessment",
    "GradeRecord"
]
