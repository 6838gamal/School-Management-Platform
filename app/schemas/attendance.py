"""Attendance schemas with full academic hierarchy support."""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import date

from app.schemas.common import ORMBase


# ============================================================
# 1️⃣ Enums (القيم الثابتة)
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
    
    @classmethod
    def get_badge_class(cls, value: str) -> str:
        """الحصول على كلاس البادج للحالة."""
        mapping = {
            cls.PRESENT: "bg-green-100 text-green-700",
            cls.ABSENT: "bg-red-100 text-red-700",
            cls.LATE: "bg-yellow-100 text-yellow-700",
            cls.EXCUSED: "bg-blue-100 text-blue-700",
        }
        return mapping.get(value, "bg-slate-100 text-slate-700")


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
    
    @classmethod
    def get_color(cls, value: str) -> str:
        """الحصول على لون الحالة."""
        mapping = {
            cls.PRESENT: "success",
            cls.ABSENT: "danger",
            cls.LATE: "warning",
            cls.EXCUSED: "info",
            cls.LEAVE: "secondary",
        }
        return mapping.get(value, "secondary")


# ============================================================
# 2️⃣ Schemas الأساسية للإنشاء والتحديث
# ============================================================

class StudentAttendanceCreate(BaseModel):
    """إنشاء سجل حضور طالب."""
    student_id: str = Field(..., description="معرف الطالب")
    section_id: Optional[str] = Field(None, description="معرف الشعبة")
    grade_id: Optional[str] = Field(None, description="معرف الصف")
    stage_id: Optional[str] = Field(None, description="معرف المرحلة")
    year_id: Optional[str] = Field(None, description="معرف السنة الدراسية")
    period_id: Optional[str] = Field(None, description="معرف الحصة")
    schedule_entry_id: Optional[str] = Field(None, description="معرف الجدول")
    date: str = Field(..., description="التاريخ (YYYY-MM-DD)")
    status: str = Field(..., pattern="^(present|absent|late|excused)$", description="الحالة")
    note: Optional[str] = Field(None, max_length=500, description="ملاحظات")
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v: str) -> str:
        """التحقق من صحة التاريخ."""
        try:
            date.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError('التاريخ يجب أن يكون بصيغة YYYY-MM-DD')


class StudentAttendanceUpdate(BaseModel):
    """تحديث سجل حضور طالب."""
    status: Optional[str] = Field(None, pattern="^(present|absent|late|excused)$", description="الحالة")
    note: Optional[str] = Field(None, max_length=500, description="ملاحظات")
    section_id: Optional[str] = Field(None, description="معرف الشعبة")
    grade_id: Optional[str] = Field(None, description="معرف الصف")
    stage_id: Optional[str] = Field(None, description="معرف المرحلة")
    year_id: Optional[str] = Field(None, description="معرف السنة الدراسية")
    period_id: Optional[str] = Field(None, description="معرف الحصة")


class StudentAttendanceBatch(BaseModel):
    """دفعة حضور طلاب."""
    date: str = Field(..., description="التاريخ (YYYY-MM-DD)")
    section_id: str = Field(..., description="معرف الشعبة")
    grade_id: Optional[str] = Field(None, description="معرف الصف")
    stage_id: Optional[str] = Field(None, description="معرف المرحلة")
    year_id: Optional[str] = Field(None, description="معرف السنة الدراسية")
    period_id: Optional[str] = Field(None, description="معرف الحصة")
    records: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="قائمة السجلات [{student_id, status, note}]"
    )
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v: str) -> str:
        """التحقق من صحة التاريخ."""
        try:
            date.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError('التاريخ يجب أن يكون بصيغة YYYY-MM-DD')
    
    @field_validator('records')
    @classmethod
    def validate_records(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """التحقق من صحة السجلات."""
        if not v:
            raise ValueError('يجب تحديد على الأقل طالب واحد')
        
        valid_statuses = ['present', 'absent', 'late', 'excused']
        for record in v:
            if 'student_id' not in record:
                raise ValueError('كل سجل يجب أن يحتوي على student_id')
            if 'status' not in record:
                raise ValueError('كل سجل يجب أن يحتوي على status')
            if record['status'] not in valid_statuses:
                raise ValueError(f'الحالة {record["status"]} غير صالحة')
        
        return v


class TeacherAttendanceCreate(BaseModel):
    """إنشاء سجل حضور معلم."""
    teacher_id: str = Field(..., description="معرف المعلم")
    section_id: Optional[str] = Field(None, description="معرف الشعبة")
    grade_id: Optional[str] = Field(None, description="معرف الصف")
    stage_id: Optional[str] = Field(None, description="معرف المرحلة")
    year_id: Optional[str] = Field(None, description="معرف السنة الدراسية")
    period_id: Optional[str] = Field(None, description="معرف الحصة")
    date: str = Field(..., description="التاريخ (YYYY-MM-DD)")
    status: str = Field(..., pattern="^(present|absent|late|leave)$", description="الحالة")
    note: Optional[str] = Field(None, max_length=500, description="ملاحظات")
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v: str) -> str:
        """التحقق من صحة التاريخ."""
        try:
            date.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError('التاريخ يجب أن يكون بصيغة YYYY-MM-DD')


class TeacherAttendanceUpdate(BaseModel):
    """تحديث سجل حضور معلم."""
    status: Optional[str] = Field(None, pattern="^(present|absent|late|leave)$", description="الحالة")
    note: Optional[str] = Field(None, max_length=500, description="ملاحظات")
    section_id: Optional[str] = Field(None, description="معرف الشعبة")
    grade_id: Optional[str] = Field(None, description="معرف الصف")
    stage_id: Optional[str] = Field(None, description="معرف المرحلة")
    year_id: Optional[str] = Field(None, description="معرف السنة الدراسية")
    period_id: Optional[str] = Field(None, description="معرف الحصة")


# ============================================================
# 3️⃣ Schemas للعرض (Response)
# ============================================================

class StudentAttendanceOut(ORMBase):
    """عرض سجل حضور طالب."""
    id: str
    school_id: str
    student_id: str
    student_name: Optional[str] = Field(None, description="اسم الطالب")
    student_number: Optional[str] = Field(None, description="رقم الطالب")
    section_id: Optional[str] = None
    section_name: Optional[str] = Field(None, description="اسم الشعبة")
    grade_id: Optional[str] = None
    grade_name: Optional[str] = Field(None, description="اسم الصف")
    stage_id: Optional[str] = None
    stage_name: Optional[str] = Field(None, description="اسم المرحلة")
    year_id: Optional[str] = None
    year_name: Optional[str] = Field(None, description="اسم السنة الدراسية")
    period_id: Optional[str] = None
    period_name: Optional[str] = Field(None, description="اسم الحصة")
    date: str
    status: str
    status_arabic: Optional[str] = Field(None, description="الحالة بالعربية")
    status_color: Optional[str] = Field(None, description="لون الحالة")
    status_badge: Optional[str] = Field(None, description="كلاس البادج")
    note: Optional[str] = None
    recorded_by: Optional[str] = None
    recorder_name: Optional[str] = Field(None, description="اسم المسجل")
    created_at: str
    updated_at: str
    
    def model_post_init(self, __context):
        """تعيين القيم المشتقة بعد الإنشاء."""
        if self.status:
            self.status_arabic = StudentAttendanceStatus.get_arabic_name(self.status)
            self.status_color = StudentAttendanceStatus.get_color(self.status)
            self.status_badge = StudentAttendanceStatus.get_badge_class(self.status)


class TeacherAttendanceOut(ORMBase):
    """عرض سجل حضور معلم."""
    id: str
    school_id: str
    teacher_id: str
    teacher_name: Optional[str] = Field(None, description="اسم المعلم")
    section_id: Optional[str] = None
    section_name: Optional[str] = Field(None, description="اسم الشعبة")
    grade_id: Optional[str] = None
    grade_name: Optional[str] = Field(None, description="اسم الصف")
    stage_id: Optional[str] = None
    stage_name: Optional[str] = Field(None, description="اسم المرحلة")
    year_id: Optional[str] = None
    year_name: Optional[str] = Field(None, description="اسم السنة الدراسية")
    period_id: Optional[str] = None
    period_name: Optional[str] = Field(None, description="اسم الحصة")
    date: str
    status: str
    status_arabic: Optional[str] = Field(None, description="الحالة بالعربية")
    status_color: Optional[str] = Field(None, description="لون الحالة")
    note: Optional[str] = None
    recorded_by: Optional[str] = None
    recorder_name: Optional[str] = Field(None, description="اسم المسجل")
    created_at: str
    updated_at: str
    
    def model_post_init(self, __context):
        """تعيين القيم المشتقة بعد الإنشاء."""
        if self.status:
            self.status_arabic = TeacherAttendanceStatus.get_arabic_name(self.status)
            self.status_color = TeacherAttendanceStatus.get_color(self.status)


# ============================================================
# 4️⃣ Schemas للإحصائيات والتقارير
# ============================================================

class AttendanceSummary(BaseModel):
    """ملخص الحضور."""
    date: str = Field(..., description="التاريخ")
    total: int = Field(0, description="إجمالي الطلاب")
    present: int = Field(0, description="الحاضرون")
    absent: int = Field(0, description="الغائبون")
    late: int = Field(0, description="المتأخرون")
    excused: int = Field(0, description="المعذورون")
    rate: float = Field(0.0, description="نسبة الحضور")
    
    @property
    def present_percentage(self) -> float:
        """نسبة الحضور."""
        return round((self.present / self.total * 100) if self.total > 0 else 0, 1)
    
    @property
    def absent_percentage(self) -> float:
        """نسبة الغياب."""
        return round((self.absent / self.total * 100) if self.total > 0 else 0, 1)


class AttendanceSummaryExtended(AttendanceSummary):
    """ملخص الحضور الموسع."""
    section_id: Optional[str] = None
    section_name: Optional[str] = None
    grade_id: Optional[str] = None
    grade_name: Optional[str] = None
    stage_id: Optional[str] = None
    stage_name: Optional[str] = None
    year_id: Optional[str] = None
    year_name: Optional[str] = None


class TeacherAttendanceSummary(BaseModel):
    """ملخص حضور المعلمين."""
    date: str = Field(..., description="التاريخ")
    total: int = Field(0, description="إجمالي المعلمين")
    present: int = Field(0, description="الحاضرون")
    absent: int = Field(0, description="الغائبون")
    late: int = Field(0, description="المتأخرون")
    excused: int = Field(0, description="المعذورون")
    leave: int = Field(0, description="في إجازة")
    rate: float = Field(0.0, description="نسبة الحضور")
    
    @property
    def present_percentage(self) -> float:
        """نسبة الحضور."""
        return round((self.present / self.total * 100) if self.total > 0 else 0, 1)


# ============================================================
# 5️⃣ Schemas للفلترة والبحث
# ============================================================

class AttendanceFilter(BaseModel):
    """فلترة سجلات الحضور."""
    date_from: Optional[str] = Field(None, description="تاريخ البداية")
    date_to: Optional[str] = Field(None, description="تاريخ النهاية")
    section_id: Optional[str] = Field(None, description="معرف الشعبة")
    grade_id: Optional[str] = Field(None, description="معرف الصف")
    stage_id: Optional[str] = Field(None, description="معرف المرحلة")
    year_id: Optional[str] = Field(None, description="معرف السنة الدراسية")
    period_id: Optional[str] = Field(None, description="معرف الحصة")
    status: Optional[str] = Field(None, description="الحالة")
    student_id: Optional[str] = Field(None, description="معرف الطالب")
    teacher_id: Optional[str] = Field(None, description="معرف المعلم")
    
    @field_validator('date_from', 'date_to')
    @classmethod
    def validate_dates(cls, v: Optional[str]) -> Optional[str]:
        """التحقق من صحة التواريخ."""
        if v:
            try:
                date.fromisoformat(v)
                return v
            except ValueError:
                raise ValueError('التاريخ يجب أن يكون بصيغة YYYY-MM-DD')
        return v


class AttendanceReportRequest(BaseModel):
    """طلب تقرير الحضور."""
    date_from: str = Field(..., description="تاريخ البداية")
    date_to: str = Field(..., description="تاريخ النهاية")
    section_id: Optional[str] = Field(None, description="معرف الشعبة")
    grade_id: Optional[str] = Field(None, description="معرف الصف")
    stage_id: Optional[str] = Field(None, description="معرف المرحلة")
    year_id: Optional[str] = Field(None, description="معرف السنة الدراسية")
    student_id: Optional[str] = Field(None, description="معرف الطالب")
    teacher_id: Optional[str] = Field(None, description="معرف المعلم")
    format: str = Field("html", description="صيغة التقرير: html, pdf, excel")


# ============================================================
# 6️⃣ Schemas للتحليل والإحصائيات المتقدمة
# ============================================================

class StudentAttendanceAnalytics(BaseModel):
    """تحليل حضور طالب."""
    student_id: str
    student_name: str
    student_number: str
    section_name: Optional[str] = None
    grade_name: Optional[str] = None
    total_days: int = 0
    present: int = 0
    absent: int = 0
    late: int = 0
    excused: int = 0
    attendance_rate: float = 0.0
    
    # الاتجاهات
    weekly_trend: List[Dict[str, Any]] = Field(default_factory=list)
    monthly_summary: List[Dict[str, Any]] = Field(default_factory=list)


class SectionAttendanceAnalytics(BaseModel):
    """تحليل حضور شعبة."""
    section_id: str
    section_name: str
    grade_name: Optional[str] = None
    stage_name: Optional[str] = None
    total_students: int = 0
    attendance_rate: float = 0.0
    daily_rates: List[Dict[str, Any]] = Field(default_factory=list)
    top_students: List[Dict[str, Any]] = Field(default_factory=list)
    bottom_students: List[Dict[str, Any]] = Field(default_factory=list)


# ============================================================
# 7️⃣ Schemas للتصدير
# ============================================================

class AttendanceExportRow(BaseModel):
    """صف للتصدير."""
    student_number: str
    student_name: str
    section_name: str
    grade_name: str
    date: str
    status: str
    status_arabic: str
    note: Optional[str] = None
    recorded_by: Optional[str] = None


class AttendanceExportData(BaseModel):
    """بيانات التصدير."""
    school_name: str
    date_from: str
    date_to: str
    rows: List[AttendanceExportRow]
    summary: AttendanceSummary


# ============================================================
# 8️⃣ Schemas للردود (API Responses)
# ============================================================

class AttendanceResponse(BaseModel):
    """استجابة عامة للحضور."""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None


class AttendanceBatchResponse(BaseModel):
    """استجابة دفعة الحضور."""
    success: bool = True
    message: str
    total_records: int
    saved_records: int
    failed_records: int
    errors: List[Dict[str, str]] = Field(default_factory=list)


# ============================================================
# التصدير
# ============================================================

__all__ = [
    # Enums
    "StudentAttendanceStatus",
    "TeacherAttendanceStatus",
    
    # Create/Update
    "StudentAttendanceCreate",
    "StudentAttendanceUpdate",
    "StudentAttendanceBatch",
    "TeacherAttendanceCreate",
    "TeacherAttendanceUpdate",
    
    # Response
    "StudentAttendanceOut",
    "TeacherAttendanceOut",
    
    # Summary
    "AttendanceSummary",
    "AttendanceSummaryExtended",
    "TeacherAttendanceSummary",
    
    # Filter
    "AttendanceFilter",
    "AttendanceReportRequest",
    
    # Analytics
    "StudentAttendanceAnalytics",
    "SectionAttendanceAnalytics",
    
    # Export
    "AttendanceExportRow",
    "AttendanceExportData",
    
    # Response
    "AttendanceResponse",
    "AttendanceBatchResponse",
]
