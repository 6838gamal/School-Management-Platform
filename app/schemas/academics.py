"""Academic structure schemas."""
from pydantic import BaseModel, Field, validator
from typing import Optional

from app.schemas.common import ORMBase


class SchoolOut(ORMBase):
    id: str
    name: str
    name_en: str | None = None
    code: str
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    logo_url: str | None = None
    language: str
    onboarding_complete: bool
    onboarding_step: str | None = None
    is_active: bool


class SchoolUpdate(BaseModel):
    name: str | None = None
    name_en: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    logo_url: str | None = None
    language: str | None = None


# ============= Academic Year =============
class AcademicYearCreate(BaseModel):
    name: str
    start_date: str
    end_date: str
    is_current: bool = True
    
    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        """التحقق من صيغة التاريخ"""
        import re
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError('صيغة التاريخ يجب أن تكون YYYY-MM-DD')
        return v
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """التحقق من أن تاريخ النهاية بعد تاريخ البداية"""
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('تاريخ النهاية يجب أن يكون بعد تاريخ البداية')
        return v


class AcademicYearUpdate(BaseModel):
    name: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool | None = None
    is_active: bool | None = None


class AcademicYearOut(ORMBase):
    id: str
    school_id: str
    name: str
    start_date: str
    end_date: str
    is_current: bool
    is_active: bool


# ============= Stage =============
class StageCreate(BaseModel):
    year_id: str
    name: str = Field(..., min_length=2, max_length=100)
    name_en: str | None = Field(None, max_length=100)
    order: int = 0
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('اسم المرحلة يجب أن يكون على الأقل حرفين')
        return v.strip()


class StageUpdate(BaseModel):
    year_id: str | None = None
    name: str | None = None
    name_en: str | None = None
    order: int | None = None


class StageOut(ORMBase):
    id: str
    school_id: str
    year_id: str
    name: str
    name_en: str | None = None
    order: int


# ============= Grade =============
class GradeCreate(BaseModel):
    """✅ نموذج إنشاء صف جديد - مع دعم السنة الدراسية"""
    stage_id: str = Field(..., description="معرف المرحلة")
    year_id: str = Field(..., description="معرف السنة الدراسية")  # ✅ حقل جديد
    name: str = Field(..., min_length=2, max_length=100, description="اسم الصف")
    name_en: str | None = Field(None, max_length=100, description="اسم الصف بالإنجليزية")
    order: int = Field(0, ge=0, description="ترتيب الصف")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('اسم الصف يجب أن يكون على الأقل حرفين')
        return v.strip()
    
    @validator('year_id')
    def validate_year_id(cls, v):
        if not v:
            raise ValueError('يرجى اختيار السنة الدراسية')
        return v
    
    @validator('stage_id')
    def validate_stage_id(cls, v):
        if not v:
            raise ValueError('يرجى اختيار المرحلة')
        return v


class GradeUpdate(BaseModel):
    """✅ نموذج تحديث صف - مع دعم السنة الدراسية"""
    stage_id: str | None = Field(None, description="معرف المرحلة")
    year_id: str | None = Field(None, description="معرف السنة الدراسية")  # ✅ حقل جديد
    name: str | None = Field(None, min_length=2, max_length=100, description="اسم الصف")
    name_en: str | None = Field(None, max_length=100, description="اسم الصف بالإنجليزية")
    order: int | None = Field(None, ge=0, description="ترتيب الصف")
    is_active: bool | None = Field(None, description="حالة التفعيل")


class GradeOut(ORMBase):
    """✅ نموذج عرض الصف - مع دعم السنة الدراسية"""
    id: str
    school_id: str
    stage_id: str
    year_id: str  # ✅ حقل جديد
    name: str
    name_en: str | None = None
    order: int
    is_active: bool
    
    # حقول إضافية للعرض (من JOIN)
    stage_name: str | None = None
    year_name: str | None = None


# ============= Section =============
class SectionCreate(BaseModel):
    grade_id: str
    name: str = Field(..., min_length=1, max_length=50)
    capacity: int = Field(30, ge=1, le=100)
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 1:
            raise ValueError('اسم الشعبة مطلوب')
        return v.strip()


class SectionUpdate(BaseModel):
    grade_id: str | None = None
    name: str | None = None
    capacity: int | None = None
    is_active: bool | None = None


class SectionOut(ORMBase):
    id: str
    school_id: str
    grade_id: str
    name: str
    capacity: int
    is_active: bool
    
    # حقول إضافية للعرض
    grade_name: str | None = None


# ============= Subject =============
class SubjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    name_en: str | None = Field(None, max_length=100)
    code: str | None = Field(None, max_length=20)
    color: str | None = Field(None, max_length=20)
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('اسم المادة يجب أن يكون على الأقل حرفين')
        return v.strip()


class SubjectUpdate(BaseModel):
    name: str | None = None
    name_en: str | None = None
    code: str | None = None
    color: str | None = None
    is_active: bool | None = None


class SubjectOut(ORMBase):
    id: str
    school_id: str
    name: str
    name_en: str | None = None
    code: str | None = None
    color: str | None = None
    is_active: bool


# ============= Room =============
class RoomCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    building: str | None = Field(None, max_length=100)
    floor: str | None = Field(None, max_length=20)
    capacity: int = Field(30, ge=1, le=500)


class RoomUpdate(BaseModel):
    name: str | None = None
    building: str | None = None
    floor: str | None = None
    capacity: int | None = None
    is_active: bool | None = None


class RoomOut(ORMBase):
    id: str
    school_id: str
    name: str
    building: str | None = None
    floor: str | None = None
    capacity: int
    is_active: bool


# ============= Period =============
class PeriodCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    order: int = Field(..., ge=0)
    start_time: str = Field(..., pattern=r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$')
    end_time: str = Field(..., pattern=r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$')
    is_break: bool = False
    
    @validator('end_time')
    def validate_time_range(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('وقت النهاية يجب أن يكون بعد وقت البداية')
        return v


class PeriodUpdate(BaseModel):
    name: str | None = None
    order: int | None = None
    start_time: str | None = None
    end_time: str | None = None
    is_break: bool | None = None


class PeriodOut(ORMBase):
    id: str
    school_id: str
    name: str
    order: int
    start_time: str
    end_time: str
    is_break: bool


# ============= Academic Tree =============
class AcademicTreeYear(BaseModel):
    """نموذج السنة في الشجرة الأكاديمية"""
    id: str
    name: str
    name_en: str | None = None
    is_current: bool
    stages: list["AcademicTreeStage"] = []


class AcademicTreeStage(BaseModel):
    """نموذج المرحلة في الشجرة الأكاديمية"""
    id: str
    name: str
    name_en: str | None = None
    order: int
    grades: list["AcademicTreeGrade"] = []


class AcademicTreeGrade(BaseModel):
    """✅ نموذج الصف في الشجرة الأكاديمية - مع year_id"""
    id: str
    name: str
    name_en: str | None = None
    order: int
    year_id: str  # ✅ حقل جديد
    sections: list["AcademicTreeSection"] = []


class AcademicTreeSection(BaseModel):
    """نموذج الشعبة في الشجرة الأكاديمية"""
    id: str
    name: str
    capacity: int
    is_active: bool


class AcademicTree(BaseModel):
    """نموذج الشجرة الأكاديمية الكامل"""
    years: list[AcademicTreeYear] = []


# ============= Assessment (التقييمات) =============
class AssessmentCreate(BaseModel):
    """نموذج إنشاء تقييم جديد"""
    section_id: str
    subject_id: str
    teacher_id: str | None = None
    title: str = Field(..., min_length=2, max_length=200)
    assessment_type: str = Field(..., pattern="^(exam|quiz|assignment|homework|activity|participation)$")
    max_score: float = Field(100.0, gt=0)
    passing_score: float | None = Field(50.0, ge=0)
    weight: float = Field(1.0, gt=0)
    date: str | None = None
    description: str | None = None
    school_id: str | None = None
    year_id: str | None = None


class AssessmentUpdate(BaseModel):
    """نموذج تحديث تقييم"""
    section_id: str | None = None
    subject_id: str | None = None
    teacher_id: str | None = None
    title: str | None = None
    assessment_type: str | None = Field(None, pattern="^(exam|quiz|assignment|homework|activity|participation)$")
    max_score: float | None = None
    passing_score: float | None = None
    weight: float | None = None
    date: str | None = None
    description: str | None = None
    year_id: str | None = None


class AssessmentOut(ORMBase):
    """نموذج عرض التقييم"""
    id: str
    school_id: str
    section_id: str
    subject_id: str
    teacher_id: str | None = None
    year_id: str | None = None
    title: str
    description: str | None = None
    assessment_type: str
    max_score: float
    passing_score: float | None = None
    weight: float
    date: str | None = None
    
    # حقول إضافية للعرض (من JOIN)
    section_name: str | None = None
    subject_name: str | None = None
    teacher_name: str | None = None


class AssessmentListResponse(BaseModel):
    """رد قائمة التقييمات"""
    items: list[AssessmentOut]
    total: int
    page: int = 1
    page_size: int = 10


# ============================================================
# ✅ دعم العلاقات بين الكيانات
# ============================================================

class GradeWithRelations(GradeOut):
    """✅ الصف مع العلاقات الكاملة"""
    stage: "StageOut" | None = None
    year: "AcademicYearOut" | None = None
    sections_count: int = 0


class StageWithRelations(StageOut):
    """المرحلة مع العلاقات الكاملة"""
    year: "AcademicYearOut" | None = None
    grades: list[GradeOut] = []
    grades_count: int = 0


class AcademicYearWithRelations(AcademicYearOut):
    """السنة الدراسية مع العلاقات الكاملة"""
    stages: list[StageOut] = []
    grades: list[GradeOut] = []  # ✅ علاقة مباشرة مع الصفوف
    stages_count: int = 0
    grades_count: int = 0


# ============================================================
# ✅ تحديث Forward References
# ============================================================

# تحديث المراجع الأمامية لـ Pydantic
AcademicTreeGrade.model_rebuild()
AcademicTreeStage.model_rebuild()
AcademicTreeYear.model_rebuild()
GradeWithRelations.model_rebuild()
StageWithRelations.model_rebuild()
AcademicYearWithRelations.model_rebuild()
