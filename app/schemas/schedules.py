"""Schedules schemas - نماذج البيانات للجداول الدراسية."""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


# ============================================================
# Enums
# ============================================================

class ScheduleStatus(str, Enum):
    """حالة الجدول"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"


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
    
    @classmethod
    def is_weekend(cls, day: int) -> bool:
        """هل اليوم عطلة؟"""
        return day in [5, 6]  # الجمعة والسبت
    
    @classmethod
    def is_active_day(cls, day: int) -> bool:
        """هل اليوم نشط (أيام الأحد إلى الخميس)؟"""
        return day in [0, 1, 2, 3, 4]


# ============================================================
# Schedule Schemas
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
    entries: Optional[List["ScheduleEntryCreate"]] = Field(
        default=[], 
        description="الحصص في الجدول"
    )
    
    @field_validator('section_id')
    @classmethod
    def validate_section_id(cls, v: str) -> str:
        if not v or len(v) != 36:
            raise ValueError('معرف الشعبة غير صحيح')
        return v

    @field_validator('year_id')
    @classmethod
    def validate_year_id(cls, v: str) -> str:
        if not v or len(v) != 36:
            raise ValueError('معرف العام الدراسي غير صحيح')
        return v
    
    @model_validator(mode='after')
    def validate_dates(self) -> 'ScheduleCreate':
        """التحقق من صحة التواريخ"""
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValueError('تاريخ البداية يجب أن يكون قبل تاريخ النهاية')
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
    
    @field_validator('section_id')
    @classmethod
    def validate_section_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v or len(v) != 36):
            raise ValueError('معرف الشعبة غير صحيح')
        return v

    @field_validator('year_id')
    @classmethod
    def validate_year_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v or len(v) != 36):
            raise ValueError('معرف العام الدراسي غير صحيح')
        return v
    
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
    year_id: str
    academic_year_name: Optional[str] = None
    status: ScheduleStatus
    is_active: bool
    is_default: bool
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    
    # إحصائيات
    entries_count: int = 0
    total_periods: int = 0
    days_count: int = 0
    periods_per_day: int = 0
    
    # الحصص
    entries: List["ScheduleEntryResponse"] = Field(default_factory=list)
    
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
# Schedule Entry Schemas
# ============================================================

class ScheduleEntryBase(BaseModel):
    """القاعدة المشتركة للحصة"""
    day_of_week: int = Field(..., ge=0, le=6, description="رقم اليوم (0=الأحد, 6=السبت)")
    period_id: str = Field(..., description="معرف الفترة/الحصة")
    subject_id: str = Field(..., description="معرف المادة")
    teacher_id: str = Field(..., description="معرف المعلم")
    room_id: Optional[str] = Field(None, description="معرف الغرفة")
    notes: Optional[str] = Field(None, max_length=500, description="ملاحظات")


class ScheduleEntryCreate(ScheduleEntryBase):
    """Schema لإضافة حصة إلى الجدول"""
    
    @field_validator('day_of_week')
    @classmethod
    def validate_day_of_week(cls, v: int) -> int:
        if v < 0 or v > 6:
            raise ValueError('رقم اليوم يجب أن يكون بين 0 و 6')
        if DayOfWeek.is_weekend(v):
            raise ValueError('لا يمكن إضافة حصص في عطلة نهاية الأسبوع (الجمعة والسبت)')
        return v

    @field_validator('period_id')
    @classmethod
    def validate_period_id(cls, v: str) -> str:
        if not v or len(v) != 36:
            raise ValueError('معرف الفترة غير صحيح')
        return v

    @field_validator('subject_id')
    @classmethod
    def validate_subject_id(cls, v: str) -> str:
        if not v or len(v) != 36:
            raise ValueError('معرف المادة غير صحيح')
        return v

    @field_validator('teacher_id')
    @classmethod
    def validate_teacher_id(cls, v: str) -> str:
        if not v or len(v) != 36:
            raise ValueError('معرف المعلم غير صحيح')
        return v


class ScheduleEntryUpdate(BaseModel):
    """Schema لتحديث حصة"""
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    period_id: Optional[str] = None
    subject_id: Optional[str] = None
    teacher_id: Optional[str] = None
    room_id: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=500)
    
    @field_validator('day_of_week')
    @classmethod
    def validate_day_of_week(cls, v: Optional[int]) -> Optional[int]:
        if v is not None:
            if v < 0 or v > 6:
                raise ValueError('رقم اليوم يجب أن يكون بين 0 و 6')
            if DayOfWeek.is_weekend(v):
                raise ValueError('لا يمكن إضافة حصص في عطلة نهاية الأسبوع')
        return v


class ScheduleEntryResponse(BaseModel):
    """Schema لعرض الحصة"""
    id: str
    schedule_id: str
    day_of_week: int
    day_name: Optional[str] = None
    day_name_en: Optional[str] = None
    period_id: str
    period_name: Optional[str] = None
    period_order: Optional[int] = None
    period_start_time: Optional[str] = None
    period_end_time: Optional[str] = None
    subject_id: str
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    subject_color: Optional[str] = None
    teacher_id: str
    teacher_name: Optional[str] = None
    teacher_full_name: Optional[str] = None
    room_id: Optional[str] = None
    room_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


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
    day_of_week: int = Field(..., ge=0, le=6)
    period_id: str = Field(..., description="معرف الفترة")
    subject_id: str = Field(..., description="معرف المادة")


class ScheduleTemplateEntryCreate(ScheduleTemplateEntryBase):
    """Schema لإنشاء مدخل قالب"""
    pass


class ScheduleTemplateEntryResponse(ScheduleTemplateEntryBase):
    """Schema لعرض مدخل قالب"""
    id: str
    template_id: str
    period_name: Optional[str] = None
    subject_name: Optional[str] = None


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
    status: Optional[ScheduleStatus] = None
    is_active: Optional[bool] = None
    search: Optional[str] = Field(None, description="بحث في الاسم والوصف")
    start_date_from: Optional[date] = None
    start_date_to: Optional[date] = None
    
    @field_validator('section_id')
    @classmethod
    def validate_section_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v or len(v) != 36):
            raise ValueError('معرف الشعبة غير صحيح')
        return v

    @field_validator('year_id')
    @classmethod
    def validate_year_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v or len(v) != 36):
            raise ValueError('معرف العام الدراسي غير صحيح')
        return v


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
    # Enums
    "ScheduleStatus",
    "DayOfWeek",
    
    # Schedule
    "ScheduleBase",
    "ScheduleCreate",
    "ScheduleUpdate",
    "ScheduleResponse",
    "ScheduleListResponse",
    
    # Schedule Entry
    "ScheduleEntryBase",
    "ScheduleEntryCreate",
    "ScheduleEntryUpdate",
    "ScheduleEntryResponse",
    
    # Templates
    "ScheduleTemplateBase",
    "ScheduleTemplateCreate",
    "ScheduleTemplateUpdate",
    "ScheduleTemplateResponse",
    "ScheduleTemplateEntryBase",
    "ScheduleTemplateEntryCreate",
    "ScheduleTemplateEntryResponse",
    
    # Batch Operations
    "ScheduleBulkCreate",
    "ScheduleBulkResponse",
    "ScheduleCopyRequest",
    "ScheduleValidationResult",
    
    # Filters
    "ScheduleFilter",
]
