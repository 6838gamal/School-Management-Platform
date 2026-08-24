"""Activities and behavior service."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.repositories.activities import (
    ActivityRepository, BehaviorCategoryRepository,
    BehaviorRecordRepository, ParticipantRepository,
)
from app.schemas.activities import ActivityCreate, ActivityUpdate, ParticipantAdd
from app.schemas.behavior import BehaviorCategoryCreate, BehaviorRecordCreate, BehaviorRecordUpdate


class ActivityService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.activities = ActivityRepository(db)
        self.participants = ParticipantRepository(db)

    async def create(self, school_id: str, req: ActivityCreate) -> dict:
        activity = await self.activities.create(school_id=school_id, **req.model_dump())
        return {"id": activity.id}

    async def update(self, activity_id: str, req: ActivityUpdate) -> dict:
        activity = await self.activities.get(activity_id)
        if not activity:
            raise NotFoundException("النشاط غير موجود")
        activity = await self.activities.update(activity, **req.model_dump(exclude_unset=True))
        return {"id": activity.id}

    async def delete(self, activity_id: str) -> None:
        activity = await self.activities.get(activity_id)
        if not activity:
            raise NotFoundException("النشاط غير موجود")
        await self.activities.delete(activity)

    async def list_activities(self, school_id: str, status: str | None = None) -> list[dict]:
        items = await self.activities.list_by_school(school_id, status)
        return [
            {"id": a.id, "title": a.title, "status": a.status, "start_date": a.start_date, "end_date": a.end_date}
            for a in items
        ]

    async def add_participant(self, req: ParticipantAdd) -> dict:
        p = await self.participants.create(**req.model_dump())
        return {"id": p.id}

    async def list_participants(self, activity_id: str) -> list[dict]:
        items = await self.participants.list_by_activity(activity_id)
        return [{"id": p.id, "student_id": p.student_id, "role": p.role, "result": p.result} for p in items]


class BehaviorService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.categories = BehaviorCategoryRepository(db)
        self.records = BehaviorRecordRepository(db)

    async def create_category(self, school_id: str, req: BehaviorCategoryCreate) -> dict:
        cat = await self.categories.create(school_id=school_id, **req.model_dump())
        return {"id": cat.id}

    async def list_categories(self, school_id: str) -> list[dict]:
        items = await self.categories.list_by_school(school_id)
        return [{"id": c.id, "name": c.name, "type": c.type, "default_severity": c.default_severity} for c in items]

    async def create_record(self, school_id: str, user_id: str, req: BehaviorRecordCreate) -> dict:
        record = await self.records.create(school_id=school_id, recorded_by=user_id, **req.model_dump())
        return {"id": record.id}

    async def update_record(self, record_id: str, req: BehaviorRecordUpdate) -> dict:
        record = await self.records.get(record_id)
        if not record:
            raise NotFoundException("السجل غير موجود")
        record = await self.records.update(record, **req.model_dump(exclude_unset=True))
        return {"id": record.id}

    async def student_records(self, student_id: str) -> list[dict]:
        items = await self.records.list_by_student(student_id)
        return [
            {"id": r.id, "type": r.type, "severity": r.severity, "title": r.title, "date": r.date}
            for r in items
        ]

    async def school_records(self, school_id: str, limit: int = 50) -> list[dict]:
        items = await self.records.list_by_school(school_id, limit)
        return [
            {"id": r.id, "student_id": r.student_id, "type": r.type, "severity": r.severity, "title": r.title, "date": r.date}
            for r in items
        ]
