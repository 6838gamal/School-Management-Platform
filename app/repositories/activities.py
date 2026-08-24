"""Activities and behavior repositories."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activities import Activity, ActivityParticipant
from app.models.behavior import BehaviorCategory, BehaviorRecord
from app.repositories.base import BaseRepository


class ActivityRepository(BaseRepository[Activity]):
    model = Activity

    async def list_by_school(self, school_id: str, status: str | None = None) -> list[Activity]:
        stmt = select(Activity).where(Activity.school_id == school_id)
        if status:
            stmt = stmt.where(Activity.status == status)
        result = await self.db.execute(stmt.order_by(Activity.start_date.desc()))
        return list(result.scalars().all())


class ParticipantRepository(BaseRepository[ActivityParticipant]):
    model = ActivityParticipant

    async def list_by_activity(self, activity_id: str) -> list[ActivityParticipant]:
        result = await self.db.execute(
            select(ActivityParticipant).where(ActivityParticipant.activity_id == activity_id)
        )
        return list(result.scalars().all())


class BehaviorCategoryRepository(BaseRepository[BehaviorCategory]):
    model = BehaviorCategory

    async def list_by_school(self, school_id: str) -> list[BehaviorCategory]:
        result = await self.db.execute(
            select(BehaviorCategory).where(BehaviorCategory.school_id == school_id)
        )
        return list(result.scalars().all())


class BehaviorRecordRepository(BaseRepository[BehaviorRecord]):
    model = BehaviorRecord

    async def list_by_student(self, student_id: str) -> list[BehaviorRecord]:
        result = await self.db.execute(
            select(BehaviorRecord).where(BehaviorRecord.student_id == student_id).order_by(BehaviorRecord.date.desc())
        )
        return list(result.scalars().all())

    async def list_by_school(self, school_id: str, limit: int = 50) -> list[BehaviorRecord]:
        result = await self.db.execute(
            select(BehaviorRecord).where(BehaviorRecord.school_id == school_id).order_by(BehaviorRecord.date.desc()).limit(limit)
        )
        return list(result.scalars().all())
