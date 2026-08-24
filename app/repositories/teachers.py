"""Teacher repositories."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.teachers import Teacher, TeacherAssignment
from app.repositories.base import BaseRepository


class TeacherRepository(BaseRepository[Teacher]):
    model = Teacher

    async def list_by_school(self, school_id: str, page: int = 1, page_size: int = 20, search: str | None = None) -> tuple[list[Teacher], int]:
        stmt = select(Teacher).where(Teacher.school_id == school_id)
        count_stmt = select(func.count()).select_from(Teacher).where(Teacher.school_id == school_id)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                (Teacher.first_name.ilike(like)) | (Teacher.last_name.ilike(like)) | (Teacher.employee_number.ilike(like))
            )
            count_stmt = count_stmt.where(
                (Teacher.first_name.ilike(like)) | (Teacher.last_name.ilike(like)) | (Teacher.employee_number.ilike(like))
            )
        total = (await self.db.execute(count_stmt)).scalar() or 0
        offset = (page - 1) * page_size
        result = await self.db.execute(stmt.order_by(Teacher.created_at.desc()).offset(offset).limit(page_size))
        return list(result.scalars().all()), total

    async def get_by_number(self, school_id: str, number: str) -> Teacher | None:
        result = await self.db.execute(
            select(Teacher).where(Teacher.school_id == school_id, Teacher.employee_number == number)
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: str) -> Teacher | None:
        result = await self.db.execute(
            select(Teacher).where(Teacher.user_id == user_id)
        )
        return result.scalar_one_or_none()


class AssignmentRepository(BaseRepository[TeacherAssignment]):
    model = TeacherAssignment

    async def list_by_teacher(self, teacher_id: str, year_id: str | None = None) -> list[TeacherAssignment]:
        stmt = select(TeacherAssignment).where(TeacherAssignment.teacher_id == teacher_id, TeacherAssignment.status == "active")
        if year_id:
            stmt = stmt.where(TeacherAssignment.year_id == year_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_section(self, section_id: str, year_id: str) -> list[TeacherAssignment]:
        result = await self.db.execute(
            select(TeacherAssignment).where(
                TeacherAssignment.section_id == section_id,
                TeacherAssignment.year_id == year_id,
                TeacherAssignment.status == "active",
            )
        )
        return list(result.scalars().all())

    async def get_existing(self, teacher_id: str, subject_id: str, section_id: str, year_id: str) -> TeacherAssignment | None:
        result = await self.db.execute(
            select(TeacherAssignment).where(
                TeacherAssignment.teacher_id == teacher_id,
                TeacherAssignment.subject_id == subject_id,
                TeacherAssignment.section_id == section_id,
                TeacherAssignment.year_id == year_id,
            )
        )
        return result.scalar_one_or_none()
