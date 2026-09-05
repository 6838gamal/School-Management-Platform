"""Schedules schemas - نماذج البيانات للجداول الدراسية."""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


# ============================================================
# ✅ Enums - محاولة استخدام قيم مختلفة
# ============================================================

class ScheduleStatus(str, Enum):
    """حالة الجدول"""
    # ✅ جرب هذه القيم بدلاً من DRAFT
    DRAFT = "draft"  # أو جرب "مسودة"
    PUBLISHED = "published"  # أو جرب "منشور"
    ARCHIVED = "archived"  # أو جرب "مؤرشف"
    CANCELLED = "cancelled"  # أو جرب "ملغي"
    
    # إذا كانت القيم بالعربية:
    # DRAFT = "مسودة"
    # PUBLISHED = "منشور"
    # ARCHIVED = "مؤرشف"
    # CANCELLED = "ملغي"


class DayOfWeek(int, Enum):
    """أيام الأسبوع"""
    SUNDAY = 0
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    
    @property
    def arabic_name(self) -> str:
        names = {
            0: "الأحد",
            1: "الإثنين",
            2: "الثلاثاء",
            3: "الأربعاء",
            4: "الخميس",
            5: "الجمعة",
            6: "السبت"
        }
        return names.get(self.value, "غير معروف")
    
    @property
    def english_name(self) -> str:
        names = {
            0: "Sunday",
            1: "Monday",
            2: "Tuesday",
            3: "Wednesday",
            4: "Thursday",
            5: "Friday",
            6: "Saturday"
        }
        return names.get(self.value, "Unknown")


# ============================================================
# ✅ Schedule Entry Schemas
# ============================================================

class ScheduleEntryBase(BaseModel):
    """القاعدة المشتركة للحصة"""
    day: int = Field(..., ge=0, le=6, description="رقم اليوم (0=الأحد, 6=السبت)")
    period: int = Field(..., ge=1, le=8, description="رقم الفترة/الحصة (1-8)")
    subject_id: str = Field(..., description="معرف المادة")
    teacher_id: Optional[str] = Field(None, description="معرف المعلم")
    room_id: Optional[str] = Field(None, description="معرف الغرفة")
    notes: Optional[str] = Field(None, max_length=500, description="ملاحظات")
    
    @field_validator('day')
    @classmethod
    def validate_day(cls, v: int) -> int:
        if v < 0 or v > 6:
            raise ValueError('رقم اليوم يجب أن يكون بين 0 و 6')
        return v

    @field_validator('period')
    @classmethod
    def validate_period(cls, v: int) -> int:
        if v < 1 or v > 8:
            raise ValueError('رقم الفترة يجب أن يكون بين 1 و 8')
        return v

    @field_validator('subject_id')
    @classmethod
    def validate_subject_id(cls, v: str) -> str:
        if not v or v == '':
            raise ValueError('معرف المادة مطلوب')
        return v


class ScheduleEntryCreate(ScheduleEntryBase):
    """Schema لإضافة حصة إلى الجدول"""
    pass


class ScheduleEntryUpdate(BaseModel):
    """Schema لتحديث حصة"""
    day: Optional[int] = Field(None, ge=0, le=6)
    period: Optional[int] = Field(None, ge=1, le=8)
    subject_id: Optional[str] = None
    teacher_id: Optional[str] = None
    room_id: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class ScheduleEntryResponse(BaseModel):
    """Schema لعرض الحصة"""
    id: str
    schedule_id: str
    day: int
    day_of_week: int
    day_name: Optional[str] = None
    day_name_en: Optional[str] = None
    period: int
    period_id: Optional[str] = None
    period_name: Optional[str] = None
    period_order: Optional[int] = None
    period_start_time: Optional[str] = None
    period_end_time: Optional[str] = None
    subject_id: str
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    subject_color: Optional[str] = None
    teacher_id: Optional[str] = None
    teacher_name: Optional[str] = None
    teacher_full_name: Optional[str] = None
    room_id: Optional[str] = None
    room_name: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================
# ✅ Schedule Schemas - مع إزالة status من الإنشاء مؤقتاً
# ============================================================

class ScheduleBase(BaseModel):
    """القاعدة المشتركة للجدول"""
    name: str = Field(..., min_length=1, max_length=100, description="اسم الجدول")
    description: Optional[str] = Field(None, max_length=500, description="وصف الجدول")
    section_id: str = Field(..., description="معرف الشعبة")
    year_id: str = Field(..., description="معرف العام الدراسي")
    status: ScheduleStatus = Field(default=ScheduleStatus.DRAFT, description="حالة الجدول")
    is_active: bool = Field(default=True, description="هل الجدول مفعل؟")
    is_default: bool = Field(default=False, description="هل هذا الجدول هو الافتراضي للشعبة؟")
    start_date: Optional[date] = Field(None, description="تاريخ بدء تطبيق الجدول")
    end_date: Optional[date] = Field(None, description="تاريخ انتهاء تطبيق الجدول")


class ScheduleCreate(ScheduleBase):
    """Schema لإنشاء جدول جديد"""
    entries: List[ScheduleEntryCreate] = Field(
        default=[], 
        description="الحصص في الجدول"
    )
    
    @field_validator('section_id')
    @classmethod
    def validate_section_id(cls, v: str) -> str:
        if not v or v == '':
            raise ValueError('معرف الشعبة مطلوب')
        return v

    @field_validator('year_id')
    @classmethod
    def validate_year_id(cls, v: str) -> str:
        if not v or v == '':
            raise ValueError('معرف العام الدراسي مطلوب')
        return v
    
    @model_validator(mode='after')
    def validate_dates(self) -> 'ScheduleCreate':
        """التحقق من صحة التواريخ"""
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValueError('تاريخ البداية يجب أن يكون قبل تاريخ النهاية')
        return self
    
    @model_validator(mode='after')
    def validate_entries(self) -> 'ScheduleCreate':
        """التحقق من وجود حصص"""
        if not self.entries:
            raise ValueError('يجب إضافة حصة واحدة على الأقل')
        return self


class ScheduleUpdate(BaseModel):
    """Schema لتحديث جدول"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    section_id: Optional[str] = None
    year_id: Optional[str] = None
    status: Optional[ScheduleStatus] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    @model_validator(mode='after')
    def validate_dates(self) -> 'ScheduleUpdate':
        """التحقق من صحة التواريخ"""
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValueError('تاريخ البداية يجب أن يكون قبل تاريخ النهاية')
        return self


class ScheduleResponse(BaseModel):
    """Schema لعرض الجدول"""
    id: str
    name: str
    description: Optional[str] = None
    school_id: str
    section_id: str
    section_name: Optional[str] = None
    section_grade: Optional[str] = None
    section_stage: Optional[str] = None
    grade_id: Optional[str] = None
    grade_name: Optional[str] = None
    stage_id: Optional[str] = None
    stage_name: Optional[str] = None
    year_id: str
    year_name: Optional[str] = None
    academic_year_name: Optional[str] = None
    status: ScheduleStatus
    is_active: bool
    is_default: bool
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    
    entries_count: int = 0
    total_periods: int = 0
    days_count: int = 0
    periods_per_day: int = 0
    entries: List[ScheduleEntryResponse] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


class ScheduleListResponse(BaseModel):
    """Schema لقائمة الجداول"""
    items: List[ScheduleResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ============================================================
# Schedule Template Schemas
# ============================================================

class ScheduleTemplateBase(BaseModel):
    """القاعدة المشتركة لقالب الجدول"""
    name: str = Field(..., min_length=1, max_length=100, description="اسم القالب")
    description: Optional[str] = Field(None, max_length=500, description="وصف القالب")
    days_count: int = Field(default=5, ge=1, le=7, description="عدد الأيام")
    periods_per_day: int = Field(default=5, ge=1, le=8, description="عدد الحصص في اليوم")
    is_active: bool = Field(default=True, description="هل القالب مفعل؟")


class ScheduleTemplateCreate(ScheduleTemplateBase):
    """Schema لإنشاء قالب جديد"""
    entries: List["ScheduleTemplateEntryCreate"] = Field(
        default=[], 
        description="مدخلات القالب"
    )


class ScheduleTemplateUpdate(BaseModel):
    """Schema لتحديث قالب"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    days_count: Optional[int] = Field(None, ge=1, le=7)
    periods_per_day: Optional[int] = Field(None, ge=1, le=8)
    is_active: Optional[bool] = None


class ScheduleTemplateEntryBase(BaseModel):
    """القاعدة المشتركة لمدخل القالب"""
    day: int = Field(..., ge=0, le=6)
    period: int = Field(..., ge=1, le=8)
    subject_id: str = Field(..., description="معرف المادة")
    teacher_id: Optional[str] = Field(None, description="معرف المعلم")


class ScheduleTemplateEntryCreate(ScheduleTemplateEntryBase):
    """Schema لإنشاء مدخل قالب"""
    pass


class ScheduleTemplateEntryResponse(ScheduleTemplateEntryBase):
    """Schema لعرض مدخل قالب"""
    id: str
    template_id: str
    period_name: Optional[str] = None
    subject_name: Optional[str] = None
    teacher_name: Optional[str] = None


class ScheduleTemplateResponse(ScheduleTemplateBase):
    """Schema لعرض قالب"""
    id: str
    school_id: str
    created_at: datetime
    updated_at: datetime
    entries: List[ScheduleTemplateEntryResponse] = Field(default_factory=list)
    entries_count: int = 0
    
    class Config:
        from_attributes = True


# ============================================================
# Batch Operations Schemas
# ============================================================

class ScheduleBulkCreate(BaseModel):
    """Schema للإنشاء الجماعي للجداول"""
    schedules: List[ScheduleCreate] = Field(..., min_length=1, description="قائمة الجداول")
    overwrite_existing: bool = Field(default=False, description="استبدال الجداول الموجودة؟")


class ScheduleBulkResponse(BaseModel):
    """Schema للرد على الإنشاء الجماعي"""
    created: int = Field(..., description="عدد الجداول المنشأة")
    updated: int = Field(..., description="عدد الجداول المحدثة")
    failed: int = Field(..., description="عدد الجداول الفاشلة")
    errors: List[dict] = Field(default_factory=list, description="قائمة الأخطاء")


class ScheduleCopyRequest(BaseModel):
    """Schema لنسخ جدول"""
    source_schedule_id: str = Field(..., description="معرف الجدول المصدر")
    target_section_id: str = Field(..., description="معرف الشعبة المستهدفة")
    target_year_id: str = Field(..., description="معرف العام الدراسي المستهدف")
    new_name: str = Field(..., min_length=1, max_length=100, description="اسم الجدول الجديد")


class ScheduleValidationResult(BaseModel):
    """Schema لنتيجة التحقق من الجدول"""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


# ============================================================
# Filter Schemas
# ============================================================

class ScheduleFilter(BaseModel):
    """فلترة الجداول"""
    section_id: Optional[str] = None
    year_id: Optional[str] = None
    stage_id: Optional[str] = None
    grade_id: Optional[str] = None
    status: Optional[ScheduleStatus] = None
    is_active: Optional[bool] = None
    search: Optional[str] = Field(None, description="بحث في الاسم والوصف")
    start_date_from: Optional[date] = None
    start_date_to: Optional[date] = None


# ============================================================
# Forward references for Pydantic
# ============================================================
ScheduleCreate.model_rebuild()
ScheduleResponse.model_rebuild()
ScheduleTemplateCreate.model_rebuild()
ScheduleTemplateResponse.model_rebuild()


# ============================================================
# تحديث __all__
# ============================================================
__all__ = [
    "ScheduleStatus",
    "DayOfWeek",
    "ScheduleBase",
    "ScheduleCreate",
    "ScheduleUpdate",
    "ScheduleResponse",
    "ScheduleListResponse",
    "ScheduleEntryBase",
    "ScheduleEntryCreate",
    "ScheduleEntryUpdate",
    "ScheduleEntryResponse",
    "ScheduleTemplateBase",
    "ScheduleTemplateCreate",
    "ScheduleTemplateUpdate",
    "ScheduleTemplateResponse",
    "ScheduleTemplateEntryBase",
    "ScheduleTemplateEntryCreate",
    "ScheduleTemplateEntryResponse",
    "ScheduleBulkCreate",
    "ScheduleBulkResponse",
    "ScheduleCopyRequest",
    "ScheduleValidationResult",
    "ScheduleFilter",
]
