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

    # ============= دوال مساعدة لجلب الأسماء =============

    async def get_section_name(self, section_id: str) -> Optional[str]:
        """جلب اسم الشعبة"""
        result = await self.db.execute(
            select(Section.name).where(Section.id == section_id)
        )
        return result.scalar_one_or_none()

    async def get_academic_year_name(self, academic_year_id: str) -> Optional[str]:
        """جلب اسم العام الدراسي"""
        result = await self.db.execute(
            select(AcademicYear.name).where(AcademicYear.id == academic_year_id)
        )
        return result.scalar_one_or_none()

    async def get_subject_name(self, subject_id: str) -> Optional[str]:
        """جلب اسم المادة"""
        result = await self.db.execute(
            select(Subject.name).where(Subject.id == subject_id)
        )
        return result.scalar_one_or_none()

    async def get_teacher_name(self, teacher_id: str) -> Optional[str]:
        """جلب اسم المعلم"""
        result = await self.db.execute(
            select(User.full_name).where(User.id == teacher_id)
        )
        return result.scalar_one_or_none()

    async def get_room_name(self, room_id: str) -> Optional[str]:
        """جلب اسم القاعة"""
        result = await self.db.execute(
            select(Room.name).where(Room.id == room_id)
        )
        return result.scalar_one_or_none()

    async def get_period_name(self, period_id: str) -> Optional[str]:
        """جلب اسم الفترة"""
        result = await self.db.execute(
            select(Period.name).where(Period.id == period_id)
        )
        return result.scalar_one_or_none()

    # ============= الجداول =============

    async def list_schedules(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع الجداول مع الأسماء"""
        result = await self.db.execute(
            select(Schedule)
            .where(Schedule.school_id == school_id)
            .order_by(Schedule.name)
        )
        schedules = list(result.scalars().all())
        
        result_list = []
        for schedule in schedules:
            section_name = await self.get_section_name(schedule.section_id)
            year_name = await self.get_academic_year_name(schedule.academic_year_id)
            
            entries_result = await self.db.execute(
                select(ScheduleEntry)
                .where(ScheduleEntry.schedule_id == schedule.id)
            )
            entries = list(entries_result.scalars().all())
            
            result_list.append({
                "id": schedule.id,
                "name": schedule.name,
                "school_id": schedule.school_id,
                "section_id": schedule.section_id,
                "section_name": section_name,
                "academic_year_id": schedule.academic_year_id,
                "academic_year_name": year_name,
                "is_active": schedule.is_active,
                "created_at": schedule.created_at,
                "updated_at": schedule.updated_at,
                "entries": entries,
                "entries_count": len(entries)
            })
        
        return result_list

    async def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """جلب جدول بواسطة المعرف مع الأسماء"""
        result = await self.db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            return None
        
        section_name = await self.get_section_name(schedule.section_id)
        year_name = await self.get_academic_year_name(schedule.academic_year_id)
        
        return {
            "id": schedule.id,
            "name": schedule.name,
            "school_id": schedule.school_id,
            "section_id": schedule.section_id,
            "section_name": section_name,
            "academic_year_id": schedule.academic_year_id,
            "academic_year_name": year_name,
            "is_active": schedule.is_active,
            "created_at": schedule.created_at,
            "updated_at": schedule.updated_at
        }

    async def get_schedule_with_entries(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """جلب جدول مع جميع مدخلاته"""
        schedule_data = await self.get_schedule(schedule_id)
        if not schedule_data:
            return None
        
        entries_result = await self.db.execute(
            select(ScheduleEntry)
            .where(ScheduleEntry.schedule_id == schedule_id)
            .order_by(ScheduleEntry.day_of_week, ScheduleEntry.period_id)
        )
        entries = list(entries_result.scalars().all())
        
        entries_with_names = []
        for entry in entries:
            subject_name = await self.get_subject_name(entry.subject_id)
            teacher_name = await self.get_teacher_name(entry.teacher_id)
            room_name = await self.get_room_name(entry.room_id)
            period_name = await self.get_period_name(entry.period_id)
            
            entries_with_names.append({
                "id": entry.id,
                "day_of_week": entry.day_of_week,
                "period_id": entry.period_id,
                "period_name": period_name,
                "subject_id": entry.subject_id,
                "subject_name": subject_name,
                "teacher_id": entry.teacher_id,
                "teacher_name": teacher_name,
                "room_id": entry.room_id,
                "room_name": room_name,
                "note": entry.note
            })
        
        schedule_data["entries"] = entries_with_names
        schedule_data["entries_count"] = len(entries_with_names)
        
        return schedule_data

    async def create_schedule(self, school_id: str, req: ScheduleCreate) -> Schedule:
        """إنشاء جدول جديد"""
        # التحقق من وجود الشعبة
        section_result = await self.db.execute(
            select(Section).where(Section.id == req.section_id)
        )
        if not section_result.scalar_one_or_none():
            raise ValueError("الشعبة غير موجودة")
        
        # التحقق من وجود العام الدراسي
        year_result = await self.db.execute(
            select(AcademicYear).where(AcademicYear.id == req.academic_year_id)
        )
        if not year_result.scalar_one_or_none():
            raise ValueError("العام الدراسي غير موجود")
        
        # التحقق من عدم وجود جدول مكرر
        existing = await self.db.execute(
            select(Schedule)
            .where(
                Schedule.school_id == school_id,
                Schedule.section_id == req.section_id,
                Schedule.academic_year_id == req.academic_year_id
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("يوجد بالفعل جدول لهذه الشعبة في هذا العام الدراسي")
        
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
        result = await self.db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()
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
        result = await self.db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            raise NotFoundException("الجدول غير موجود")
        
        await self.db.delete(schedule)
        await self.db.flush()
        return True

    # ============= مدخلات الجدول (الحصص) =============

    async def add_entry(self, schedule_id: str, req: ScheduleEntryCreate) -> ScheduleEntry:
        """إضافة مدخل (حصة) إلى الجدول"""
        result = await self.db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        if not result.scalar_one_or_none():
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
            raise ValueError("يوجد بالفعل حصة في هذا اليوم والفترة")
        
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
        """تحديث مدخل (حصة) في الجدول"""
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
        """حذف مدخل (حصة) من الجدول"""
        result = await self.db.execute(
            select(ScheduleEntry).where(ScheduleEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise NotFoundException("المدخل غير موجود")
        
        await self.db.delete(entry)
        await self.db.flush()
        return True

    # ============= دوال جلب البيانات للقوائم =============

    async def get_all_sections(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع الشعب كقواميس"""
        result = await self.db.execute(
            select(Section)
            .where(Section.school_id == school_id)
            .where(Section.is_active == True)
            .order_by(Section.name)
        )
        sections = list(result.scalars().all())
        return [
            {"id": s.id, "name": s.name, "capacity": s.capacity, "is_active": s.is_active}
            for s in sections
        ]

    async def get_sections_objects(self, school_id: str) -> List[Section]:
        """جلب جميع الشعب كـ ORM Objects"""
        result = await self.db.execute(
            select(Section)
            .where(Section.school_id == school_id)
            .where(Section.is_active == True)
            .order_by(Section.name)
        )
        return list(result.scalars().all())

    async def get_academic_years_objects(self, school_id: str) -> List[AcademicYear]:
        """جلب جميع الأعوام الدراسية"""
        result = await self.db.execute(
            select(AcademicYear)
            .where(AcademicYear.school_id == school_id)
            .order_by(AcademicYear.name.desc())
        )
        return list(result.scalars().all())

    async def get_periods(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع الفترات"""
        result = await self.db.execute(
            select(Period)
            .where(Period.school_id == school_id)
            .order_by(Period.order)
        )
        periods = list(result.scalars().all())
        return [
            {"id": p.id, "name": p.name, "order": p.order, "start_time": p.start_time, "end_time": p.end_time}
            for p in periods
        ]

    async def get_subjects(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع المواد"""
        result = await self.db.execute(
            select(Subject)
            .where(Subject.school_id == school_id)
            .where(Subject.is_active == True)
            .order_by(Subject.name)
        )
        subjects = list(result.scalars().all())
        return [{"id": s.id, "name": s.name} for s in subjects]

    async def get_teachers(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع المعلمين"""
        try:
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
            teachers = list(result.scalars().all())
            return [{"id": t.id, "full_name": t.full_name} for t in teachers]
        except Exception as e:
            print(f"❌ خطأ في جلب المعلمين: {str(e)}")
            return []

    async def get_rooms(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع القاعات"""
        result = await self.db.execute(
            select(Room)
            .where(Room.school_id == school_id)
            .where(Room.is_active == True)
            .order_by(Room.name)
        )
        rooms = list(result.scalars().all())
        return [{"id": r.id, "name": r.name} for r in rooms]
