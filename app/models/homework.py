"""Homework models."""
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models._mixins import TimestampMixin, UUIDPkMixin


class Homework(UUIDPkMixin, TimestampMixin):
    __tablename__ = "homework"

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    section_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sections.id", ondelete="CASCADE"), index=True
    )
    subject_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )
    teacher_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teachers.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    due_date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    is_graded: Mapped[bool] = mapped_column(Boolean, default=False)
    max_score: Mapped[float] = mapped_column(default=10.0)


class HomeworkSubmission(UUIDPkMixin, TimestampMixin):
    __tablename__ = "homework_submissions"
    __table_args__ = (
        # one submission per student per homework
    )

    homework_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("homework.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/submitted/graded/late
    submitted_at: Mapped[str | None] = mapped_column(String(20))
    score: Mapped[float | None] = mapped_column()
    note: Mapped[str | None] = mapped_column(String(500))
