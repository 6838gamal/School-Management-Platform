"""Academic structure schemas."""
from pydantic import BaseModel, Field, validator
from typing import Optional, List

from app.schemas.common import ORMBase


class SchoolOut(ORMBase):
    id: str
    name: str
    name_en: Optional[str] = None
    code: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    logo_url: Optional[str] = None
    language: str
    onboarding_complete: bool
    onboarding_step: Optional[str] = None
    is_active: bool


class SchoolUpdate(BaseModel):
    name: Optional[str] = None
    name_en: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    logo_url: Optional[str] = None
    language: Optional[str] = None


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
    name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: Optional[bool] = None
    is_active: Optional[bool] = None


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
    name_en: Optional[str] = Field(None, max_length=100)
    order: int = 0
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('اسم المرحلة يجب أن يكون على الأقل حرفين')
        return v.strip()


class StageUpdate(BaseModel):
    year_id: Optional[str] = None
    name: Optional[str] = None
    name_en: Optional[str] = None
    order: Optional[int] = None


class StageOut(ORMBase):
    id: str
    school_id: str
    year_id: str
    name: str
    name_en: Optional[str] = None
    order: int


# ============= Grade =============
class GradeCreate(BaseModel):
    """نموذج إنشاء صف جديد - مع دعم السنة الدراسية"""
    stage_id: str = Field(..., description="معرف المرحلة")
    year_id: str = Field(..., description="معرف السنة الدراسية")
    name: str = Field(..., min_length=2, max_length=100, description="اسم الصف")
    name_en: Optional[str] = Field(None, max_length=100, description="اسم الصف بالإنجليزية")
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
    """نموذج تحديث صف - مع دعم السنة الدراسية"""
    stage_id: Optional[str] = Field(None, description="معرف المرحلة")
    year_id: Optional[str] = Field(None, description="معرف السنة الدراسية")
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="اسم الصف")
    name_en: Optional[str] = Field(None, max_length=100, description="اسم الصف بالإنجليزية")
    order: Optional[int] = Field(None, ge=0, description="ترتيب الصف")
    is_active: Optional[bool] = Field(None, description="حالة التفعيل")


class GradeOut(ORMBase):
    """نموذج عرض الصف - مع دعم السنة الدراسية"""
    id: str
    school_id: str
    stage_id: str
    year_id: str
    name: str
    name_en: Optional[str] = None
    order: int
    is_active: bool
    
    # حقول إضافية للعرض (من JOIN)
    stage_name: Optional[str] = None
    year_name: Optional[str] = None


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
    grade_id: Optional[str] = None
    name: Optional[str] = None
    capacity: Optional[int] = None
    is_active: Optional[bool] = None


class SectionOut(ORMBase):
    id: str
    school_id: str
    grade_id: str
    name: str
    capacity: int
    is_active: bool
    
    # حقول إضافية للعرض
    grade_name: Optional[str] = None


# ============= Subject =============
class SubjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    name_en: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    color: Optional[str] = Field(None, max_length=20)
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('اسم المادة يجب أن يكون على الأقل حرفين')
        return v.strip()


class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    name_en: Optional[str] = None
    code: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None


class SubjectOut(ORMBase):
    id: str
    school_id: str
    name: str
    name_en: Optional[str] = None
    code: Optional[str] = None
    color: Optional[str] = None
    is_active: bool


# ============= Room =============
class RoomCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    building: Optional[str] = Field(None, max_length=100)
    floor: Optional[str] = Field(None, max_length=20)
    capacity: int = Field(30, ge=1, le=500)


class RoomUpdate(BaseModel):
    name: Optional[str] = None
    building: Optional[str] = None
    floor: Optional[str] = None
    capacity: Optional[int] = None
    is_active: Optional[bool] = None


class RoomOut(ORMBase):
    id: str
    school_id: str
    name: str
    building: Optional[str] = None
    floor: Optional[str] = None
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
    name: Optional[str] = None
    order: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    is_break: Optional[bool] = None


class PeriodOut(ORMBase):
    id: str
    school_id: str
    name: str
    order: int
    start_time: str
    end_time: str
    is_break: bool


# ============= Academic Tree =============
class AcademicTreeSection(BaseModel):
    """نموذج الشعبة في الشجرة الأكاديمية"""
    id: str
    name: str
    capacity: int
    is_active: bool


class AcademicTreeGrade(BaseModel):
    """نموذج الصف في الشجرة الأكاديمية"""
    id: str
    name: str
    name_en: Optional[str] = None
    order: int
    year_id: str
    sections: List[AcademicTreeSection] = []


class AcademicTreeStage(BaseModel):
    """نموذج المرحلة في الشجرة الأكاديمية"""
    id: str
    name: str
    name_en: Optional[str] = None
    order: int
    year_id: str
    grades: List[AcademicTreeGrade] = []


class AcademicTreeYear(BaseModel):
    """نموذج السنة في الشجرة الأكاديمية"""
    id: str
    name: str
    name_en: Optional[str] = None
    is_current: bool
    stages: List[AcademicTreeStage] = []


class AcademicTree(BaseModel):
    """نموذج الشجرة الأكاديمية الكامل"""
    years: List[AcademicTreeYear] = []


# ============= Assessment (التقييمات) =============
class AssessmentCreate(BaseModel):
    """نموذج إنشاء تقييم جديد"""
    section_id: str
    subject_id: str
    teacher_id: Optional[str] = None
    title: str = Field(..., min_length=2, max_length=200)
    assessment_type: str = Field(..., pattern="^(exam|quiz|assignment|homework|activity|participation)$")
    max_score: float = Field(100.0, gt=0)
    passing_score: Optional[float] = Field(50.0, ge=0)
    weight: float = Field(1.0, gt=0)
    date: Optional[str] = None
    description: Optional[str] = None
    school_id: Optional[str] = None
    year_id: Optional[str] = None


class AssessmentUpdate(BaseModel):
    """نموذج تحديث تقييم"""
    section_id: Optional[str] = None
    subject_id: Optional[str] = None
    teacher_id: Optional[str] = None
    title: Optional[str] = None
    assessment_type: Optional[str] = Field(None, pattern="^(exam|quiz|assignment|homework|activity|participation)$")
    max_score: Optional[float] = None
    passing_score: Optional[float] = None
    weight: Optional[float] = None
    date: Optional[str] = None
    description: Optional[str] = None
    year_id: Optional[str] = None


class AssessmentOut(ORMBase):
    """نموذج عرض التقييم"""
    id: str
    school_id: str
    section_id: str
    subject_id: str
    teacher_id: Optional[str] = None
    year_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    assessment_type: str
    max_score: float
    passing_score: Optional[float] = None
    weight: float
    date: Optional[str] = None
    
    # حقول إضافية للعرض (من JOIN)
    section_name: Optional[str] = None
    subject_name: Optional[str] = None
    teacher_name: Optional[str] = None


class AssessmentListResponse(BaseModel):
    """رد قائمة التقييمات"""
    items: List[AssessmentOut]
    total: int
    page: int = 1
    page_size: int = 10


# ============================================================
# ✅ دعم العلاقات بين الكيانات
# ============================================================

class GradeWithRelations(GradeOut):
    """الصف مع العلاقات الكاملة"""
    stage: Optional["StageOut"] = None
    year: Optional["AcademicYearOut"] = None
    sections_count: int = 0


class StageWithRelations(StageOut):
    """المرحلة مع العلاقات الكاملة"""
    year: Optional["AcademicYearOut"] = None
    grades: List[GradeOut] = []
    grades_count: int = 0


class AcademicYearWithRelations(AcademicYearOut):
    """السنة الدراسية مع العلاقات الكاملة"""
    stages: List[StageOut] = []
    grades: List[GradeOut] = []
    stages_count: int = 0
    grades_count: int = 0


# ============================================================
# ✅ تحديث __all__
# ============================================================

__all__ = [
    # School
    "SchoolOut",
    "SchoolUpdate",
    # Academic Year
    "AcademicYearCreate",
    "AcademicYearUpdate",
    "AcademicYearOut",
    "AcademicYearWithRelations",
    # Stage
    "StageCreate",
    "StageUpdate",
    "StageOut",
    "StageWithRelations",
    # Grade
    "GradeCreate",
    "GradeUpdate",
    "GradeOut",
    "GradeWithRelations",
    # Section
    "SectionCreate",
    "SectionUpdate",
    "SectionOut",
    # Subject
    "SubjectCreate",
    "SubjectUpdate",
    "SubjectOut",
    # Room
    "RoomCreate",
    "RoomUpdate",
    "RoomOut",
    # Period
    "PeriodCreate",
    "PeriodUpdate",
    "PeriodOut",
    # Academic Tree
    "AcademicTree",
    "AcademicTreeYear",
    "AcademicTreeStage",
    "AcademicTreeGrade",
    "AcademicTreeSection",
    # Assessment
    "AssessmentCreate",
    "AssessmentUpdate",
    "AssessmentOut",
    "AssessmentListResponse",
]
