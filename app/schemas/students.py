"""Student schemas."""
from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any

from app.schemas.common import ORMBase


# ============================================================
# Schemas للإنشاء والتحديث
# ============================================================

class StudentCreate(BaseModel):
    """Schema لإنشاء طالب جديد"""
    student_number: str = Field(..., min_length=1, max_length=50)
    national_id: str | None = Field(None, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    first_name_ar: str | None = Field(None, max_length=100)
    last_name_ar: str | None = Field(None, max_length=100)
    gender: str | None = Field(None, pattern="^(male|female|ذكر|أنثى)$")
    birth_date: date | None = None
    nationality: str | None = Field(None, max_length=50)
    
    # معلومات ولي الأمر
    guardian_name: str | None = Field(None, max_length=255)
    guardian_phone: str | None = Field(None, max_length=50)
    guardian_email: str | None = Field(None, max_length=255)
    guardian_relation: str | None = Field(None, max_length=50)
    
    # معلومات الاتصال
    phone: str | None = Field(None, max_length=50)
    address: str | None = Field(None, max_length=500)
    photo_url: str | None = Field(None, max_length=500)
    
    # ✅ الحقول الأكاديمية
    school_id: str | None = Field(None, max_length=36)
    user_id: str | None = Field(None, max_length=36)
    year_id: str | None = Field(None, max_length=36, description="معرف السنة الدراسية")
    grade_id: str | None = Field(None, max_length=36, description="معرف الصف")
    section_id: str | None = Field(None, max_length=36, description="معرف الشعبة")
    
    # ✅ حالة الحضور الافتراضية
    attendance_status: str | None = Field(
        "present", 
        pattern="^(present|absent|late|permitted|excused)$",
        description="حالة الحضور"
    )
    
    @field_validator('birth_date', mode='before')
    @classmethod
    def validate_birth_date(cls, v):
        """تحويل تاريخ الميلاد من نص إلى Date"""
        if isinstance(v, str):
            try:
                return date.fromisoformat(v)
            except ValueError:
                raise ValueError('Invalid date format. Use YYYY-MM-DD')
        return v


class StudentUpdate(BaseModel):
    """Schema لتحديث بيانات طالب"""
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    first_name_ar: str | None = Field(None, max_length=100)
    last_name_ar: str | None = Field(None, max_length=100)
    national_id: str | None = Field(None, max_length=50)
    gender: str | None = Field(None, pattern="^(male|female|ذكر|أنثى)$")
    birth_date: date | None = None
    nationality: str | None = Field(None, max_length=50)
    
    # معلومات ولي الأمر
    guardian_name: str | None = Field(None, max_length=255)
    guardian_phone: str | None = Field(None, max_length=50)
    guardian_email: str | None = Field(None, max_length=255)
    guardian_relation: str | None = Field(None, max_length=50)
    
    # معلومات الاتصال
    phone: str | None = Field(None, max_length=50)
    address: str | None = Field(None, max_length=500)
    photo_url: str | None = Field(None, max_length=500)
    
    # ✅ الحقول الأكاديمية
    year_id: str | None = Field(None, max_length=36, description="معرف السنة الدراسية")
    grade_id: str | None = Field(None, max_length=36, description="معرف الصف")
    section_id: str | None = Field(None, max_length=36, description="معرف الشعبة")
    
    # ✅ حالة الحضور
    attendance_status: str | None = Field(
        None, 
        pattern="^(present|absent|late|permitted|excused)$",
        description="حالة الحضور"
    )
    
    # الحالة
    is_active: bool | None = None
    enrollment_status: str | None = Field(None, pattern="^(active|transferred|graduated|left)$")
    
    @field_validator('birth_date', mode='before')
    @classmethod
    def validate_birth_date(cls, v):
        """تحويل تاريخ الميلاد من نص إلى Date"""
        if isinstance(v, str):
            try:
                return date.fromisoformat(v)
            except ValueError:
                raise ValueError('Invalid date format. Use YYYY-MM-DD')
        return v


# ============================================================
# Schemas للاستعلام والعرض
# ============================================================

class StudentOut(ORMBase):
    """Schema لعرض بيانات طالب كاملة"""
    id: str
    school_id: str
    user_id: str | None = None
    student_number: str
    national_id: str | None = None
    first_name: str
    last_name: str
    first_name_ar: str | None = None
    last_name_ar: str | None = None
    gender: str | None = None
    birth_date: date | None = None
    nationality: str | None = None
    
    # معلومات ولي الأمر
    guardian_name: str | None = None
    guardian_phone: str | None = None
    guardian_email: str | None = None
    guardian_relation: str | None = None
    
    # معلومات الاتصال
    phone: str | None = None
    address: str | None = None
    photo_url: str | None = None
    
    # ✅ الحقول الأكاديمية
    year_id: str | None = None
    grade_id: str | None = None
    section_id: str | None = None
    
    # ✅ حالة الحضور
    attendance_status: str | None = None
    attendance_updated_at: datetime | None = None
    
    # الحالة
    is_active: bool
    enrollment_status: str | None = None
    
    # الخصائص المحسوبة
    full_name: str = ""
    full_name_ar: str | None = None
    display_name: str = ""
    display_name_ar: str | None = None
    age: int | None = None
    
    # ✅ تسميات حالة الحضور
    attendance_label: str | None = None
    attendance_color: str | None = None
    
    # معلومات إضافية للعرض (من JOIN)
    year_name: str | None = None
    grade_name: str | None = None
    section_name: str | None = None
    
    # التسجيل الحالي
    current_enrollment: "EnrollmentOut | None" = None
    
    # إحصائيات إضافية (للواجهة)
    assignments_total: int = 0
    assignments_completed: int = 0
    activities_total: int = 0
    activities_completed: int = 0
    
    # إحصائيات الحضور
    attendance_stats: Dict[str, Any] | None = None
    late_stats: Dict[str, Any] | None = None
    
    # الحصص (للواجهة)
    periods: list[Dict[str, Any]] | None = None
    assignments: list[Dict[str, Any]] | None = None
    activities: list[Dict[str, Any]] | None = None


class StudentListOut(ORMBase):
    """Schema لقائمة الطلاب (مختصر)"""
    id: str
    student_number: str
    first_name: str
    last_name: str
    first_name_ar: str | None = None
    last_name_ar: str | None = None
    gender: str | None = None
    is_active: bool
    full_name: str = ""
    display_name: str = ""
    
    # ✅ الحقول الأكاديمية
    year_id: str | None = None
    grade_id: str | None = None
    section_id: str | None = None
    
    # ✅ حالة الحضور
    attendance_status: str | None = None
    
    # معلومات للعرض
    year_name: str | None = None
    grade_name: str | None = None
    section_name: str | None = None
    photo_url: str | None = None
    
    # ✅ تسميات حالة الحضور
    attendance_label: str | None = None
    attendance_color: str | None = None
    
    # إحصائيات للعرض في البطاقة
    assignments_total: int = 0
    assignments_completed: int = 0
    activities_total: int = 0
    activities_completed: int = 0
    
    # إحصائيات الحضور
    attendance_stats: Dict[str, Any] | None = None


# ============================================================
# Schemas للتسجيل الأكاديمي
# ============================================================

class EnrollmentCreate(BaseModel):
    """Schema لتسجيل طالب في صف/شعبة"""
    student_id: str = Field(..., max_length=36)
    school_id: str = Field(..., max_length=36)
    year_id: str = Field(..., max_length=36)
    section_id: str | None = Field(None, max_length=36)
    grade_id: str | None = Field(None, max_length=36)  # ✅ بدلاً من class_id
    enrolled_at: date = Field(default=date.today)
    status: str = Field(default="active", pattern="^(active|transferred|graduated|left|dropped)$")
    notes: str | None = Field(None, max_length=500)


class EnrollmentUpdate(BaseModel):
    """Schema لتحديث تسجيل طالب"""
    section_id: str | None = Field(None, max_length=36)
    grade_id: str | None = Field(None, max_length=36)  # ✅ بدلاً من class_id
    status: str | None = Field(None, pattern="^(active|transferred|graduated|left|dropped)$")
    ended_at: date | None = None
    notes: str | None = Field(None, max_length=500)


class EnrollmentOut(ORMBase):
    """Schema لعرض تسجيل طالب"""
    id: str
    student_id: str
    school_id: str
    year_id: str
    section_id: str | None = None
    grade_id: str | None = None  # ✅ بدلاً من class_id
    status: str
    enrolled_at: date
    ended_at: date | None = None
    notes: str | None = None
    
    # الخصائص المحسوبة
    is_current: bool = False
    enrollment_duration: int | None = None
    
    # البيانات المرتبطة (اختياري)
    student: StudentOut | None = None


# ============================================================
# Schemas للبحث والترشيح
# ============================================================

class StudentFilter(BaseModel):
    """فلترة قائمة الطلاب"""
    school_id: str | None = Field(None, max_length=36)
    year_id: str | None = Field(None, max_length=36, description="معرف السنة الدراسية")
    grade_id: str | None = Field(None, max_length=36, description="معرف الصف")
    section_id: str | None = Field(None, max_length=36, description="معرف الشعبة")
    is_active: bool | None = None
    gender: str | None = Field(None, pattern="^(male|female|ذكر|أنثى)$")
    search: str | None = Field(None, description="بحث في الاسم أو رقم الطالب")
    
    # ✅ إضافة فلتر حالة الحضور
    attendance_status: str | None = Field(
        None, 
        pattern="^(present|absent|late|permitted|excused)$",
        description="فلتر حسب حالة الحضور"
    )


class StudentSearchResult(StudentListOut):
    """نتيجة بحث عن طالب مع معلومات إضافية"""
    age: int | None = None
    current_section: str | None = None
    enrollment_status: str | None = None


# ============================================================
# Schemas للتحويلات والنقل
# ============================================================

class TransferRequest(BaseModel):
    """طلب نقل طالب من شعبة لأخرى"""
    student_id: str = Field(..., max_length=36)
    from_section_id: str | None = Field(None, max_length=36)
    to_section_id: str = Field(..., max_length=36)
    year_id: str = Field(..., max_length=36)
    reason: str | None = Field(None, max_length=500)
    transfer_date: date = Field(default=date.today)


class TransferResponse(BaseModel):
    """رد نقل طالب"""
    success: bool
    message: str
    old_enrollment: EnrollmentOut
    new_enrollment: EnrollmentOut


# ============================================================
# Schemas للإحصائيات
# ============================================================

class StudentStats(BaseModel):
    """إحصائيات الطلاب"""
    total_students: int = 0
    active_students: int = 0
    inactive_students: int = 0
    male_students: int = 0
    female_students: int = 0
    students_by_year: dict[str, int] = {}
    students_by_grade: dict[str, int] = {}
    students_by_section: dict[str, int] = {}
    students_by_class: dict[str, int] = {}
    new_enrollments_this_year: int = 0
    graduates_this_year: int = 0
    
    # ✅ إحصائيات الحضور
    present_today: int = 0
    absent_today: int = 0
    late_today: int = 0
    permitted_today: int = 0
    excused_today: int = 0


# ============================================================
# Schema لتحديث حالة الحضور (API)
# ============================================================

class AttendanceUpdate(BaseModel):
    """Schema لتحديث حالة الحضور"""
    student_id: str = Field(..., max_length=36)
    status: str = Field(..., pattern="^(present|absent|late|permitted|excused)$")
    date: str | None = Field(None, description="تاريخ الحضور (YYYY-MM-DD)")
    note: str | None = Field(None, max_length=500)


class AttendanceBulkUpdate(BaseModel):
    """Schema لتحديث حالة الحضور لمجموعة من الطلاب"""
    student_ids: list[str] = Field(..., min_length=1)
    status: str = Field(..., pattern="^(present|absent|late|permitted|excused)$")
    date: str | None = Field(None, description="تاريخ الحضور (YYYY-MM-DD)")
    note: str | None = Field(None, max_length=500)


# ============================================================
# Schema لحالة الطالب الكاملة (للواجهة)
# ============================================================

class StudentFullStatus(BaseModel):
    """Schema لحالة الطالب الكاملة للواجهة"""
    # بيانات الطالب الأساسية
    student: StudentOut
    
    # حالة الحضور اليومية
    today_attendance: str | None = None
    
    # إحصائيات الحضور
    attendance_stats: Dict[str, Any] | None = None
    
    # الواجبات
    assignments: list[Dict[str, Any]] | None = None
    assignments_stats: Dict[str, int] | None = None
    
    # الأنشطة
    activities: list[Dict[str, Any]] | None = None
    activities_stats: Dict[str, int] | None = None
    
    # التأخر
    late_stats: Dict[str, int] | None = None
    
    # الحصص
    periods: list[Dict[str, Any]] | None = None


# ============================================================
# تحديث المراجع
# ============================================================

StudentOut.model_rebuild()
StudentListOut.model_rebuild()
EnrollmentOut.model_rebuild()
