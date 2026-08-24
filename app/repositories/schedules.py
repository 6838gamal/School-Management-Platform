"""Schedule repositories with conflict detection."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedules import Schedule, ScheduleEntry
from app.repositories.base import BaseRepository


class ScheduleRepository(BaseRepository[Schedule]):
    model = Schedule

    async def get_by_section(self, section_id: str, year_id: str) -> Schedule | None:
        result = await self.db.execute(
            select(Schedule).where(Schedule.section_id == section_id, Schedule.year_id == year_id)
        )
        return result.scalar_one_or_none()


class ScheduleEntryRepository(BaseRepository[ScheduleEntry]):
    model = ScheduleEntry

    async def list_by_schedule(self, schedule_id: str) -> list[ScheduleEntry]:
        result = await self.db.execute(
            select(ScheduleEntry).where(ScheduleEntry.schedule_id == schedule_id)
        )
        return list(result.scalars().all())

    async def get_slot(self, schedule_id: str, day: int, period_id: str) -> ScheduleEntry | None:
        result = await self.db.execute(
            select(ScheduleEntry).where(
                ScheduleEntry.schedule_id == schedule_id,
                ScheduleEntry.day_of_week == day,
                ScheduleEntry.period_id == period_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_teacher(self, teacher_id: str) -> list[ScheduleEntry]:
        result = await self.db.execute(
            select(ScheduleEntry).where(ScheduleEntry.teacher_id == teacher_id)
        )
        return list(result.scalars().all())

    async def list_by_room(self, room_id: str) -> list[ScheduleEntry]:
        result = await self.db.execute(
            select(ScheduleEntry).where(ScheduleEntry.room_id == room_id)
        )
        return list(result.scalars().all())

    async def list_by_school(self, school_id: str) -> list[ScheduleEntry]:
        result = await self.db.execute(
            select(ScheduleEntry).where(ScheduleEntry.school_id == school_id)
        )
        return list(result.scalars().all())

    async def check_conflicts(self, school_id: str, day: int, period_id: str, teacher_id: str, room_id: str | None, section_id: str, exclude_entry_id: str | None = None) -> dict:
        """Check for teacher, room, and section conflicts."""
        stmt = select(ScheduleEntry).where(
            ScheduleEntry.school_id == school_id,
            ScheduleEntry.day_of_week == day,
            ScheduleEntry.period_id == period_id,
        )
        if exclude_entry_id:
            stmt = stmt.where(ScheduleEntry.id != exclude_entry_id)
        entries = list((await self.db.execute(stmt)).scalars().all())
        conflicts = {"teacher": [], "room": [], "section": []}
        for e in entries:
            if e.teacher_id == teacher_id:
                conflicts["teacher"].append(e)
            if room_id and e.room_id == room_id:
                conflicts["room"].append(e)
            if e.section_id == section_id:
                conflicts["section"].append(e)
        return conflicts
