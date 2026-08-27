"""Schedule service."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional, Dict, Any

from app.core.exceptions import NotFoundException
from app.models.academics import Section, Period, Subject, Room, AcademicYear
from app.models.schedules import Schedule, ScheduleEntry
from app.models.users import User, UserRole, Role
from app.schemas.schedules import (
    ScheduleCreate, ScheduleUpdate, 
    ScheduleEntryCreate, ScheduleEntryUpdate
)


class ScheduleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ============= الجداول =============

    async def list_schedules(self, school_id: str) -> List[Schedule]:
        """جلب جميع الجداول لمدرسة معينة"""
        result = await self.db.execute(
            select(Schedule)
            .where(Schedule.school_id == school_id)
            .order_by(Schedule.name)
        )
        return list(result.scalars().all())

    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """جلب جدول بواسطة المعرف"""
        result = await self.db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        return result.scalar_one_or_none()

    async def get_schedule_with_entries(self, schedule_id: str) -> Optional[Schedule]:
        """جلب جدول مع جميع مدخلاته"""
        result = await self.db.execute(
            select(Schedule)
            .where(Schedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()
        if schedule:
            entries_result = await self.db.execute(
                select(ScheduleEntry)
                .where(ScheduleEntry.schedule_id == schedule_id)
                .order_by(ScheduleEntry.day_of_week, ScheduleEntry.period_id)
            )
            schedule.entries = list(entries_result.scalars().all())
        return schedule

    async def create_schedule(self, school_id: str, req: ScheduleCreate) -> Schedule:
        """إنشاء جدول جديد"""
        schedule = Schedule(
            school_id=school_id,
            name=req.name,
            section_id=req.section_id,
            academic_year_id=req.academic_year_id,
            is_active=req.is_active,
        )
        self.db.add(schedule)
        await self.db.flush()
        await self.db.refresh(schedule)
        return schedule

    async def update_schedule(self, schedule_id: str, req: ScheduleUpdate) -> Schedule:
        """تحديث جدول"""
        schedule = await self.get_schedule(schedule_id)
        if not schedule:
            raise NotFoundException("الجدول غير موجود")
        
        update_data = req.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(schedule, key):
                setattr(schedule, key, value)
        
        await self.db.flush()
        await self.db.refresh(schedule)
        return schedule

    async def delete_schedule(self, schedule_id: str) -> bool:
        """حذف جدول"""
        schedule = await self.get_schedule(schedule_id)
        if not schedule:
            raise NotFoundException("الجدول غير موجود")
        
        await self.db.delete(schedule)
        await self.db.flush()
        return True

    # ============= مدخلات الجدول =============

    async def add_entry(self, schedule_id: str, req: ScheduleEntryCreate) -> ScheduleEntry:
        """إضافة مدخل إلى الجدول"""
        schedule = await self.get_schedule(schedule_id)
        if not schedule:
            raise NotFoundException("الجدول غير موجود")
        
        # التحقق من عدم وجود تعارض
        existing = await self.db.execute(
            select(ScheduleEntry)
            .where(
                ScheduleEntry.schedule_id == schedule_id,
                ScheduleEntry.day_of_week == req.day_of_week,
                ScheduleEntry.period_id == req.period_id
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("يوجد بالفعل مدخل في هذا اليوم والفترة")
        
        entry = ScheduleEntry(
            schedule_id=schedule_id,
            day_of_week=req.day_of_week,
            period_id=req.period_id,
            subject_id=req.subject_id,
            teacher_id=req.teacher_id,
            room_id=req.room_id,
            note=req.note,
        )
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        return entry

    async def update_entry(self, entry_id: str, req: ScheduleEntryUpdate) -> ScheduleEntry:
        """تحديث مدخل في الجدول"""
        result = await self.db.execute(
            select(ScheduleEntry).where(ScheduleEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise NotFoundException("المدخل غير موجود")
        
        update_data = req.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        
        await self.db.flush()
        await self.db.refresh(entry)
        return entry

    async def delete_entry(self, entry_id: str) -> bool:
        """حذف مدخل من الجدول"""
        result = await self.db.execute(
            select(ScheduleEntry).where(ScheduleEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise NotFoundException("المدخل غير موجود")
        
        await self.db.delete(entry)
        await self.db.flush()
        return True

    # ============= دوال مساعدة لجلب البيانات =============

    async def get_sections(self, school_id: str) -> List[Section]:
        """جلب جميع الشعب لمدرسة معينة"""
        result = await self.db.execute(
            select(Section)
            .where(Section.school_id == school_id)
            .where(Section.is_active == True)
            .order_by(Section.name)
        )
        return list(result.scalars().all())

    async def get_periods(self, school_id: str) -> List[Period]:
        """جلب جميع الفترات لمدرسة معينة"""
        result = await self.db.execute(
            select(Period)
            .where(Period.school_id == school_id)
            .order_by(Period.order)
        )
        return list(result.scalars().all())

    async def get_subjects(self, school_id: str) -> List[Subject]:
        """جلب جميع المواد لمدرسة معينة"""
        result = await self.db.execute(
            select(Subject)
            .where(Subject.school_id == school_id)
            .where(Subject.is_active == True)
            .order_by(Subject.name)
        )
        return list(result.scalars().all())

    async def get_teachers(self, school_id: str) -> List[User]:
        """جلب جميع المعلمين لمدرسة معينة"""
        role_result = await self.db.execute(
            select(Role).where(Role.key == "teacher", Role.school_id == school_id)
        )
        teacher_role = role_result.scalar_one_or_none()
        
        if not teacher_role:
            return []
        
        result = await self.db.execute(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .where(UserRole.role_id == teacher_role.id)
            .where(User.school_id == school_id)
            .where(User.is_active == True)
            .order_by(User.full_name)
        )
        return list(result.scalars().all())

    async def get_rooms(self, school_id: str) -> List[Room]:
        """جلب جميع القاعات لمدرسة معينة"""
        result = await self.db.execute(
            select(Room)
            .where(Room.school_id == school_id)
            .where(Room.is_active == True)
            .order_by(Room.name)
        )
        return list(result.scalars().all())

    async def get_academic_years(self, school_id: str) -> List[AcademicYear]:
        """جلب جميع الأعوام الدراسية لمدرسة معينة"""
        result = await self.db.execute(
            select(AcademicYear)
            .where(AcademicYear.school_id == school_id)
            .order_by(AcademicYear.name.desc())
        )
        return list(result.scalars().all())
