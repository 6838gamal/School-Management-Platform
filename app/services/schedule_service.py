"""Schedule service with conflict detection and replacement suggestions."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.repositories.academics import PeriodRepository, SectionRepository, SubjectRepository
from app.repositories.attendance import TeacherAttendanceRepository
from app.repositories.schedules import ScheduleEntryRepository, ScheduleRepository
from app.repositories.teachers import AssignmentRepository, TeacherRepository
from app.schemas.schedules import ScheduleEntryCreate, ScheduleEntryUpdate


class ScheduleService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.schedules = ScheduleRepository(db)
        self.entries = ScheduleEntryRepository(db)
        self.teachers = TeacherRepository(db)
        self.assignments = AssignmentRepository(db)
        self.periods = PeriodRepository(db)
        self.sections = SectionRepository(db)
        self.subjects = SubjectRepository(db)
        self.teacher_att = TeacherAttendanceRepository(db)

    async def get_or_create_schedule(self, school_id: str, year_id: str, section_id: str) -> str:
        sched = await self.schedules.get_by_section(section_id, year_id)
        if sched:
            return sched.id
        section = await self.sections.get(section_id)
        name = f"جدول {section.name}" if section else "جدول"
        sched = await self.schedules.create(
            school_id=school_id, year_id=year_id, section_id=section_id, name=name, is_active=True,
        )
        return sched.id

    async def get_weekly_grid(self, schedule_id: str) -> dict:
        entries = await self.entries.list_by_schedule(schedule_id)
        periods = await self.periods.list_by_school(entries[0].school_id if entries else "")
        grid: dict[int, dict[str, dict]] = {}
        for e in entries:
            grid.setdefault(e.day_of_week, {})[e.period_id] = {
                "id": e.id, "subject_id": e.subject_id, "teacher_id": e.teacher_id, "room_id": e.room_id,
            }
        return {"periods": [{"id": p.id, "name": p.name, "order": p.order} for p in periods], "grid": grid}

    async def add_entry(self, school_id: str, schedule_id: str, req: ScheduleEntryCreate) -> dict:
        conflicts = await self.entries.check_conflicts(
            school_id, req.day_of_week, req.period_id, req.teacher_id, req.room_id, req.section_id,
        )
        conflict_list = {k: [{"id": e.id, "day": e.day_of_week} for e in v] for k, v in conflicts.items() if v}
        if conflict_list:
            raise ConflictException(f"تعارض: {conflict_list}")
        entry = await self.entries.create(
            schedule_id=schedule_id,
            school_id=school_id,
            day_of_week=req.day_of_week,
            period_id=req.period_id,
            subject_id=req.subject_id,
            teacher_id=req.teacher_id,
            room_id=req.room_id,
            section_id=req.section_id,
        )
        return {"id": entry.id}

    async def update_entry(self, entry_id: str, req: ScheduleEntryUpdate) -> dict:
        entry = await self.entries.get(entry_id)
        if not entry:
            raise NotFoundException("الحصة غير موجودة")
        entry = await self.entries.update(entry, **req.model_dump(exclude_unset=True))
        return {"id": entry.id}

    async def delete_entry(self, entry_id: str) -> None:
        entry = await self.entries.get(entry_id)
        if not entry:
            raise NotFoundException("الحصة غير موجودة")
        await self.entries.delete(entry)

    async def suggest_replacements(self, school_id: str, absent_teacher_id: str, date: str) -> list[dict]:
        """Find available teachers to replace an absent teacher's lessons."""
        all_teachers = await self.teachers.list_by_school(school_id, page=1, page_size=200)
        absent_entries = await self.entries.list_by_teacher(absent_teacher_id)
        suggestions = []
        for t in all_teachers[0]:
            if t.id == absent_teacher_id or not t.is_active:
                continue
            teacher_entries = await self.entries.list_by_teacher(t.id)
            busy_periods = {(e.day_of_week, e.period_id) for e in teacher_entries}
            free_count = sum(
                1 for e in absent_entries if (e.day_of_week, e.period_id) not in busy_periods
            )
            if free_count > 0:
                suggestions.append({
                    "teacher_id": t.id,
                    "teacher_name": f"{t.first_name} {t.last_name}",
                    "free_periods": free_count,
                    "specialization": t.specialization,
                })
        suggestions.sort(key=lambda x: x["free_periods"], reverse=True)
        return suggestions[:10]
