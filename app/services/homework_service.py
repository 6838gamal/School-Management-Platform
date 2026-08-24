"""Homework service."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.repositories.homework import HomeworkRepository, SubmissionRepository
from app.schemas.homework import HomeworkCreate, HomeworkUpdate, SubmissionUpdate


class HomeworkService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.homework = HomeworkRepository(db)
        self.submissions = SubmissionRepository(db)

    async def create(self, school_id: str, req: HomeworkCreate) -> dict:
        hw = await self.homework.create(school_id=school_id, **req.model_dump())
        return {"id": hw.id}

    async def update(self, homework_id: str, req: HomeworkUpdate) -> dict:
        hw = await self.homework.get(homework_id)
        if not hw:
            raise NotFoundException("الواجب غير موجود")
        hw = await self.homework.update(hw, **req.model_dump(exclude_unset=True))
        return {"id": hw.id}

    async def delete(self, homework_id: str) -> None:
        hw = await self.homework.get(homework_id)
        if not hw:
            raise NotFoundException("الواجب غير موجود")
        await self.homework.delete(hw)

    async def list_by_section(self, section_id: str) -> list[dict]:
        items = await self.homework.list_by_section(section_id)
        return [
            {"id": h.id, "title": h.title, "due_date": h.due_date, "is_graded": h.is_graded}
            for h in items
        ]

    async def list_by_teacher(self, teacher_id: str) -> list[dict]:
        items = await self.homework.list_by_teacher(teacher_id)
        return [
            {"id": h.id, "title": h.title, "due_date": h.due_date, "is_graded": h.is_graded, "section_id": h.section_id}
            for h in items
        ]

    async def update_submission(self, homework_id: str, student_id: str, req: SubmissionUpdate) -> dict:
        sub = await self.submissions.get_by_homework_student(homework_id, student_id)
        if not sub:
            from datetime import datetime, timezone
            sub = await self.submissions.create(
                homework_id=homework_id, student_id=student_id, status="submitted",
                submitted_at=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            )
        sub = await self.submissions.update(sub, **req.model_dump(exclude_unset=True))
        return {"id": sub.id}
