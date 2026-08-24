"""Homework repositories."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.homework import Homework, HomeworkSubmission
from app.repositories.base import BaseRepository


class HomeworkRepository(BaseRepository[Homework]):
    model = Homework

    async def list_by_section(self, section_id: str) -> list[Homework]:
        result = await self.db.execute(
            select(Homework).where(Homework.section_id == section_id).order_by(Homework.due_date.desc())
        )
        return list(result.scalars().all())

    async def list_by_teacher(self, teacher_id: str) -> list[Homework]:
        result = await self.db.execute(
            select(Homework).where(Homework.teacher_id == teacher_id).order_by(Homework.due_date.desc())
        )
        return list(result.scalars().all())


class SubmissionRepository(BaseRepository[HomeworkSubmission]):
    model = HomeworkSubmission

    async def get_by_homework_student(self, homework_id: str, student_id: str) -> HomeworkSubmission | None:
        result = await self.db.execute(
            select(HomeworkSubmission).where(
                HomeworkSubmission.homework_id == homework_id,
                HomeworkSubmission.student_id == student_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_homework(self, homework_id: str) -> list[HomeworkSubmission]:
        result = await self.db.execute(
            select(HomeworkSubmission).where(HomeworkSubmission.homework_id == homework_id)
        )
        return list(result.scalars().all())
