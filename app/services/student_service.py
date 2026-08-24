"""Student service with enrollment and transfer logic."""
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.repositories.students import EnrollmentRepository, StudentRepository
from app.schemas.students import StudentCreate, StudentUpdate, TransferRequest


class StudentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.students = StudentRepository(db)
        self.enrollments = EnrollmentRepository(db)

    async def create_student(self, school_id: str, req: StudentCreate) -> dict:
        existing = await self.students.get_by_number(school_id, req.student_number)
        if existing:
            raise ConflictException("رقم الطالب مستخدم بالفعل")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        student = await self.students.create(
            school_id=school_id,
            student_number=req.student_number,
            national_id=req.national_id,
            first_name=req.first_name,
            last_name=req.last_name,
            gender=req.gender,
            birth_date=req.birth_date,
            guardian_name=req.guardian_name,
            guardian_phone=req.guardian_phone,
            guardian_email=req.guardian_email,
            address=req.address,
            is_active=True,
        )
        # Create enrollment if section + year provided
        if req.section_id and req.year_id:
            await self.enrollments.create(
                student_id=student.id,
                school_id=school_id,
                year_id=req.year_id,
                section_id=req.section_id,
                status="active",
                enrolled_at=now,
            )
        return {"id": student.id, "full_name": f"{student.first_name} {student.last_name}"}

    async def update_student(self, student_id: str, req: StudentUpdate) -> dict:
        student = await self.students.get(student_id)
        if not student:
            raise NotFoundException("الطالب غير موجود")
        student = await self.students.update(student, **req.model_dump(exclude_unset=True))
        return {"id": student.id}

    async def list_students(self, school_id: str, page: int, page_size: int, search: str | None = None) -> dict:
        items, total = await self.students.list_by_school(school_id, page, page_size, search)
        return {
            "items": [
                {
                    "id": s.id,
                    "student_number": s.student_number,
                    "full_name": f"{s.first_name} {s.last_name}",
                    "gender": s.gender,
                    "guardian_phone": s.guardian_phone,
                    "is_active": s.is_active,
                }
                for s in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_student_detail(self, student_id: str) -> dict:
        student = await self.students.get(student_id)
        if not student:
            raise NotFoundException("الطالب غير موجود")
        enrollments = await self.enrollments.list_by_student(student_id)
        return {
            "id": student.id,
            "student_number": student.student_number,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "full_name": f"{student.first_name} {student.last_name}",
            "national_id": student.national_id,
            "gender": student.gender,
            "birth_date": student.birth_date,
            "guardian_name": student.guardian_name,
            "guardian_phone": student.guardian_phone,
            "guardian_email": student.guardian_email,
            "address": student.address,
            "photo_url": student.photo_url,
            "is_active": student.is_active,
            "enrollments": [
                {"id": e.id, "section_id": e.section_id, "year_id": e.year_id, "status": e.status, "enrolled_at": e.enrolled_at}
                for e in enrollments
            ],
        }

    async def transfer_student(self, school_id: str, req: TransferRequest) -> dict:
        enrollment = await self.enrollments.get_active(req.student_id, req.year_id)
        if not enrollment:
            raise NotFoundException("لا يوجد تسجيل نشط للطالب")
        # End current enrollment
        enrollment.status = "transferred"
        enrollment.ended_at = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        await self.db.flush()
        # Create new enrollment
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        new_enrollment = await self.enrollments.create(
            student_id=req.student_id,
            school_id=school_id,
            year_id=req.year_id,
            section_id=req.to_section_id,
            status="active",
            enrolled_at=now,
        )
        return {"enrollment_id": new_enrollment.id}
