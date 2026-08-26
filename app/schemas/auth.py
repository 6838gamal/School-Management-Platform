"""Auth and user management schemas."""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any

from app.schemas.common import ORMBase


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterSchoolRequest(BaseModel):
    school_name: str = Field(..., min_length=2, max_length=255)
    school_code: str = Field(..., min_length=2, max_length=50)
    director_name: str = Field(..., min_length=2, max_length=255)
    director_email: EmailStr
    director_phone: Optional[str] = Field(None, description="رقم جوال المدير")
    director_password: str = Field(..., min_length=8, max_length=72)


class RegisterUserRequest(BaseModel):
    """طلب تسجيل مستخدم جديد (وكيل، مسؤول أنشطة، معلم)"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)
    full_name: str = Field(..., min_length=2, max_length=255)
    employee_number: Optional[str] = Field(None, description="الرقم الوظيفي (اختياري)")  # ✅ جعلته اختيارياً
    phone: Optional[str] = Field(None, description="رقم الجوال (اختياري)")
    school_code: str = Field(..., description="رمز المدرسة للانضمام")
    role_name: str = Field(..., description="اسم الدور (deputy, activities_manager, teacher)")
    extra_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="بيانات إضافية")
    
    @validator('phone')
    def validate_phone(cls, v):
        """
        التحقق من رقم الجوال - مرن جداً
        
        - يمكن أن يكون فارغاً (اختياري)
        - يمكن أن يكون رقم محلي (05xxxxxxxx)
        - يمكن أن يكون رقم دولي (+9665xxxxxxxx)
        - أي صيغة أخرى مقبولة
        """
        if not v:
            return None
        
        # إزالة المسافات
        v = v.strip()
        
        # إذا كان الرقم فارغاً بعد التنظيف، أرجع None
        if not v:
            return None
        
        # أبسط تحقق: فقط تأكد من أنه ليس فارغاً
        if len(v) < 5:
            raise ValueError('رقم الجوال قصير جداً')
        
        # حذف الرموز غير الرقمية للتحقق من الطول
        digits = ''.join(filter(str.isdigit, v))
        if len(digits) < 5:
            raise ValueError('رقم الجوال يجب أن يحتوي على 5 أرقام على الأقل')
        
        return v
    
    @validator('role_name')
    def validate_role(cls, v):
        """التحقق من صحة اسم الدور - مطابق لقاعدة البيانات"""
        # ✅ تحديث الأدوار المسموحة لتطابق قاعدة البيانات
        allowed_roles = ['deputy', 'activities_manager', 'teacher']
        if v not in allowed_roles:
            raise ValueError(
                f'الدور غير مسموح. الأدوار المسموحة: {", ".join(allowed_roles)}'
            )
        return v


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)
    full_name: str
    phone: str | None = None
    role_key: str = "teacher"


class UserUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    is_active: bool | None = None
    role_key: str | None = None


class UserOut(ORMBase):
    id: str
    email: str
    full_name: str
    phone: str | None = None
    is_active: bool
    school_id: str | None = None
    roles: list[str] = []


class RoleOut(ORMBase):
    id: str
    key: str
    name_ar: str
    name_en: str | None = None
    is_system: bool
    permissions: list[str] = []


class PermissionOut(ORMBase):
    id: str
    key: str
    label_ar: str
    label_en: str | None = None
    group: str


class SessionInfo(BaseModel):
    user: UserOut
    school_id: str | None = None
    permissions: list[str] = []
