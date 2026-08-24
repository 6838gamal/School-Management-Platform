"""Grades repositories."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.grades import Assessment, GradeRecord
from app.repositories.base import BaseRepository


class AssessmentRepository(BaseRepository[Assessment]):
    model = Assessment

    async def list_by_section(self, section_id: str) -> list[Assessment]:
        result = await self.db.execute(
            select(Assessment).where(Assessment.section_id == section_id).order_by(Assessment.date.desc())
        )
        return list(result.scalars().all())

    async def list_by_subject(self, subject_id: str) -> list[Assessment]:
        result = await self.db.execute(
            select(Assessment).where(Assessment.subject_id == subject_id)
        )
        return list(result.scalars().all())


class GradeRecordRepository(BaseRepository[GradeRecord]):
    model = GradeRecord

    async def get_by_assessment_student(self, assessment_id: str, student_id: str) -> GradeRecord | None:
        result = await self.db.execute(
            select(GradeRecord).where(GradeRecord.assessment_id == assessment_id, GradeRecord.student_id == student_id)
        )
        return result.scalar_one_or_none()

    async def list_by_assessment(self, assessment_id: str) -> list[GradeRecord]:
        result = await self.db.execute(
            select(GradeRecord).where(GradeRecord.assessment_id == assessment_id)
        )
        return list(result.scalars().all())

    async def list_by_student(self, student_id: str) -> list[GradeRecord]:
        result = await self.db.execute(
            select(GradeRecord).where(GradeRecord.student_id == student_id)
        )
        return list(result.scalars().all())
