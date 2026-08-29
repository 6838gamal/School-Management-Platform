"""
Academic structure models.

Hierarchy: School → AcademicYear → Stage → Grade → Section
Also: Subject (shared within a school), Room, Period.
"""
from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint, Float, Text, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import TimestampMixin, UUIDPkMixin


class AcademicYear(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "academic_years"

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[str] = mapped_column(String(20), nullable=False)
    end_date: Mapped[str] = mapped_column(String(20), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    stages: Mapped[list["Stage"]] = relationship("Stage", back_populates="year", cascade="all, delete-orphan")


class Stage(UUIDPkMixin, TimestampMixin, Base):
    """Educational stage, e.g. Primary, Middle, Secondary."""
    __tablename__ = "stages"
    __table_args__ = (UniqueConstraint("school_id", "year_id", "name", name="uq_stage_school_year_name"),)

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    year_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("academic_years.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(100))
    order: Mapped[int] = mapped_column(Integer, default=0)

    year: Mapped["AcademicYear"] = relationship("AcademicYear", back_populates="stages")
    grades: Mapped[list["Grade"]] = relationship("Grade", back_populates="stage", cascade="all, delete-orphan")


class Grade(UUIDPkMixin, TimestampMixin, Base):
    """Grade level within a stage, e.g. Grade 1, Grade 2."""
    __tablename__ = "grades"
    __table_args__ = (UniqueConstraint("stage_id", "name", name="uq_grade_stage_name"),)

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    stage_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stages.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(100))
    order: Mapped[int] = mapped_column(Integer, default=0)

    stage: Mapped["Stage"] = relationship("Stage", back_populates="grades")
    sections: Mapped[list["Section"]] = relationship("Section", back_populates="grade", cascade="all, delete-orphan")


class Section(UUIDPkMixin, TimestampMixin, Base):
    """Section within a grade, e.g. 1-A, 1-B."""
    __tablename__ = "sections"
    __table_args__ = (UniqueConstraint("grade_id", "name", name="uq_section_grade_name"),)

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    grade_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("grades.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    grade: Mapped["Grade"] = relationship("Grade", back_populates="sections")


class Subject(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "subjects"
    __table_args__ = (UniqueConstraint("school_id", "name", name="uq_subject_school_name"),)

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(100))
    code: Mapped[str | None] = mapped_column(String(20))
    color: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Room(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "rooms"
    __table_args__ = (UniqueConstraint("school_id", "name", name="uq_room_school_name"),)

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    building: Mapped[str | None] = mapped_column(String(100))
    floor: Mapped[str | None] = mapped_column(String(20))
    capacity: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Period(UUIDPkMixin, TimestampMixin, Base):
    """A time slot in the school day, e.g. Period 1: 07:00-07:45."""
    __tablename__ = "periods"
    __table_args__ = (UniqueConstraint("school_id", "order", name="uq_period_school_order"),)

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[str] = mapped_column(String(10), nullable=False)
    end_time: Mapped[str] = mapped_column(String(10), nullable=False)
    is_break: Mapped[bool] = mapped_column(Boolean, default=False)


# ✅ ============================================
# ✅ نموذج التقييمات (Assessment)
# ✅ ============================================
class Assessment(UUIDPkMixin, TimestampMixin, Base):
    """نموذج التقييمات والاختبارات"""
    __tablename__ = "assessments"

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    section_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sections.id", ondelete="CASCADE"), index=True
    )
    subject_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )
    teacher_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    year_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("academic_years.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    assessment_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # exam, quiz, assignment, homework, activity, participation
    max_score: Mapped[float] = mapped_column(Float, default=100.0)
    passing_score: Mapped[float | None] = mapped_column(Float, default=50.0)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    date: Mapped[str | None] = mapped_column(String(20))

    # العلاقات (اختيارية - يمكن إضافتها عند الحاجة)
    # section: Mapped["Section"] = relationship("Section", back_populates="assessments")
    # subject: Mapped["Subject"] = relationship("Subject", back_populates="assessments")
    # teacher: Mapped["User"] = relationship("User", back_populates="assessments")


# ✅ تحديث __all__
__all__ = [
    "AcademicYear",
    "Stage",
    "Grade",
    "Section",
    "Subject",
    "Room",
    "Period",
    "Assessment",  # ✅ أضف هذا
]
