"""Auth and user management schemas."""
from pydantic import BaseModel, EmailStr, Field  # ✅ تمت إضافة BaseModel

from app.schemas.common import ORMBase


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterSchoolRequest(BaseModel):
    school_name: str = Field(..., min_length=2, max_length=255)
    school_code: str = Field(..., min_length=2, max_length=50)
    director_name: str = Field(..., min_length=2, max_length=255)
    director_email: EmailStr
    director_password: str = Field(..., min_length=8)


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
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
