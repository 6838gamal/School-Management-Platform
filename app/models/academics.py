"""
Academic structure models.

Hierarchy: School → AcademicYear → Stage → Grade → Section
Also: Subject (shared within a school), Room, Period.
"""
from sqlalchemy import Boolean, Integer, String, UniqueConstraint, Float, Text, Date
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._mixins import TimestampMixin, UUIDPkMixin


# ============================================================
#  السنة الدراسية (بدون علاقات)
# ============================================================

class AcademicYear(UUIDPkMixin, TimestampMixin, Base):
    """السنة الدراسية"""
    __tablename__ = "academic_years"

    # الحقول الأساسية (بدون Foreign Keys)
    school_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[str] = mapped_column(String(20), nullable=False)
    end_date: Mapped[str] = mapped_column(String(20), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ❌ تم إزالة جميع العلاقات
    # stages: Mapped[list["Stage"]] = relationship(...)
    # grades: Mapped[list["Grade"]] = relationship(...)

    def __repr__(self) -> str:
        return f"<AcademicYear {self.name}>"


# ============================================================
#  المرحلة (بدون علاقات)
# ============================================================

class Stage(UUIDPkMixin, TimestampMixin, Base):
    """المرحلة التعليمية: ابتدائي، متوسط، ثانوي"""
    __tablename__ = "stages"
    __table_args__ = (
        UniqueConstraint("school_id", "year_id", "name", name="uq_stage_school_year_name"),
    )

    # الحقول الأساسية (بدون Foreign Keys)
    school_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    year_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(100))
    order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ❌ تم إزالة جميع العلاقات
    # year: Mapped["AcademicYear"] = relationship(...)
    # grades: Mapped[list["Grade"]] = relationship(...)

    def __repr__(self) -> str:
        return f"<Stage {self.name}>"


# ============================================================
#  الصف (بدون علاقات)
# ============================================================

class Grade(UUIDPkMixin, TimestampMixin, Base):
    """الصف الدراسي: الصف الأول، الصف الثاني"""
    __tablename__ = "grades"
    __table_args__ = (
        UniqueConstraint("stage_id", "year_id", "name", name="uq_grade_stage_year_name"),
    )

    # الحقول الأساسية (بدون Foreign Keys)
    school_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    stage_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    year_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(100))
    order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ❌ تم إزالة جميع العلاقات
    # stage: Mapped["Stage"] = relationship(...)
    # year: Mapped["AcademicYear"] = relationship(...)
    # sections: Mapped[list["Section"]] = relationship(...)

    def __repr__(self) -> str:
        return f"<Grade {self.name}>"


# ============================================================
#  الشعبة (بدون علاقات)
# ============================================================

class Section(UUIDPkMixin, TimestampMixin, Base):
    """الشعبة: 1-A، 1-B"""
    __tablename__ = "sections"
    __table_args__ = (
        UniqueConstraint("grade_id", "name", name="uq_section_grade_name"),
    )

    # الحقول الأساسية (بدون Foreign Keys)
    school_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    grade_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    year_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False, comment="معرف السنة الدراسية"
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # ✅ معلمون رؤساء الفصل (مخزنة كنص مفصول بفواصل)
    class_teacher_ids: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="معرفات المعلمين رؤساء الفصل مفصولة بفواصل"
    )

    # ❌ تم إزالة جميع العلاقات
    # grade: Mapped["Grade"] = relationship(...)

    # ============================================================
    # دوال مساعدة للتعامل مع معلمي الفصل
    # ============================================================
    
    @property
    def class_teacher_list(self) -> list[str]:
        """الحصول على قائمة معرفات معلمي الفصل"""
        if not self.class_teacher_ids:
            return []
        return [tid.strip() for tid in self.class_teacher_ids.split(',') if tid.strip()]
    
    def set_class_teachers(self, teacher_ids: list[str]):
        """تعيين قائمة معلمي الفصل"""
        if teacher_ids:
            self.class_teacher_ids = ','.join(teacher_ids)
        else:
            self.class_teacher_ids = None
    
    def add_class_teacher(self, teacher_id: str):
        """إضافة معلم فصل جديد"""
        current = self.class_teacher_list
        if teacher_id not in current:
            current.append(teacher_id)
            self.set_class_teachers(current)
    
    def remove_class_teacher(self, teacher_id: str):
        """إزالة معلم فصل"""
        current = self.class_teacher_list
        if teacher_id in current:
            current.remove(teacher_id)
            self.set_class_teachers(current)
    
    def __repr__(self) -> str:
        return f"<Section {self.name}>"


# ============================================================
#  المادة (بدون علاقات)
# ============================================================

class Subject(UUIDPkMixin, TimestampMixin, Base):
    """المادة الدراسية"""
    __tablename__ = "subjects"
    __table_args__ = (
        UniqueConstraint("school_id", "name", name="uq_subject_school_name"),
    )

    # الحقول الأساسية (بدون Foreign Keys)
    school_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(100))
    code: Mapped[str | None] = mapped_column(String(20))
    color: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ❌ تم إزالة جميع العلاقات

    def __repr__(self) -> str:
        return f"<Subject {self.name}>"


# ============================================================
#  القاعة (بدون علاقات)
# ============================================================

class Room(UUIDPkMixin, TimestampMixin, Base):
    """القاعة الدراسية"""
    __tablename__ = "rooms"
    __table_args__ = (
        UniqueConstraint("school_id", "name", name="uq_room_school_name"),
    )

    # الحقول الأساسية (بدون Foreign Keys)
    school_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    building: Mapped[str | None] = mapped_column(String(100))
    floor: Mapped[str | None] = mapped_column(String(20))
    capacity: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ❌ تم إزالة جميع العلاقات

    def __repr__(self) -> str:
        return f"<Room {self.name}>"


# ============================================================
#  الحصة (بدون علاقات)
# ============================================================

class Period(UUIDPkMixin, TimestampMixin, Base):
    """الحصة الزمنية في اليوم الدراسي"""
    __tablename__ = "periods"
    __table_args__ = (
        UniqueConstraint("school_id", "order", name="uq_period_school_order"),
    )

    # الحقول الأساسية (بدون Foreign Keys)
    school_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[str] = mapped_column(String(10), nullable=False)
    end_time: Mapped[str] = mapped_column(String(10), nullable=False)
    is_break: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ❌ تم إزالة جميع العلاقات

    def __repr__(self) -> str:
        return f"<Period {self.name} ({self.start_time}-{self.end_time})>"


# ============================================================
#  التصدير
# ============================================================

__all__ = [
    "AcademicYear",
    "Stage",
    "Grade",
    "Section",
    "Subject",
    "Room",
    "Period",
]
