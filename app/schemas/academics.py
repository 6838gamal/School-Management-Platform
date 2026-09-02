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


class AcademicYearWithRelations(AcademicYearOut):
    """السنة الدراسية مع العلاقات الكاملة"""
    stages: List["StageOut"] = []
    grades: List["GradeOut"] = []
    stages_count: int = 0
    grades_count: int = 0


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
    
    @validator('year_id')
    def validate_year_id(cls, v):
        if not v:
            raise ValueError('يرجى اختيار السنة الدراسية')
        return v


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


class StageWithRelations(StageOut):
    """المرحلة مع العلاقات الكاملة"""
    year: Optional["AcademicYearOut"] = None
    grades: List["GradeOut"] = []
    grades_count: int = 0


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


class GradeWithRelations(GradeOut):
    """الصف مع العلاقات الكاملة"""
    stage: Optional["StageOut"] = None
    year: Optional["AcademicYearOut"] = None
    sections_count: int = 0


# ============= Section =============
class SectionCreate(BaseModel):
    """نموذج إنشاء شعبة - مع دعم السنة والمعلمين"""
    grade_id: str = Field(..., description="معرف الصف")
    year_id: str = Field(..., description="معرف السنة الدراسية")
    name: str = Field(..., min_length=1, max_length=50, description="اسم الشعبة")
    capacity: int = Field(30, ge=1, le=100, description="السعة")
    teacher_ids: Optional[List[str]] = Field(
        default_factory=list, 
        description="قائمة معرفات المعلمين كرؤساء فصل"
    )
    is_active: bool = Field(True, description="حالة التفعيل")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 1:
            raise ValueError('اسم الشعبة مطلوب')
        return v.strip()
    
    @validator('grade_id')
    def validate_grade_id(cls, v):
        if not v:
            raise ValueError('يرجى اختيار الصف')
        return v
    
    @validator('year_id')
    def validate_year_id(cls, v):
        if not v:
            raise ValueError('يرجى اختيار السنة الدراسية')
        return v
    
    @validator('capacity')
    def validate_capacity(cls, v):
        if v < 1:
            raise ValueError('السعة يجب أن تكون على الأقل 1')
        if v > 100:
            raise ValueError('السعة القصوى هي 100')
        return v


class SectionUpdate(BaseModel):
    """نموذج تحديث شعبة - مع دعم السنة والمعلمين"""
    grade_id: Optional[str] = Field(None, description="معرف الصف")
    year_id: Optional[str] = Field(None, description="معرف السنة الدراسية")
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="اسم الشعبة")
    capacity: Optional[int] = Field(None, ge=1, le=100, description="السعة")
    teacher_ids: Optional[List[str]] = Field(
        None, 
        description="قائمة معرفات المعلمين كرؤساء فصل"
    )
    is_active: Optional[bool] = Field(None, description="حالة التفعيل")


class SectionOut(ORMBase):
    """نموذج عرض الشعبة - مع دعم السنة والمعلمين"""
    id: str
    school_id: str
    grade_id: str
    year_id: str
    name: str
    capacity: int
    is_active: bool
    class_teacher_ids: Optional[str] = None
    
    # حقول إضافية للعرض (من JOIN)
    grade_name: Optional[str] = None
    year_name: Optional[str] = None
    class_teachers: List[dict] = []  # قائمة المعلمين كرؤساء فصل


class SectionListResponse(BaseModel):
    """رد قائمة الشعب"""
    items: List[SectionOut]
    total: int
    page: int = 1
    page_size: int = 20


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
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 1:
            raise ValueError('اسم القاعة مطلوب')
        return v.strip()


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
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 1:
            raise ValueError('اسم الفصل مطلوب')
        return v.strip()
    
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
    class_teacher_ids: Optional[str] = None
    class_teachers: List[dict] = []  # قائمة المعلمين كرؤساء فصل


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
    section_id: str = Field(..., description="معرف الشعبة")
    subject_id: str = Field(..., description="معرف المادة")
    teacher_id: Optional[str] = Field(None, description="معرف المعلم")
    title: str = Field(..., min_length=2, max_length=200, description="عنوان التقييم")
    assessment_type: str = Field(..., pattern="^(exam|quiz|assignment|homework|activity|participation)$", description="نوع التقييم")
    max_score: float = Field(100.0, gt=0, description="الدرجة القصوى")
    passing_score: Optional[float] = Field(50.0, ge=0, description="درجة النجاح")
    weight: float = Field(1.0, gt=0, description="الوزن النسبي")
    date: Optional[str] = Field(None, description="تاريخ التقييم")
    description: Optional[str] = Field(None, description="وصف التقييم")
    school_id: Optional[str] = Field(None, description="معرف المدرسة")
    year_id: Optional[str] = Field(None, description="معرف السنة الدراسية")
    
    @validator('title')
    def validate_title(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('عنوان التقييم يجب أن يكون على الأقل حرفين')
        return v.strip()
    
    @validator('max_score')
    def validate_max_score(cls, v):
        if v <= 0:
            raise ValueError('الدرجة القصوى يجب أن تكون أكبر من صفر')
        return v
    
    @validator('passing_score')
    def validate_passing_score(cls, v, values):
        if v is not None and 'max_score' in values and v > values['max_score']:
            raise ValueError('درجة النجاح يجب أن لا تتجاوز الدرجة القصوى')
        return v
    
    @validator('weight')
    def validate_weight(cls, v):
        if v <= 0:
            raise ValueError('الوزن يجب أن يكون أكبر من صفر')
        return v


class AssessmentUpdate(BaseModel):
    """نموذج تحديث تقييم"""
    section_id: Optional[str] = Field(None, description="معرف الشعبة")
    subject_id: Optional[str] = Field(None, description="معرف المادة")
    teacher_id: Optional[str] = Field(None, description="معرف المعلم")
    title: Optional[str] = Field(None, min_length=2, max_length=200, description="عنوان التقييم")
    assessment_type: Optional[str] = Field(None, pattern="^(exam|quiz|assignment|homework|activity|participation)$", description="نوع التقييم")
    max_score: Optional[float] = Field(None, gt=0, description="الدرجة القصوى")
    passing_score: Optional[float] = Field(None, ge=0, description="درجة النجاح")
    weight: Optional[float] = Field(None, gt=0, description="الوزن النسبي")
    date: Optional[str] = Field(None, description="تاريخ التقييم")
    description: Optional[str] = Field(None, description="وصف التقييم")
    year_id: Optional[str] = Field(None, description="معرف السنة الدراسية")


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
    school_name: Optional[str] = None


class AssessmentListResponse(BaseModel):
    """رد قائمة التقييمات"""
    items: List[AssessmentOut]
    total: int
    page: int = 1
    page_size: int = 10


# ============================================================
# ✅ تحديث __all__ - القائمة الكاملة
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
    "SectionListResponse",
    
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
