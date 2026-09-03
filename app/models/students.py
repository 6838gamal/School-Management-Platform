"""
Student models.

Student is the person record. StudentEnrollment tracks the history of
which section/grade a student belongs to over time, enabling transfers
without losing history.
"""
from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from app.core.database import Base
from app.models._mixins import TimestampMixin, UUIDPkMixin


class Student(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "students"

    # ============================================================
    # المعرفات (بدون Foreign Keys) - حسب طلبك
    # ============================================================
    school_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    
    # ============================================================
    # ✅ الحقول الأكاديمية (بدون Foreign Keys)
    # ============================================================
    year_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True, comment="معرف السنة الدراسية"
    )
    grade_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True, comment="معرف الصف"
    )
    section_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True, comment="معرف الشعبة"
    )
    
    # ============================================================
    # ✅ إضافة حقل حالة الحضور (مهم للفلترة)
    # ============================================================
    attendance_status: Mapped[str | None] = mapped_column(
        String(20), 
        nullable=True, 
        default="present",
        comment="حالة الحضور: present, absent, late, permitted, excused"
    )
    
    attendance_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, 
        nullable=True,
        comment="تاريخ آخر تحديث لحالة الحضور"
    )
    
    # ============================================================
    # معلومات الطالب الأساسية
    # ============================================================
    student_number: Mapped[str] = mapped_column(
        String(50), index=True, nullable=False
    )
    national_id: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    
    # الاسم
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    first_name_ar: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name_ar: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # المعلومات الشخصية
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)  # male / female / ذكر / أنثى
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # معلومات ولي الأمر
    guardian_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    guardian_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    guardian_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    guardian_relation: Mapped[str | None] = mapped_column(String(50), nullable=True)  # أب / أم / ولي
    
    # معلومات الاتصال
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # ============================================================
    # الحالة والتفعيل
    # ============================================================
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enrollment_status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # active / transferred / graduated / left
    
    # ============================================================
    # الخصائص المحسوبة (Hybrid Properties)
    # ============================================================
    
    @hybrid_property
    def full_name(self) -> str:
        """إرجاع الاسم الكامل للطالب (بالإنجليزية)"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return ""
    
    @full_name.expression
    def full_name(cls):
        """للاستخدام في استعلامات SQL"""
        return func.concat(cls.first_name, " ", cls.last_name)
    
    @hybrid_property
    def full_name_ar(self) -> str:
        """إرجاع الاسم الكامل للطالب (بالعربية)"""
        if self.first_name_ar and self.last_name_ar:
            return f"{self.first_name_ar} {self.last_name_ar}".strip()
        return self.full_name
    
    @full_name_ar.expression
    def full_name_ar(cls):
        """للاستخدام في استعلامات SQL"""
        return func.concat(cls.first_name_ar, " ", cls.last_name_ar)
    
    @property
    def display_name(self) -> str:
        """اسم الطالب مع رقم الطالب للعرض"""
        return f"{self.full_name} ({self.student_number})"
    
    @property
    def display_name_ar(self) -> str:
        """اسم الطالب بالعربية مع رقم الطالب للعرض"""
        name = self.full_name_ar or self.full_name
        return f"{name} ({self.student_number})"
    
    @property
    def age(self) -> int | None:
        """حساب عمر الطالب بالسنة"""
        if not self.birth_date:
            return None
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )
    
    @property
    def attendance_label(self) -> str:
        """الحصول على تسمية حالة الحضور بالعربية"""
        labels = {
            'present': 'حاضر',
            'absent': 'غائب',
            'late': 'متأخر',
            'permitted': 'مستأذن',
            'excused': 'معذور'
        }
        return labels.get(self.attendance_status, 'غير محدد')
    
    @property
    def attendance_color(self) -> str:
        """الحصول على لون حالة الحضور"""
        colors = {
            'present': 'emerald',
            'absent': 'red',
            'late': 'amber',
            'permitted': 'blue',
            'excused': 'purple'
        }
        return colors.get(self.attendance_status, 'gray')
    
    def __repr__(self) -> str:
        return f"<Student {self.full_name} ({self.student_number})>"


class StudentEnrollment(UUIDPkMixin, TimestampMixin, Base):
    """Tracks a student's placement in a section for a given academic year."""
    __tablename__ = "student_enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "year_id", name="uq_enrollment_student_year"),
    )

    # ============================================================
    # المعرفات (بدون Foreign Keys)
    # ============================================================
    student_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    school_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    year_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    section_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    grade_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    
    # ============================================================
    # معلومات التسجيل
    # ============================================================
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # active / transferred / graduated / left / dropped
    
    enrolled_at: Mapped[date] = mapped_column(
        Date, nullable=False, default=date.today
    )
    
    ended_at: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )
    
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ============================================================
    # الخصائص المحسوبة
    # ============================================================
    
    @property
    def is_current(self) -> bool:
        """هل هذا التسجيل هو التسجيل الحالي للطالب"""
        return self.status == "active" and self.ended_at is None
    
    @property
    def enrollment_duration(self) -> int | None:
        """مدة التسجيل بالأيام"""
        if not self.enrolled_at:
            return None
        end_date = self.ended_at or date.today()
        return (end_date - self.enrolled_at).days
    
    def __repr__(self) -> str:
        return f"<StudentEnrollment student={self.student_id} year={self.year_id} status={self.status}>"


__all__ = [
    "Student",
    "StudentEnrollment"
]
