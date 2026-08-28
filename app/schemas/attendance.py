"""Attendance schemas."""
from enum import Enum
from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


# ============================================================
# Enums (القيم الثابتة)
# ============================================================

class StudentAttendanceStatus(str, Enum):
    """حالة حضور الطالب."""
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"
    
    @classmethod
    def get_arabic_name(cls, value: str) -> str:
        """الحصول على الاسم العربي للحالة."""
        mapping = {
            cls.PRESENT: "حاضر",
            cls.ABSENT: "غائب",
            cls.LATE: "متأخر",
            cls.EXCUSED: "معذور",
        }
        return mapping.get(value, value)
    
    @classmethod
    def get_color(cls, value: str) -> str:
        """الحصول على لون الحالة."""
        mapping = {
            cls.PRESENT: "success",
            cls.ABSENT: "danger",
            cls.LATE: "warning",
            cls.EXCUSED: "info",
        }
        return mapping.get(value, "secondary")


class TeacherAttendanceStatus(str, Enum):
    """حالة حضور المعلم."""
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"
    LEAVE = "leave"  # إجازة
    
    @classmethod
    def get_arabic_name(cls, value: str) -> str:
        """الحصول على الاسم العربي للحالة."""
        mapping = {
            cls.PRESENT: "حاضر",
            cls.ABSENT: "غائب",
            cls.LATE: "متأخر",
            cls.EXCUSED: "معذور",
            cls.LEAVE: "إجازة",
        }
        return mapping.get(value, value)


# ============================================================
# الـ Schemas الموجودة
# ============================================================

class StudentAttendanceCreate(BaseModel):
    student_id: str
    section_id: str | None = None
    period_id: str | None = None
    schedule_entry_id: str | None = None
    date: str
    status: str = Field(..., pattern="^(present|absent|late|excused)$")
    note: str | None = None


class StudentAttendanceBatch(BaseModel):
    date: str
    section_id: str
    period_id: str | None = None
    records: list[dict] = []  # [{student_id, status, note}]


class StudentAttendanceOut(ORMBase):
    id: str
    student_id: str
    section_id: str | None = None
    period_id: str | None = None
    date: str
    status: str
    note: str | None = None
    recorded_by: str | None = None


class TeacherAttendanceCreate(BaseModel):
    teacher_id: str
    date: str
    status: str = Field(..., pattern="^(present|absent|late|leave)$")
    note: str | None = None


class TeacherAttendanceOut(ORMBase):
    id: str
    teacher_id: str
    date: str
    status: str
    note: str | None = None
    recorded_by: str | None = None


class AttendanceSummary(BaseModel):
    date: str
    total: int
    present: int
    absent: int
    late: int
    excused: int
    rate: float
