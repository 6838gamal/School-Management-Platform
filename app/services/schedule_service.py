"""Schedule service."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional, Dict, Any

from app.core.exceptions import NotFoundException
from app.models.academics import Section, Period, Subject, Room, AcademicYear, Grade, Stage
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
        """جلب جميع الجداول لمدرسة معينة (بدون علاقات)"""
        result = await self.db.execute(
            select(Schedule)
            .where(Schedule.school_id == school_id)
            .order_by(Schedule.name)
        )
        schedules = list(result.scalars().all())
        
        # جلب المدخلات لكل جدول بشكل منفصل
        for schedule in schedules:
            entries_result = await self.db.execute(
                select(ScheduleEntry)
                .where(ScheduleEntry.schedule_id == schedule.id)
            )
            schedule.entries = list(entries_result.scalars().all())
        
        return schedules

    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """جلب جدول بواسطة المعرف"""
        result = await self.db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        return result.scalar_one_or_none()

    async def get_schedule_with_entries(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """جلب جدول مع جميع مدخلاته (كقاموس)"""
        # جلب الجدول
        result = await self.db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            return None
        
        # جلب المدخلات
        entries_result = await self.db.execute(
            select(ScheduleEntry)
            .where(ScheduleEntry.schedule_id == schedule_id)
            .order_by(ScheduleEntry.day_of_week, ScheduleEntry.period_id)
        )
        entries = list(entries_result.scalars().all())
        
        # جلب اسم الشعبة
        section_name = None
        if schedule.section_id:
            section_result = await self.db.execute(
                select(Section).where(Section.id == schedule.section_id)
            )
            section = section_result.scalar_one_or_none()
            section_name = section.name if section else None
        
        # جلب اسم العام الدراسي
        year_name = None
        if schedule.academic_year_id:
            year_result = await self.db.execute(
                select(AcademicYear).where(AcademicYear.id == schedule.academic_year_id)
            )
            year = year_result.scalar_one_or_none()
            year_name = year.name if year else None
        
        # بناء البيانات
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
            "updated_at": schedule.updated_at,
            "entries": entries
        }

    async def create_schedule(self, school_id: str, req: ScheduleCreate) -> Schedule:
        """إنشاء جدول جديد لشعبة معينة"""
        # التحقق من وجود الشعبة
        section_result = await self.db.execute(
            select(Section).where(Section.id == req.section_id)
        )
        section = section_result.scalar_one_or_none()
        if not section:
            raise ValueError("الشعبة غير موجودة")
        
        # التحقق من وجود العام الدراسي
        year_result = await self.db.execute(
            select(AcademicYear).where(AcademicYear.id == req.academic_year_id)
        )
        year = year_result.scalar_one_or_none()
        if not year:
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
        # التحقق من وجود الجدول
        result = await self.db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            raise NotFoundException("الجدول غير موجود")
        
        # التحقق من وجود الفترة
        period_result = await self.db.execute(
            select(Period).where(Period.id == req.period_id)
        )
        if not period_result.scalar_one_or_none():
            raise ValueError("الفترة غير موجودة")
        
        # التحقق من وجود المادة
        subject_result = await self.db.execute(
            select(Subject).where(Subject.id == req.subject_id)
        )
        if not subject_result.scalar_one_or_none():
            raise ValueError("المادة غير موجودة")
        
        # التحقق من وجود المعلم
        teacher_result = await self.db.execute(
            select(User).where(User.id == req.teacher_id)
        )
        if not teacher_result.scalar_one_or_none():
            raise ValueError("المعلم غير موجود")
        
        # التحقق من وجود القاعة
        room_result = await self.db.execute(
            select(Room).where(Room.id == req.room_id)
        )
        if not room_result.scalar_one_or_none():
            raise ValueError("القاعة غير موجودة")
        
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

    # ============= دوال جلب البيانات =============

    async def get_all_sections(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع الشعب المتاحة في المدرسة كقواميس"""
        try:
            result = await self.db.execute(
                select(Section)
                .where(Section.school_id == school_id)
                .where(Section.is_active == True)
                .order_by(Section.name)
            )
            sections = list(result.scalars().all())
            print(f"✅ تم جلب {len(sections)} شعبة للمدرسة {school_id}")
            return [
                {
                    "id": s.id,
                    "name": s.name,
                    "capacity": s.capacity,
                    "is_active": s.is_active,
                    "grade_id": s.grade_id
                }
                for s in sections
            ]
        except Exception as e:
            print(f"❌ خطأ في جلب الشعب: {str(e)}")
            return []

    async def get_sections_objects(self, school_id: str) -> List[Section]:
        """جلب جميع الشعب كـ ORM Objects"""
        try:
            result = await self.db.execute(
                select(Section)
                .where(Section.school_id == school_id)
                .where(Section.is_active == True)
                .order_by(Section.name)
            )
            sections = list(result.scalars().all())
            print(f"✅ تم جلب {len(sections)} شعبة للمدرسة {school_id}")
            return sections
        except Exception as e:
            print(f"❌ خطأ في جلب الشعب: {str(e)}")
            return []

    async def get_academic_years_objects(self, school_id: str) -> List[AcademicYear]:
        """جلب جميع الأعوام الدراسية للمدرسة"""
        try:
            result = await self.db.execute(
                select(AcademicYear)
                .where(AcademicYear.school_id == school_id)
                .order_by(AcademicYear.name.desc())
            )
            years = list(result.scalars().all())
            print(f"✅ تم جلب {len(years)} عام دراسي للمدرسة {school_id}")
            return years
        except Exception as e:
            print(f"❌ خطأ في جلب الأعوام الدراسية: {str(e)}")
            return []

    async def get_current_academic_year(self, school_id: str) -> Optional[AcademicYear]:
        """جلب العام الدراسي الحالي"""
        result = await self.db.execute(
            select(AcademicYear)
            .where(AcademicYear.school_id == school_id)
            .where(AcademicYear.is_current == True)
        )
        return result.scalar_one_or_none()

    async def get_periods(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع الفترات مع تفاصيلها"""
        result = await self.db.execute(
            select(Period)
            .where(Period.school_id == school_id)
            .order_by(Period.order)
        )
        periods = list(result.scalars().all())
        return [
            {
                "id": p.id, 
                "name": p.name, 
                "order": p.order, 
                "start_time": p.start_time, 
                "end_time": p.end_time,
                "is_break": p.is_break
            } 
            for p in periods
        ]

    async def get_period_by_id(self, period_id: str) -> Optional[Period]:
        """جلب فترة بواسطة المعرف"""
        result = await self.db.execute(
            select(Period).where(Period.id == period_id)
        )
        return result.scalar_one_or_none()

    async def get_subjects(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع المواد مع تفاصيلها"""
        result = await self.db.execute(
            select(Subject)
            .where(Subject.school_id == school_id)
            .where(Subject.is_active == True)
            .order_by(Subject.name)
        )
        subjects = list(result.scalars().all())
        return [
            {
                "id": s.id, 
                "name": s.name, 
                "name_en": s.name_en,
                "code": s.code,
                "color": s.color
            } 
            for s in subjects
        ]

    async def get_subject_by_id(self, subject_id: str) -> Optional[Subject]:
        """جلب مادة بواسطة المعرف"""
        result = await self.db.execute(
            select(Subject).where(Subject.id == subject_id)
        )
        return result.scalar_one_or_none()

    async def get_teachers(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع المعلمين مع تفاصيلهم"""
        try:
            role_result = await self.db.execute(
                select(Role).where(
                    Role.key == "teacher", 
                    Role.school_id == school_id
                )
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
            return [
                {
                    "id": t.id, 
                    "full_name": t.full_name,
                    "email": t.email,
                    "phone": t.phone
                } 
                for t in teachers
            ]
        except Exception as e:
            print(f"❌ خطأ في جلب المعلمين: {str(e)}")
            return []

    async def get_teacher_by_id(self, teacher_id: str) -> Optional[User]:
        """جلب معلم بواسطة المعرف"""
        result = await self.db.execute(
            select(User).where(User.id == teacher_id)
        )
        return result.scalar_one_or_none()

    async def get_rooms(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع القاعات مع تفاصيلها"""
        result = await self.db.execute(
            select(Room)
            .where(Room.school_id == school_id)
            .where(Room.is_active == True)
            .order_by(Room.name)
        )
        rooms = list(result.scalars().all())
        return [
            {
                "id": r.id, 
                "name": r.name,
                "building": r.building,
                "floor": r.floor,
                "capacity": r.capacity
            } 
            for r in rooms
        ]

    async def get_room_by_id(self, room_id: str) -> Optional[Room]:
        """جلب قاعة بواسطة المعرف"""
        result = await self.db.execute(
            select(Room).where(Room.id == room_id)
        )
        return result.scalar_one_or_none()

    # ============= دوال مساعدة إضافية =============

    async def get_schedule_entries_count(self, schedule_id: str) -> int:
        """جلب عدد الحصص في جدول معين"""
        result = await self.db.execute(
            select(ScheduleEntry)
            .where(ScheduleEntry.schedule_id == schedule_id)
        )
        return len(list(result.scalars().all()))

    async def check_schedule_exists(self, school_id: str, section_id: str, academic_year_id: str) -> bool:
        """التحقق من وجود جدول لشعبة معينة في عام معين"""
        result = await self.db.execute(
            select(Schedule)
            .where(
                Schedule.school_id == school_id,
                Schedule.section_id == section_id,
                Schedule.academic_year_id == academic_year_id
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_schedules_by_section(self, section_id: str) -> List[Schedule]:
        """جلب جميع الجداول لشعبة معينة"""
        result = await self.db.execute(
            select(Schedule)
            .where(Schedule.section_id == section_id)
            .order_by(Schedule.name)
        )
        return list(result.scalars().all())
