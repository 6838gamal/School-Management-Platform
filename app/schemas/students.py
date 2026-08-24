"""Student schemas."""
from pydantic import BaseModel,Field

from app.schemas.common import ORMBase


class StudentCreate(BaseModel):
    student_number: str
    national_id: str | None = None
    first_name: str
    last_name: str
    gender: str | None = None
    birth_date: str | None = None
    guardian_name: str | None = None
    guardian_phone: str | None = None
    guardian_email: str | None = None
    address: str | None = None
    section_id: str | None = None
    year_id: str | None = None


class StudentUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    national_id: str | None = None
    gender: str | None = None
    birth_date: str | None = None
    guardian_name: str | None = None
    guardian_phone: str | None = None
    guardian_email: str | None = None
    address: str | None = None
    is_active: bool | None = None


class StudentOut(ORMBase):
    id: str
    school_id: str
    student_number: str
    national_id: str | None = None
    first_name: str
    last_name: str
    gender: str | None = None
    birth_date: str | None = None
    guardian_name: str | None = None
    guardian_phone: str | None = None
    guardian_email: str | None = None
    address: str | None = None
    photo_url: str | None = None
    is_active: bool
    full_name: str = ""


class EnrollmentOut(ORMBase):
    id: str
    student_id: str
    year_id: str
    section_id: str | None = None
    status: str
    enrolled_at: str
    ended_at: str | None = None


class TransferRequest(BaseModel):
    student_id: str
    to_section_id: str
    year_id: str
    reason: str | None = None
