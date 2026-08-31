"""Schedule service."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
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

    # ============= دوال مساعدة للبحث والتحقق =============

    async def find_section_by_id(self, section_id: str) -> Optional[Section]:
        """البحث عن شعبة بالمعرف مع تحميل العلاقات"""
        result = await self.db.execute(
            select(Section)
            .options(
                selectinload(Section.grade).selectinload(Grade.stage)
            )
            .where(Section.id == section_id)
        )
        return result.scalar_one_or_none()

    async def find_academic_year_by_id(self, year_id: str) -> Optional[AcademicYear]:
        """البحث عن عام دراسي بالمعرف"""
        result = await self.db.execute(
            select(AcademicYear).where(AcademicYear.id == year_id)
        )
        return result.scalar_one_or_none()

    async def find_subject_by_id(self, subject_id: str) -> Optional[Subject]:
        """البحث عن مادة بالمعرف"""
        result = await self.db.execute(
            select(Subject).where(Subject.id == subject_id)
        )
        return result.scalar_one_or_none()

    async def find_teacher_by_id(self, teacher_id: str) -> Optional[User]:
        """البحث عن معلم بالمعرف"""
        result = await self.db.execute(
            select(User).where(User.id == teacher_id)
        )
        return result.scalar_one_or_none()

    async def find_room_by_id(self, room_id: str) -> Optional[Room]:
        """البحث عن قاعة بالمعرف"""
        result = await self.db.execute(
            select(Room).where(Room.id == room_id)
        )
        return result.scalar_one_or_none()

    async def find_period_by_id(self, period_id: str) -> Optional[Period]:
        """البحث عن فترة بالمعرف"""
        result = await self.db.execute(
            select(Period).where(Period.id == period_id)
        )
        return result.scalar_one_or_none()

    async def find_schedule_duplicate(
        self, 
        school_id: str, 
        section_id: str, 
        academic_year_id: str
    ) -> Optional[Schedule]:
        """البحث عن جدول مكرر - استخدام year_id في قاعدة البيانات"""
        result = await self.db.execute(
            select(Schedule)
            .where(
                Schedule.school_id == school_id,
                Schedule.section_id == section_id,
                Schedule.year_id == academic_year_id
            )
        )
        return result.scalar_one_or_none()

    async def find_entry_conflict(
        self,
        schedule_id: str,
        day_of_week: int,
        period_id: str
    ) -> Optional[ScheduleEntry]:
        """البحث عن تعارض في الحصص (نفس اليوم والفترة)"""
        result = await self.db.execute(
            select(ScheduleEntry)
            .where(
                ScheduleEntry.schedule_id == schedule_id,
                ScheduleEntry.day_of_week == day_of_week,
                ScheduleEntry.period_id == period_id
            )
        )
        return result.scalar_one_or_none()

    # ============= دوال مساعدة لجلب الأسماء =============

    async def get_section_name(self, section_id: str) -> Optional[str]:
        """جلب اسم الشعبة"""
        section = await self.find_section_by_id(section_id)
        return section.name if section else None

    async def get_academic_year_name(self, academic_year_id: str) -> Optional[str]:
        """جلب اسم العام الدراسي"""
        year = await self.find_academic_year_by_id(academic_year_id)
        return year.name if year else None

    async def get_subject_name(self, subject_id: str) -> Optional[str]:
        """جلب اسم المادة"""
        subject = await self.find_subject_by_id(subject_id)
        return subject.name if subject else None

    async def get_teacher_name(self, teacher_id: str) -> Optional[str]:
        """جلب اسم المعلم"""
        teacher = await self.find_teacher_by_id(teacher_id)
        return teacher.full_name if teacher else None

    async def get_room_name(self, room_id: str) -> Optional[str]:
        """جلب اسم القاعة"""
        room = await self.find_room_by_id(room_id)
        return room.name if room else None

    async def get_period_name(self, period_id: str) -> Optional[str]:
        """جلب اسم الفترة"""
        period = await self.find_period_by_id(period_id)
        return period.name if period else None

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
            year_name = await self.get_academic_year_name(schedule.year_id)
            
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
                "year_id": schedule.year_id,
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
        year_name = await self.get_academic_year_name(schedule.year_id)
        
        return {
            "id": schedule.id,
            "name": schedule.name,
            "school_id": schedule.school_id,
            "section_id": schedule.section_id,
            "section_name": section_name,
            "year_id": schedule.year_id,
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
            })
        
        schedule_data["entries"] = entries_with_names
        schedule_data["entries_count"] = len(entries_with_names)
        
        return schedule_data

    async def create_schedule(self, school_id: str, req: ScheduleCreate) -> Schedule:
        """إنشاء جدول جديد مع البحث اليدوي عن العلاقات"""
        
        print("=" * 50)
        print("📝 إنشاء جدول جديد:")
        print(f"   school_id: {school_id}")
        print(f"   name: {req.name}")
        print(f"   section_id: {req.section_id}")
        print(f"   academic_year_id: {req.academic_year_id}")
        print(f"   is_active: {req.is_active}")
        print("=" * 50)
        
        if not school_id:
            raise ValueError("معرف المدرسة غير موجود")
        
        if not req.section_id:
            raise ValueError("معرف الشعبة مطلوب")
        
        section = await self.find_section_by_id(req.section_id)
        if not section:
            all_sections = await self.db.execute(
                select(Section).where(Section.school_id == school_id)
            )
            sections_list = list(all_sections.scalars().all())
            section_ids = [s.id for s in sections_list]
            print(f"⚠️ الشعب الموجودة: {section_ids}")
            raise ValueError(f"الشعبة غير موجودة: {req.section_id}")
        
        print(f"✅ تم العثور على الشعبة: {section.name}")
        
        if not req.academic_year_id:
            raise ValueError("معرف العام الدراسي مطلوب")
        
        year = await self.find_academic_year_by_id(req.academic_year_id)
        if not year:
            all_years = await self.db.execute(
                select(AcademicYear).where(AcademicYear.school_id == school_id)
            )
            years_list = list(all_years.scalars().all())
            year_ids = [y.id for y in years_list]
            print(f"⚠️ الأعوام الموجودة: {year_ids}")
            raise ValueError(f"العام الدراسي غير موجود: {req.academic_year_id}")
        
        print(f"✅ تم العثور على العام الدراسي: {year.name}")
        
        duplicate = await self.find_schedule_duplicate(
            school_id, req.section_id, req.academic_year_id
        )
        if duplicate:
            raise ValueError("يوجد بالفعل جدول لهذه الشعبة في هذا العام الدراسي")
        
        print("✅ لا يوجد جدول مكرر")
        
        schedule = Schedule(
            school_id=school_id,
            name=req.name,
            section_id=req.section_id,
            year_id=req.academic_year_id,
            is_active=req.is_active,
        )
        self.db.add(schedule)
        await self.db.flush()
        await self.db.refresh(schedule)
        
        print(f"✅ تم إنشاء الجدول بنجاح: {schedule.id}")
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
        """إضافة مدخل (حصة) إلى الجدول مع البحث اليدوي"""
        
        print("=" * 50)
        print("📝 إضافة حصة جديدة:")
        print(f"   schedule_id: {schedule_id}")
        print(f"   day_of_week: {req.day_of_week}")
        print(f"   period_id: {req.period_id}")
        print(f"   subject_id: {req.subject_id}")
        print(f"   teacher_id: {req.teacher_id}")
        print(f"   room_id: {req.room_id}")
        print("=" * 50)
        
        schedule_result = await self.db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        if not schedule_result.scalar_one_or_none():
            raise NotFoundException("الجدول غير موجود")
        
        subject = await self.find_subject_by_id(req.subject_id)
        if not subject:
            raise ValueError(f"المادة غير موجودة: {req.subject_id}")
        print(f"✅ تم العثور على المادة: {subject.name}")
        
        teacher = await self.find_teacher_by_id(req.teacher_id)
        if not teacher:
            raise ValueError(f"المعلم غير موجود: {req.teacher_id}")
        print(f"✅ تم العثور على المعلم: {teacher.full_name}")
        
        room = await self.find_room_by_id(req.room_id)
        if not room:
            raise ValueError(f"القاعة غير موجودة: {req.room_id}")
        print(f"✅ تم العثور على القاعة: {room.name}")
        
        period = await self.find_period_by_id(req.period_id)
        if not period:
            raise ValueError(f"الفترة غير موجودة: {req.period_id}")
        print(f"✅ تم العثور على الفترة: {period.name}")
        
        conflict = await self.find_entry_conflict(
            schedule_id, req.day_of_week, req.period_id
        )
        if conflict:
            raise ValueError("يوجد بالفعل حصة في هذا اليوم والفترة")
        
        print("✅ لا يوجد تعارض")
        
        entry = ScheduleEntry(
            schedule_id=schedule_id,
            day_of_week=req.day_of_week,
            period_id=req.period_id,
            subject_id=req.subject_id,
            teacher_id=req.teacher_id,
            room_id=req.room_id,
        )
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        
        print(f"✅ تم إضافة الحصة بنجاح: {entry.id}")
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

    # ============================================================
    # دوال جلب البيانات للقوائم (مع تحميل العلاقات)
    # ============================================================

    async def get_all_sections(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع الشعب كقواميس مع تفاصيل الصف والمرحلة"""
        result = await self.db.execute(
            select(Section)
            .options(
                selectinload(Section.grade).selectinload(Grade.stage)
            )
            .where(Section.school_id == school_id)
            .where(Section.is_active == True)
            .order_by(Section.grade_id, Section.name)
        )
        sections = list(result.scalars().all())
        
        return [
            {
                "id": str(s.id),
                "name": s.name,
                "grade_id": str(s.grade_id) if s.grade_id else None,
                "grade_name": s.grade.name if s.grade else None,
                "stage_name": s.grade.stage.name if s.grade and s.grade.stage else None,
                "display_name": f"{s.grade.stage.name if s.grade and s.grade.stage else ''} - {s.grade.name if s.grade else ''} - {s.name}",
                "capacity": s.capacity,
                "is_active": s.is_active
            }
            for s in sections
        ]

    async def get_sections_objects(self, school_id: str) -> List[Section]:
        """جلب جميع الشعب كـ ORM Objects مع تحميل العلاقات"""
        result = await self.db.execute(
            select(Section)
            .options(
                selectinload(Section.grade).selectinload(Grade.stage)
            )
            .where(Section.school_id == school_id)
            .where(Section.is_active == True)
            .order_by(Section.grade_id, Section.name)
        )
        return list(result.scalars().all())

    async def get_academic_years_objects(self, school_id: str) -> List[AcademicYear]:
        """جلب جميع الأعوام الدراسية"""
        result = await self.db.execute(
            select(AcademicYear)
            .where(AcademicYear.school_id == school_id)
            .where(AcademicYear.is_active == True)
            .order_by(AcademicYear.start_date.desc())
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

    # ============================================================
    # دوال جديدة لصفحة إنشاء الجدول (باستخدام AcademicService)
    # ============================================================

    async def get_sections_for_schedule(self, school_id: str) -> List[Dict[str, Any]]:
        """
        جلب جميع الشعب المتاحة للجدول الدراسي مع تفاصيلها
        
        هذه الدالة تعيد الشعب مع معلومات الصف والمرحلة
        """
        try:
            result = await self.db.execute(
                select(Section)
                .options(
                    selectinload(Section.grade).selectinload(Grade.stage)
                )
                .where(Section.school_id == school_id)
                .where(Section.is_active == True)
                .order_by(Section.grade_id, Section.name)
            )
            sections = list(result.scalars().all())
            
            sections_data = []
            for section in sections:
                grade_name = section.grade.name if section.grade else "غير محدد"
                stage_name = section.grade.stage.name if section.grade and section.grade.stage else "غير محدد"
                
                sections_data.append({
                    "id": str(section.id),
                    "name": section.name,
                    "grade_id": str(section.grade_id) if section.grade_id else None,
                    "grade_name": grade_name,
                    "stage_name": stage_name,
                    "display_name": f"{stage_name} - {grade_name} - {section.name}",
                    "capacity": section.capacity,
                    "is_active": section.is_active
                })
            
            print(f"📚 تم جلب {len(sections_data)} شعبة للمدرسة {school_id}")
            return sections_data
            
        except Exception as e:
            print(f"❌ خطأ في جلب الشعب: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    async def get_academic_years_for_schedule(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب السنوات الدراسية المتاحة للجدول"""
        try:
            result = await self.db.execute(
                select(AcademicYear)
                .where(AcademicYear.school_id == school_id)
                .where(AcademicYear.is_active == True)
                .order_by(AcademicYear.start_date.desc())
            )
            years = list(result.scalars().all())
            
            years_data = []
            for year in years:
                years_data.append({
                    "id": str(year.id),
                    "name": year.name,
                    "start_date": year.start_date,
                    "end_date": year.end_date,
                    "is_current": year.is_current,
                    "is_active": year.is_active
                })
            
            print(f"📅 تم جلب {len(years_data)} سنة دراسية للمدرسة {school_id}")
            return years_data
            
        except Exception as e:
            print(f"❌ خطأ في جلب السنوات الدراسية: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    async def get_subjects_for_schedule(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب المواد المتاحة للجدول"""
        try:
            result = await self.db.execute(
                select(Subject)
                .where(Subject.school_id == school_id)
                .where(Subject.is_active == True)
                .order_by(Subject.name)
            )
            subjects = list(result.scalars().all())
            
            return [
                {
                    "id": str(subject.id),
                    "name": subject.name,
                    "code": subject.code,
                    "color": subject.color
                }
                for subject in subjects
            ]
        except Exception as e:
            print(f"⚠️ خطأ في جلب المواد: {str(e)}")
            return []

    async def get_teachers_for_schedule(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب المعلمين المتاحين للجدول"""
        try:
            role_result = await self.db.execute(
                select(Role).where(Role.key == "teacher", Role.school_id == school_id)
            )
            teacher_role = role_result.scalar_one_or_none()
            
            if not teacher_role:
                print("⚠️ لا يوجد دور معلم في المدرسة")
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
                    "id": str(teacher.id),
                    "name": teacher.full_name or teacher.name,
                    "email": teacher.email
                }
                for teacher in teachers
            ]
        except Exception as e:
            print(f"⚠️ خطأ في جلب المعلمين: {str(e)}")
            return []

    async def get_periods_for_schedule(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب الحصص (الفترات) المتاحة للجدول"""
        try:
            result = await self.db.execute(
                select(Period)
                .where(Period.school_id == school_id)
                .order_by(Period.order)
            )
            periods = list(result.scalars().all())
            
            return [
                {
                    "id": str(period.id),
                    "name": period.name,
                    "order": period.order,
                    "start_time": period.start_time,
                    "end_time": period.end_time
                }
                for period in periods
            ]
        except Exception as e:
            print(f"⚠️ خطأ في جلب الحصص: {str(e)}")
            # إرجاع حصص افتراضية
            return [
                {"id": "1", "name": "الحصة الأولى", "order": 1},
                {"id": "2", "name": "الحصة الثانية", "order": 2},
                {"id": "3", "name": "الحصة الثالثة", "order": 3},
                {"id": "4", "name": "الحصة الرابعة", "order": 4},
                {"id": "5", "name": "الحصة الخامسة", "order": 5},
                {"id": "6", "name": "الحصة السادسة", "order": 6},
            ]

    # ============= دوال تشخيصية =============

    async def check_available_data(self, school_id: str) -> Dict[str, Any]:
        """التحقق من البيانات المتاحة للمدرسة"""
        sections = await self.get_sections_objects(school_id)
        years = await self.get_academic_years_objects(school_id)
        schedules = await self.list_schedules(school_id)
        
        return {
            "school_id": school_id,
            "sections": [
                {
                    "id": s.id, 
                    "name": s.name, 
                    "is_active": s.is_active,
                    "grade": s.grade.name if s.grade else None,
                    "stage": s.grade.stage.name if s.grade and s.grade.stage else None
                }
                for s in sections
            ],
            "academic_years": [
                {"id": y.id, "name": y.name, "is_current": y.is_current}
                for y in years
            ],
            "existing_schedules": [
                {"id": s["id"], "name": s["name"], "section_name": s["section_name"]}
                for s in schedules
            ],
            "counts": {
                "sections": len(sections),
                "academic_years": len(years),
                "schedules": len(schedules)
            }
        }
