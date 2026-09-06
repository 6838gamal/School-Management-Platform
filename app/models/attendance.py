"""Attendance models for students and teachers."""
from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.core.database import Base
from app.models._mixins import TimestampMixin, UUIDPkMixin


# ============================================================
#  Enums (لحالات الحضور)
# ============================================================

class StudentAttendanceStatus(str, enum.Enum):
    """حالات حضور الطالب"""
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"
    
    @classmethod
    def get_arabic_name(cls, value: str) -> str:
        """الحصول على الاسم العربي للحالة"""
        mapping = {
            cls.PRESENT: "حاضر",
            cls.ABSENT: "غائب",
            cls.LATE: "متأخر",
            cls.EXCUSED: "معذور",
        }
        return mapping.get(value, value)
    
    @classmethod
    def get_color(cls, value: str) -> str:
        """الحصول على لون الحالة"""
        mapping = {
            cls.PRESENT: "success",
            cls.ABSENT: "danger",
            cls.LATE: "warning",
            cls.EXCUSED: "info",
        }
        return mapping.get(value, "secondary")
    
    @classmethod
    def get_badge_class(cls, value: str) -> str:
        """الحصول على كلاس البادج للحالة"""
        mapping = {
            cls.PRESENT: "bg-green-100 text-green-700",
            cls.ABSENT: "bg-red-100 text-red-700",
            cls.LATE: "bg-yellow-100 text-yellow-700",
            cls.EXCUSED: "bg-blue-100 text-blue-700",
        }
        return mapping.get(value, "bg-slate-100 text-slate-700")


class TeacherAttendanceStatus(str, enum.Enum):
    """حالات حضور المعلم"""
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    LEAVE = "leave"  # إجازة
    
    @classmethod
    def get_arabic_name(cls, value: str) -> str:
        """الحصول على الاسم العربي للحالة"""
        mapping = {
            cls.PRESENT: "حاضر",
            cls.ABSENT: "غائب",
            cls.LATE: "متأخر",
            cls.LEAVE: "إجازة",
        }
        return mapping.get(value, value)
    
    @classmethod
    def get_color(cls, value: str) -> str:
        """الحصول على لون الحالة"""
        mapping = {
            cls.PRESENT: "success",
            cls.ABSENT: "danger",
            cls.LATE: "warning",
            cls.LEAVE: "secondary",
        }
        return mapping.get(value, "secondary")


# ============================================================
#  نموذج حضور الطلاب (بدون علاقات)
# ============================================================

class StudentAttendance(UUIDPkMixin, TimestampMixin, Base):
    """سجل حضور الطلاب"""
    __tablename__ = "student_attendance"
    __table_args__ = (
        UniqueConstraint("student_id", "date", "period_id", name="uq_student_att_day_period"),
    )

    # --- الحقول الأساسية (بدون Foreign Keys) ---
    school_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    student_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    
    # --- الحقول الأكاديمية (بدون Foreign Keys) ---
    section_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    grade_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    stage_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    year_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    
    # --- الحقول الزمنية (بدون Foreign Keys) ---
    period_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    schedule_entry_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    # --- الحالة والملاحظات ---
    status: Mapped[str] = mapped_column(String(15), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500))
    
    # --- من سجل (بدون Foreign Keys) ---
    recorded_by: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    
    # ❌ تم إزالة جميع العلاقات (relationships)
    # ❌ student = relationship(...)
    # ❌ section = relationship(...)
    # ❌ grade = relationship(...)
    # ❌ stage = relationship(...)
    # ❌ year = relationship(...)
    # ❌ period = relationship(...)
    # ❌ recorder = relationship(...)
    
    # ============================================================
    # دوال مساعدة للخصائص المحسوبة
    # ============================================================
    
    @property
    def status_arabic(self) -> str:
        """الحصول على اسم الحالة بالعربية"""
        return StudentAttendanceStatus.get_arabic_name(self.status)
    
    @property
    def status_color(self) -> str:
        """الحصول على لون الحالة"""
        return StudentAttendanceStatus.get_color(self.status)
    
    @property
    def status_badge(self) -> str:
        """الحصول على كلاس البادج للحالة"""
        return StudentAttendanceStatus.get_badge_class(self.status)
    
    @property
    def is_present(self) -> bool:
        """هل الطالب حاضر؟"""
        return self.status == StudentAttendanceStatus.PRESENT
    
    @property
    def is_absent(self) -> bool:
        """هل الطالب غائب؟"""
        return self.status == StudentAttendanceStatus.ABSENT
    
    @property
    def is_late(self) -> bool:
        """هل الطالب متأخر؟"""
        return self.status == StudentAttendanceStatus.LATE
    
    @property
    def is_excused(self) -> bool:
        """هل الطالب معذور؟"""
        return self.status == StudentAttendanceStatus.EXCUSED
    
    def __repr__(self) -> str:
        return f"<StudentAttendance student={self.student_id} date={self.date} status={self.status}>"


# ============================================================
#  نموذج حضور المعلمين (بدون علاقات)
# ============================================================

class TeacherAttendance(UUIDPkMixin, TimestampMixin, Base):
    """سجل حضور المعلمين"""
    __tablename__ = "teacher_attendance"
    __table_args__ = (
        UniqueConstraint("teacher_id", "date", name="uq_teacher_att_day"),
    )

    # --- الحقول الأساسية (بدون Foreign Keys) ---
    school_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    teacher_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    
    # --- الحقول الأكاديمية (بدون Foreign Keys) ---
    section_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    grade_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    stage_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    year_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    
    # --- الحقول الزمنية (بدون Foreign Keys) ---
    date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    period_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    
    # --- الحالة والملاحظات ---
    status: Mapped[str] = mapped_column(String(15), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500))
    
    # --- من سجل (بدون Foreign Keys) ---
    recorded_by: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    
    # ❌ تم إزالة جميع العلاقات (relationships)
    # ❌ teacher = relationship(...)
    # ❌ section = relationship(...)
    # ❌ grade = relationship(...)
    # ❌ stage = relationship(...)
    # ❌ year = relationship(...)
    # ❌ period = relationship(...)
    # ❌ recorder = relationship(...)
    
    # ============================================================
    # دوال مساعدة للخصائص المحسوبة
    # ============================================================
    
    @property
    def status_arabic(self) -> str:
        """الحصول على اسم الحالة بالعربية"""
        return TeacherAttendanceStatus.get_arabic_name(self.status)
    
    @property
    def status_color(self) -> str:
        """الحصول على لون الحالة"""
        return TeacherAttendanceStatus.get_color(self.status)
    
    @property
    def is_present(self) -> bool:
        """هل المعلم حاضر؟"""
        return self.status == TeacherAttendanceStatus.PRESENT
    
    @property
    def is_absent(self) -> bool:
        """هل المعلم غائب؟"""
        return self.status == TeacherAttendanceStatus.ABSENT
    
    @property
    def is_late(self) -> bool:
        """هل المعلم متأخر؟"""
        return self.status == TeacherAttendanceStatus.LATE
    
    @property
    def is_on_leave(self) -> bool:
        """هل المعلم في إجازة؟"""
        return self.status == TeacherAttendanceStatus.LEAVE
    
    def __repr__(self) -> str:
        return f"<TeacherAttendance teacher={self.teacher_id} date={self.date} status={self.status}>"


# ============================================================
#  نموذج إحصائيات الحضور (بدون علاقات)
# ============================================================

class AttendanceSummary(UUIDPkMixin, TimestampMixin, Base):
    """ملخص إحصائيات الحضور (للتقارير السريعة)"""
    __tablename__ = "attendance_summaries"
    __table_args__ = (
        UniqueConstraint("school_id", "date", "section_id", name="uq_att_summary_day_section"),
    )

    # --- الحقول الأساسية (بدون Foreign Keys) ---
    school_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    # --- التصنيفات (بدون Foreign Keys) ---
    section_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    grade_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    stage_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    year_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    
    # --- الطلاب ---
    total_students: Mapped[int] = mapped_column(default=0)
    present_students: Mapped[int] = mapped_column(default=0)
    absent_students: Mapped[int] = mapped_column(default=0)
    late_students: Mapped[int] = mapped_column(default=0)
    excused_students: Mapped[int] = mapped_column(default=0)
    attendance_percentage: Mapped[float] = mapped_column(default=0.0)
    
    # --- المعلمين ---
    total_teachers: Mapped[int] = mapped_column(default=0)
    present_teachers: Mapped[int] = mapped_column(default=0)
    absent_teachers: Mapped[int] = mapped_column(default=0)
    late_teachers: Mapped[int] = mapped_column(default=0)
    leave_teachers: Mapped[int] = mapped_column(default=0)
    teacher_percentage: Mapped[float] = mapped_column(default=0.0)
    
    # ❌ تم إزالة جميع العلاقات (relationships)
    # ❌ section = relationship(...)
    # ❌ grade = relationship(...)
    # ❌ stage = relationship(...)
    # ❌ year = relationship(...)
    
    # ============================================================
    # دوال مساعدة
    # ============================================================
    
    @property
    def present_percentage(self) -> float:
        """نسبة الحضور للطلاب"""
        return round((self.present_students / self.total_students * 100) if self.total_students > 0 else 0, 1)
    
    @property
    def absent_percentage(self) -> float:
        """نسبة الغياب للطلاب"""
        return round((self.absent_students / self.total_students * 100) if self.total_students > 0 else 0, 1)
    
    @property
    def teacher_present_percentage(self) -> float:
        """نسبة الحضور للمعلمين"""
        return round((self.present_teachers / self.total_teachers * 100) if self.total_teachers > 0 else 0, 1)
    
    def __repr__(self) -> str:
        return f"<AttendanceSummary date={self.date} section={self.section_id}>"


# ============================================================
#  نموذج سجل التغييرات (بدون علاقات)
# ============================================================

class AttendanceAuditLog(UUIDPkMixin, TimestampMixin, Base):
    """سجل تغييرات الحضور (للتدقيق)"""
    __tablename__ = "attendance_audit_logs"
    
    # --- الحقول الأساسية (بدون Foreign Keys) ---
    school_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    attendance_type: Mapped[str] = mapped_column(String(20), nullable=False)
    attendance_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    old_data: Mapped[str | None] = mapped_column(String(1000))
    new_data: Mapped[str | None] = mapped_column(String(1000))
    changed_by: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    
    # ❌ تم إزالة جميع العلاقات (relationships)
    # ❌ user = relationship(...)
    
    def __repr__(self) -> str:
        return f"<AttendanceAuditLog type={self.attendance_type} action={self.action}>"


# ============================================================
#  التصدير
# ============================================================

__all__ = [
    "StudentAttendance",
    "TeacherAttendance",
    "AttendanceSummary",
    "AttendanceAuditLog",
    "StudentAttendanceStatus",
    "TeacherAttendanceStatus",
]
