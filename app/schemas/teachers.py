"""Teacher schemas."""
from pydantic import BaseModel,Field

from app.schemas.common import ORMBase


class TeacherCreate(BaseModel):
    employee_number: str
    national_id: str | None = None
    first_name: str
    last_name: str
    gender: str | None = None
    phone: str | None = None
    email: str | None = None
    specialization: str | None = None
    qualification: str | None = None
    hire_date: str | None = None
    create_user: bool = False
    user_password: str | None = None
    user_email: str | None = None


class TeacherUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    national_id: str | None = None
    gender: str | None = None
    phone: str | None = None
    email: str | None = None
    specialization: str | None = None
    qualification: str | None = None
    is_active: bool | None = None


class TeacherOut(ORMBase):
    id: str
    school_id: str
    user_id: str | None = None
    employee_number: str
    national_id: str | None = None
    first_name: str
    last_name: str
    gender: str | None = None
    phone: str | None = None
    email: str | None = None
    specialization: str | None = None
    qualification: str | None = None
    hire_date: str | None = None
    photo_url: str | None = None
    is_active: bool
    full_name: str = ""


class AssignmentCreate(BaseModel):
    teacher_id: str
    subject_id: str
    section_id: str
    year_id: str


class AssignmentOut(ORMBase):
    id: str
    teacher_id: str
    subject_id: str
    section_id: str
    year_id: str
    status: str
    assigned_at: str
    ended_at: str | None = None
