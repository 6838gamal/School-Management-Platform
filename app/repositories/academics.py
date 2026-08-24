"""Academic structure repositories."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academics import AcademicYear, Grade, Period, Room, Section, Stage, Subject
from app.models.schools import School
from app.repositories.base import BaseRepository


class SchoolRepository(BaseRepository[School]):
    model = School

    async def get_by_code(self, code: str) -> School | None:
        result = await self.db.execute(select(self.model).where(self.model.code == code))
        return result.scalar_one_or_none()


class AcademicYearRepository(BaseRepository[AcademicYear]):
    model = AcademicYear

    async def get_current(self, school_id: str) -> AcademicYear | None:
        result = await self.db.execute(
            select(self.model).where(
                self.model.school_id == school_id,
                self.model.is_current == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def list_by_school(self, school_id: str) -> list[AcademicYear]:
        result = await self.db.execute(
            select(self.model).where(self.model.school_id == school_id).order_by(self.model.name.desc())
        )
        return list(result.scalars().all())


class StageRepository(BaseRepository[Stage]):
    model = Stage

    async def list_by_year(self, year_id: str) -> list[Stage]:
        result = await self.db.execute(
            select(self.model).where(self.model.year_id == year_id).order_by(self.model.order)
        )
        return list(result.scalars().all())


class GradeRepository(BaseRepository[Grade]):
    model = Grade

    async def list_by_stage(self, stage_id: str) -> list[Grade]:
        result = await self.db.execute(
            select(self.model).where(self.model.stage_id == stage_id).order_by(self.model.order)
        )
        return list(result.scalars().all())


class SectionRepository(BaseRepository[Section]):
    model = Section

    async def list_by_grade(self, grade_id: str) -> list[Section]:
        result = await self.db.execute(
            select(self.model).where(self.model.grade_id == grade_id).order_by(self.model.name)
        )
        return list(result.scalars().all())

    async def list_by_school(self, school_id: str) -> list[Section]:
        result = await self.db.execute(
            select(self.model).where(self.model.school_id == school_id).order_by(self.model.name)
        )
        return list(result.scalars().all())


class SubjectRepository(BaseRepository[Subject]):
    model = Subject

    async def list_by_school(self, school_id: str) -> list[Subject]:
        result = await self.db.execute(
            select(self.model).where(self.model.school_id == school_id).order_by(self.model.name)
        )
        return list(result.scalars().all())


class RoomRepository(BaseRepository[Room]):
    model = Room

    async def list_by_school(self, school_id: str) -> list[Room]:
        result = await self.db.execute(
            select(self.model).where(self.model.school_id == school_id).order_by(self.model.name)
        )
        return list(result.scalars().all())


class PeriodRepository(BaseRepository[Period]):
    model = Period

    async def list_by_school(self, school_id: str) -> list[Period]:
        result = await self.db.execute(
            select(self.model).where(self.model.school_id == school_id).order_by(self.model.order)
        )
        return list(result.scalars().all())
