"""Student repositories."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.students import Student, StudentEnrollment
from app.repositories.base import BaseRepository


class StudentRepository(BaseRepository[Student]):
    model = Student

    async def list_by_school(self, school_id: str, page: int = 1, page_size: int = 20, search: str | None = None) -> tuple[list[Student], int]:
        stmt = select(Student).where(Student.school_id == school_id)
        count_stmt = select(Student).where(Student.school_id == school_id)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                (Student.first_name.ilike(like)) | (Student.last_name.ilike(like)) | (Student.student_number.ilike(like))
            )
            count_stmt = count_stmt.where(
                (Student.first_name.ilike(like)) | (Student.last_name.ilike(like)) | (Student.student_number.ilike(like))
            )
        from sqlalchemy import func
        total = (await self.db.execute(select(func.count()).select_from(count_stmt))).scalar() or 0
        offset = (page - 1) * page_size
        result = await self.db.execute(stmt.order_by(Student.created_at.desc()).offset(offset).limit(page_size))
        return list(result.scalars().all()), total

    async def get_by_number(self, school_id: str, number: str) -> Student | None:
        result = await self.db.execute(
            select(Student).where(Student.school_id == school_id, Student.student_number == number)
        )
        return result.scalar_one_or_none()


class EnrollmentRepository(BaseRepository[StudentEnrollment]):
    model = StudentEnrollment

    async def get_active(self, student_id: str, year_id: str) -> StudentEnrollment | None:
        result = await self.db.execute(
            select(StudentEnrollment).where(
                StudentEnrollment.student_id == student_id,
                StudentEnrollment.year_id == year_id,
                StudentEnrollment.status == "active",
            )
        )
        return result.scalar_one_or_none()

    async def list_by_section(self, section_id: str, year_id: str) -> list[StudentEnrollment]:
        result = await self.db.execute(
            select(StudentEnrollment).where(
                StudentEnrollment.section_id == section_id,
                StudentEnrollment.year_id == year_id,
                StudentEnrollment.status == "active",
            )
        )
        return list(result.scalars().all())

    async def list_by_student(self, student_id: str) -> list[StudentEnrollment]:
        result = await self.db.execute(
            select(StudentEnrollment).where(StudentEnrollment.student_id == student_id).order_by(StudentEnrollment.enrolled_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_section(
    self, 
    school_id: str, 
    section_id: str, 
    is_active: bool = True
) -> List[Student]:
    """جلب الطلاب حسب الشعبة."""
    result = await self.db.execute(
        select(Student)
        .where(
            Student.school_id == school_id,
            Student.section_id == section_id,
            Student.is_active == is_active
        )
        .order_by(Student.first_name, Student.last_name)
    )
    return list(result.scalars().all())
