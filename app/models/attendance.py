"""Attendance models for students and teachers."""
from sqlalchemy import ForeignKey, String, UniqueConstraint, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
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


class TeacherAttendanceStatus(str, enum.Enum):
    """حالات حضور المعلم"""
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    LEAVE = "leave"  # إجازة


# ============================================================
#  نموذج حضور الطلاب (محدث)
# ============================================================

class StudentAttendance(UUIDPkMixin, TimestampMixin, Base):
    """سجل حضور الطلاب"""
    __tablename__ = "student_attendance"
    __table_args__ = (
        UniqueConstraint("student_id", "date", "period_id", name="uq_student_att_day_period"),
    )

    # --- الحقول الأساسية ---
    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"), index=True
    )
    
    # --- الحقول الأكاديمية (مضافة حديثاً) ---
    section_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sections.id", ondelete="SET NULL"), index=True
    )
    grade_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("grades.id", ondelete="SET NULL"), index=True
    )
    stage_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("stages.id", ondelete="SET NULL"), index=True
    )
    year_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("academic_years.id", ondelete="SET NULL"), index=True
    )
    
    # --- الحقول الزمنية ---
    period_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("periods.id", ondelete="SET NULL"), index=True
    )
    schedule_entry_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("schedule_entries.id", ondelete="SET NULL"), index=True
    )
    date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # YYYY-MM-DD
    
    # --- الحالة والملاحظات ---
    status: Mapped[str] = mapped_column(String(15), nullable=False)  # present/absent/late/excused
    note: Mapped[str | None] = mapped_column(String(500))
    
    # --- من سجل ---
    recorded_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    
    # --- العلاقات (Relationships) ---
    student = relationship("Student", back_populates="attendances")
    section = relationship("Section", back_populates="attendances")
    grade = relationship("Grade")
    stage = relationship("Stage")
    year = relationship("AcademicYear")
    period = relationship("Period")
    recorder = relationship("User", foreign_keys=[recorded_by])


# ============================================================
#  نموذج حضور المعلمين (محدث)
# ============================================================

class TeacherAttendance(UUIDPkMixin, TimestampMixin, Base):
    """سجل حضور المعلمين"""
    __tablename__ = "teacher_attendance"
    __table_args__ = (
        UniqueConstraint("teacher_id", "date", name="uq_teacher_att_day"),
    )

    # --- الحقول الأساسية ---
    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    teacher_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teachers.id", ondelete="CASCADE"), index=True
    )
    
    # --- الحقول الأكاديمية (مضافة حديثاً) ---
    section_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sections.id", ondelete="SET NULL"), index=True
    )
    grade_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("grades.id", ondelete="SET NULL"), index=True
    )
    stage_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("stages.id", ondelete="SET NULL"), index=True
    )
    year_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("academic_years.id", ondelete="SET NULL"), index=True
    )
    
    # --- الحقول الزمنية ---
    date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # YYYY-MM-DD
    period_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("periods.id", ondelete="SET NULL"), index=True
    )
    
    # --- الحالة والملاحظات ---
    status: Mapped[str] = mapped_column(String(15), nullable=False)  # present/absent/late/leave
    note: Mapped[str | None] = mapped_column(String(500))
    
    # --- من سجل ---
    recorded_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    
    # --- العلاقات (Relationships) ---
    teacher = relationship("Teacher", back_populates="attendances")
    section = relationship("Section")
    grade = relationship("Grade")
    stage = relationship("Stage")
    year = relationship("AcademicYear")
    period = relationship("Period")
    recorder = relationship("User", foreign_keys=[recorded_by])


# ============================================================
#  نموذج إحصائيات الحضور (جدول إضافي للتجميع)
# ============================================================

class AttendanceSummary(UUIDPkMixin, TimestampMixin, Base):
    """ملخص إحصائيات الحضور (للتقارير السريعة)"""
    __tablename__ = "attendance_summaries"
    __table_args__ = (
        UniqueConstraint("school_id", "date", "section_id", name="uq_att_summary_day_section"),
    )

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    # --- التصنيفات ---
    section_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sections.id", ondelete="CASCADE"), index=True
    )
    grade_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("grades.id", ondelete="CASCADE"), index=True
    )
    stage_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("stages.id", ondelete="CASCADE"), index=True
    )
    year_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("academic_years.id", ondelete="CASCADE"), index=True
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
    
    # --- العلاقات ---
    section = relationship("Section")
    grade = relationship("Grade")
    stage = relationship("Stage")
    year = relationship("AcademicYear")


# ============================================================
#  نموذج سجل التغييرات (Audit Log)
# ============================================================

class AttendanceAuditLog(UUIDPkMixin, TimestampMixin, Base):
    """سجل تغييرات الحضور (للتدقيق)"""
    __tablename__ = "attendance_audit_logs"
    
    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), index=True
    )
    attendance_type: Mapped[str] = mapped_column(String(20), nullable=False)  # student / teacher
    attendance_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # create / update / delete
    old_data: Mapped[str | None] = mapped_column(String(1000))  # JSON
    new_data: Mapped[str | None] = mapped_column(String(1000))  # JSON
    changed_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    
    # العلاقات
    user = relationship("User", foreign_keys=[changed_by])


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
