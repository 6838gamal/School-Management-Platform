"""Schedule service."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

from app.core.exceptions import NotFoundException, ValidationException
from app.models.academics import Section, Period, Subject, Room, AcademicYear, Grade, Stage
from app.models.schedules import Schedule, ScheduleEntry
from app.models.teachers import Teacher
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

    async def find_teacher_by_id(self, teacher_id: str) -> Optional[Teacher]:
        """البحث عن معلم بالمعرف"""
        result = await self.db.execute(
            select(Teacher).where(Teacher.id == teacher_id)
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
        """البحث عن جدول مكرر"""
        result = await self.db.execute(
            select(Schedule)
            .where(
                Schedule.school_id == school_id,
                Schedule.section_id == section_id,
                Schedule.year_id == academic_year_id,
                Schedule.is_active == True
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
                ScheduleEntry.day == day_of_week,
                ScheduleEntry.period == period_id,
                ScheduleEntry.is_active == True
            )
        )
        return result.scalar_one_or_none()

    # ============= دوال مساعدة لجلب الأسماء =============

    async def get_section_details(self, section_id: str) -> Dict[str, Any]:
        """جلب تفاصيل الشعبة مع الصف والمرحلة"""
        section = await self.find_section_by_id(section_id)
        if not section:
            return {"name": None, "grade_name": None, "stage_name": None}
        
        return {
            "name": section.name,
            "grade_name": section.grade.name if section.grade else None,
            "stage_name": section.grade.stage.name if section.grade and section.grade.stage else None,
            "grade_id": str(section.grade_id) if section.grade_id else None,
            "stage_id": str(section.grade.stage_id) if section.grade and section.grade.stage else None,
        }

    async def get_academic_year_name(self, year_id: str) -> Optional[str]:
        """جلب اسم العام الدراسي"""
        year = await self.find_academic_year_by_id(year_id)
        return year.name if year else None

    async def get_subject_name(self, subject_id: str) -> Optional[str]:
        """جلب اسم المادة"""
        subject = await self.find_subject_by_id(subject_id)
        return subject.name if subject else None

    async def get_teacher_name(self, teacher_id: str) -> Optional[str]:
        """جلب اسم المعلم"""
        teacher = await self.find_teacher_by_id(teacher_id)
        if teacher:
            return f"{teacher.first_name} {teacher.last_name}".strip() or teacher.full_name
        return None

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
        """جلب جميع الجداول مع الأسماء والتفاصيل الكاملة"""
        try:
            result = await self.db.execute(
                select(Schedule)
                .where(Schedule.school_id == school_id)
                .order_by(Schedule.created_at.desc())
                .options(
                    selectinload(Schedule.section),
                    selectinload(Schedule.grade),
                    selectinload(Schedule.stage),
                    selectinload(Schedule.year)
                )
            )
            schedules = list(result.scalars().all())
            
            if not schedules:
                print(f"📊 لا توجد جداول للمدرسة {school_id}")
                return []
            
            result_list = []
            for schedule in schedules:
                # جلب تفاصيل الشعبة
                section_details = await self.get_section_details(schedule.section_id)
                
                # جلب اسم العام الدراسي
                year_name = await self.get_academic_year_name(schedule.year_id)
                
                # حساب عدد الحصص
                entries_count_result = await self.db.execute(
                    select(func.count(ScheduleEntry.id))
                    .where(
                        ScheduleEntry.schedule_id == schedule.id,
                        ScheduleEntry.is_active == True
                    )
                )
                entries_count = entries_count_result.scalar() or 0
                
                result_list.append({
                    "id": str(schedule.id),
                    "name": schedule.name,
                    "school_id": str(schedule.school_id),
                    "section_id": str(schedule.section_id) if schedule.section_id else None,
                    "section_name": section_details.get("name"),
                    "grade_id": str(schedule.grade_id) if schedule.grade_id else section_details.get("grade_id"),
                    "grade_name": section_details.get("grade_name"),
                    "stage_id": str(schedule.stage_id) if schedule.stage_id else section_details.get("stage_id"),
                    "stage_name": section_details.get("stage_name"),
                    "year_id": str(schedule.year_id) if schedule.year_id else None,
                    "year_name": year_name,
                    "academic_year_name": year_name,  # للتوافق مع القالب
                    "academic_year_id": str(schedule.year_id) if schedule.year_id else None,
                    "is_active": schedule.is_active,
                    "created_at": schedule.created_at,
                    "updated_at": schedule.updated_at,
                    "entries_count": entries_count,
                })
            
            print(f"📊 تم جلب {len(result_list)} جدول للمدرسة {school_id}")
            return result_list
            
        except Exception as e:
            print(f"❌ Error in list_schedules: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    async def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """جلب جدول بواسطة المعرف مع الأسماء"""
        try:
            result = await self.db.execute(
                select(Schedule)
                .where(Schedule.id == schedule_id)
                .options(
                    selectinload(Schedule.section),
                    selectinload(Schedule.grade),
                    selectinload(Schedule.stage),
                    selectinload(Schedule.year)
                )
            )
            schedule = result.scalar_one_or_none()
            if not schedule:
                return None
            
            section_details = await self.get_section_details(schedule.section_id)
            year_name = await self.get_academic_year_name(schedule.year_id)
            
            return {
                "id": str(schedule.id),
                "name": schedule.name,
                "school_id": str(schedule.school_id),
                "section_id": str(schedule.section_id) if schedule.section_id else None,
                "section_name": section_details.get("name"),
                "grade_id": str(schedule.grade_id) if schedule.grade_id else section_details.get("grade_id"),
                "grade_name": section_details.get("grade_name"),
                "stage_id": str(schedule.stage_id) if schedule.stage_id else section_details.get("stage_id"),
                "stage_name": section_details.get("stage_name"),
                "year_id": str(schedule.year_id) if schedule.year_id else None,
                "year_name": year_name,
                "academic_year_name": year_name,
                "academic_year_id": str(schedule.year_id) if schedule.year_id else None,
                "is_active": schedule.is_active,
                "created_at": schedule.created_at,
                "updated_at": schedule.updated_at
            }
        except Exception as e:
            print(f"❌ Error in get_schedule: {str(e)}")
            return None

    async def get_schedule_with_entries(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """جلب جدول مع جميع مدخلاته"""
        try:
            schedule_data = await self.get_schedule(schedule_id)
            if not schedule_data:
                return None
            
            entries_result = await self.db.execute(
                select(ScheduleEntry)
                .where(
                    ScheduleEntry.schedule_id == schedule_id,
                    ScheduleEntry.is_active == True
                )
                .order_by(ScheduleEntry.day, ScheduleEntry.period)
            )
            entries = list(entries_result.scalars().all())
            
            entries_with_names = []
            for entry in entries:
                subject_name = await self.get_subject_name(entry.subject_id)
                teacher_name = await self.get_teacher_name(entry.teacher_id)
                room_name = await self.get_room_name(entry.room_id)
                period_name = await self.get_period_name(entry.period_id)
                
                entries_with_names.append({
                    "id": str(entry.id),
                    "day": entry.day,
                    "day_of_week": entry.day,
                    "period": entry.period,
                    "period_id": str(entry.period_id) if entry.period_id else None,
                    "period_name": period_name,
                    "subject_id": str(entry.subject_id) if entry.subject_id else None,
                    "subject_name": subject_name,
                    "teacher_id": str(entry.teacher_id) if entry.teacher_id else None,
                    "teacher_name": teacher_name,
                    "room_id": str(entry.room_id) if entry.room_id else None,
                    "room_name": room_name,
                    "is_active": entry.is_active,
                })
            
            schedule_data["entries"] = entries_with_names
            schedule_data["entries_count"] = len(entries_with_names)
            
            return schedule_data
            
        except Exception as e:
            print(f"❌ Error in get_schedule_with_entries: {str(e)}")
            return None

    async def create_schedule(self, school_id: str, req: ScheduleCreate) -> Schedule:
        """إنشاء جدول جديد"""
        try:
            print("=" * 50)
            print("📝 إنشاء جدول جديد:")
            print(f"   school_id: {school_id}")
            print(f"   name: {req.name}")
            print(f"   section_id: {req.section_id}")
            print(f"   year_id: {req.year_id}")
            print(f"   is_active: {req.is_active}")
            print(f"   entries_count: {len(req.entries)}")
            print("=" * 50)
            
            if not school_id:
                raise ValidationException("معرف المدرسة غير موجود")
            
            if not req.section_id:
                raise ValidationException("معرف الشعبة مطلوب")
            
            # التحقق من وجود الشعبة
            section = await self.find_section_by_id(req.section_id)
            if not section:
                raise ValidationException(f"الشعبة غير موجودة: {req.section_id}")
            
            print(f"✅ تم العثور على الشعبة: {section.name}")
            
            # التحقق من وجود العام الدراسي
            if not req.year_id:
                raise ValidationException("معرف العام الدراسي مطلوب")
            
            year = await self.find_academic_year_by_id(req.year_id)
            if not year:
                raise ValidationException(f"العام الدراسي غير موجود: {req.year_id}")
            
            print(f"✅ تم العثور على العام الدراسي: {year.name}")
            
            # التحقق من عدم وجود جدول مكرر
            duplicate = await self.find_schedule_duplicate(
                school_id, req.section_id, req.year_id
            )
            if duplicate:
                raise ValidationException("يوجد بالفعل جدول نشط لهذه الشعبة في هذا العام الدراسي")
            
            print("✅ لا يوجد جدول مكرر")
            
            # إنشاء الجدول
            schedule = Schedule(
                id=str(uuid.uuid4()),
                school_id=school_id,
                name=req.name,
                section_id=req.section_id,
                year_id=req.year_id,
                grade_id=section.grade_id if section.grade_id else req.grade_id,
                stage_id=section.grade.stage_id if section.grade and section.grade.stage_id else req.stage_id,
                is_active=req.is_active,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.db.add(schedule)
            await self.db.flush()
            
            # إضافة الحصص
            for entry_data in req.entries:
                # التحقق من وجود المادة
                subject = await self.find_subject_by_id(entry_data.subject_id)
                if not subject:
                    raise ValidationException(f"المادة غير موجودة: {entry_data.subject_id}")
                
                # التحقق من وجود المعلم (إذا تم تحديده)
                if entry_data.teacher_id:
                    teacher = await self.find_teacher_by_id(entry_data.teacher_id)
                    if not teacher:
                        raise ValidationException(f"المعلم غير موجود: {entry_data.teacher_id}")
                
                # التحقق من عدم وجود تعارض
                conflict = await self.find_entry_conflict(
                    schedule.id, entry_data.day, entry_data.period
                )
                if conflict:
                    raise ValidationException(f"يوجد بالفعل حصة في اليوم {entry_data.day} والفترة {entry_data.period}")
                
                entry = ScheduleEntry(
                    id=str(uuid.uuid4()),
                    schedule_id=schedule.id,
                    day=entry_data.day,
                    period=entry_data.period,
                    subject_id=entry_data.subject_id,
                    teacher_id=entry_data.teacher_id,
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                self.db.add(entry)
            
            await self.db.flush()
            await self.db.refresh(schedule)
            
            print(f"✅ تم إنشاء الجدول بنجاح: {schedule.id}")
            return schedule
            
        except ValidationException:
            raise
        except Exception as e:
            print(f"❌ Error in create_schedule: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    async def update_schedule(self, schedule_id: str, req: ScheduleUpdate) -> Schedule:
        """تحديث جدول"""
        try:
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
            
            schedule.updated_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(schedule)
            return schedule
            
        except NotFoundException:
            raise
        except Exception as e:
            print(f"❌ Error in update_schedule: {str(e)}")
            raise

    async def delete_schedule(self, schedule_id: str) -> bool:
        """حذف جدول (تعطيل فقط)"""
        try:
            result = await self.db.execute(
                select(Schedule).where(Schedule.id == schedule_id)
            )
            schedule = result.scalar_one_or_none()
            if not schedule:
                raise NotFoundException("الجدول غير موجود")
            
            # تعطيل الجدول بدلاً من حذفه
            schedule.is_active = False
            schedule.updated_at = datetime.utcnow()
            
            # تعطيل الحصص أيضاً
            entries_result = await self.db.execute(
                select(ScheduleEntry).where(ScheduleEntry.schedule_id == schedule_id)
            )
            entries = list(entries_result.scalars().all())
            for entry in entries:
                entry.is_active = False
                entry.updated_at = datetime.utcnow()
            
            await self.db.flush()
            return True
            
        except NotFoundException:
            raise
        except Exception as e:
            print(f"❌ Error in delete_schedule: {str(e)}")
            raise

    # ============= مدخلات الجدول (الحصص) =============

    async def add_entry(self, schedule_id: str, req: ScheduleEntryCreate) -> ScheduleEntry:
        """إضافة مدخل (حصة) إلى الجدول"""
        try:
            print("=" * 50)
            print("📝 إضافة حصة جديدة:")
            print(f"   schedule_id: {schedule_id}")
            print(f"   day: {req.day}")
            print(f"   period: {req.period}")
            print(f"   subject_id: {req.subject_id}")
            print(f"   teacher_id: {req.teacher_id}")
            print("=" * 50)
            
            # التحقق من وجود الجدول
            schedule_result = await self.db.execute(
                select(Schedule).where(Schedule.id == schedule_id)
            )
            schedule = schedule_result.scalar_one_or_none()
            if not schedule:
                raise NotFoundException("الجدول غير موجود")
            
            # التحقق من وجود المادة
            subject = await self.find_subject_by_id(req.subject_id)
            if not subject:
                raise ValidationException(f"المادة غير موجودة: {req.subject_id}")
            print(f"✅ تم العثور على المادة: {subject.name}")
            
            # التحقق من وجود المعلم
            if req.teacher_id:
                teacher = await self.find_teacher_by_id(req.teacher_id)
                if not teacher:
                    raise ValidationException(f"المعلم غير موجود: {req.teacher_id}")
                print(f"✅ تم العثور على المعلم: {teacher.first_name} {teacher.last_name}")
            
            # التحقق من عدم وجود تعارض
            conflict = await self.find_entry_conflict(
                schedule_id, req.day, req.period
            )
            if conflict:
                raise ValidationException("يوجد بالفعل حصة في هذا اليوم والفترة")
            
            print("✅ لا يوجد تعارض")
            
            # إنشاء الحصة
            entry = ScheduleEntry(
                id=str(uuid.uuid4()),
                schedule_id=schedule_id,
                day=req.day,
                period=req.period,
                subject_id=req.subject_id,
                teacher_id=req.teacher_id,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.db.add(entry)
            await self.db.flush()
            await self.db.refresh(entry)
            
            print(f"✅ تم إضافة الحصة بنجاح: {entry.id}")
            return entry
            
        except NotFoundException:
            raise
        except ValidationException:
            raise
        except Exception as e:
            print(f"❌ Error in add_entry: {str(e)}")
            raise

    async def update_entry(self, entry_id: str, req: ScheduleEntryUpdate) -> ScheduleEntry:
        """تحديث مدخل (حصة) في الجدول"""
        try:
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
            
            entry.updated_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(entry)
            return entry
            
        except NotFoundException:
            raise
        except Exception as e:
            print(f"❌ Error in update_entry: {str(e)}")
            raise

    async def delete_entry(self, entry_id: str) -> bool:
        """حذف مدخل (حصة) من الجدول (تعطيل فقط)"""
        try:
            result = await self.db.execute(
                select(ScheduleEntry).where(ScheduleEntry.id == entry_id)
            )
            entry = result.scalar_one_or_none()
            if not entry:
                raise NotFoundException("المدخل غير موجود")
            
            entry.is_active = False
            entry.updated_at = datetime.utcnow()
            await self.db.flush()
            return True
            
        except NotFoundException:
            raise
        except Exception as e:
            print(f"❌ Error in delete_entry: {str(e)}")
            raise

    # ============================================================
    # دوال جلب البيانات للقوائم
    # ============================================================

    async def get_all_sections(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع الشعب كقواميس مع تفاصيل الصف والمرحلة"""
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
        except Exception as e:
            print(f"❌ Error in get_all_sections: {str(e)}")
            return []

    async def get_sections_objects(self, school_id: str) -> List[Section]:
        """جلب جميع الشعب كـ ORM Objects"""
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
            return list(result.scalars().all())
        except Exception as e:
            print(f"❌ Error in get_sections_objects: {str(e)}")
            return []

    async def get_academic_years_objects(self, school_id: str) -> List[AcademicYear]:
        """جلب جميع الأعوام الدراسية"""
        try:
            result = await self.db.execute(
                select(AcademicYear)
                .where(AcademicYear.school_id == school_id)
                .where(AcademicYear.is_active == True)
                .order_by(AcademicYear.start_date.desc())
            )
            return list(result.scalars().all())
        except Exception as e:
            print(f"❌ Error in get_academic_years_objects: {str(e)}")
            return []

    async def get_periods(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع الفترات"""
        try:
            result = await self.db.execute(
                select(Period)
                .where(Period.school_id == school_id)
                .order_by(Period.order)
            )
            periods = list(result.scalars().all())
            return [
                {"id": str(p.id), "name": p.name, "order": p.order, 
                 "start_time": p.start_time, "end_time": p.end_time}
                for p in periods
            ]
        except Exception as e:
            print(f"❌ Error in get_periods: {str(e)}")
            return []

    async def get_subjects(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع المواد"""
        try:
            result = await self.db.execute(
                select(Subject)
                .where(Subject.school_id == school_id)
                .where(Subject.is_active == True)
                .order_by(Subject.name)
            )
            subjects = list(result.scalars().all())
            return [{"id": str(s.id), "name": s.name, "code": s.code} for s in subjects]
        except Exception as e:
            print(f"❌ Error in get_subjects: {str(e)}")
            return []

    async def get_teachers(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع المعلمين"""
        try:
            # جلب دور المعلم
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
            
            return [
                {
                    "id": str(t.id),
                    "full_name": t.full_name,
                    "email": t.email
                }
                for t in teachers
            ]
        except Exception as e:
            print(f"❌ Error in get_teachers: {str(e)}")
            return []

    async def get_rooms(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع القاعات"""
        try:
            result = await self.db.execute(
                select(Room)
                .where(Room.school_id == school_id)
                .where(Room.is_active == True)
                .order_by(Room.name)
            )
            rooms = list(result.scalars().all())
            return [{"id": str(r.id), "name": r.name} for r in rooms]
        except Exception as e:
            print(f"❌ Error in get_rooms: {str(e)}")
            return []

    # ============================================================
    # دوال تشخيصية
    # ============================================================

    async def check_available_data(self, school_id: str) -> Dict[str, Any]:
        """التحقق من البيانات المتاحة للمدرسة"""
        try:
            sections = await self.get_sections_objects(school_id)
            years = await self.get_academic_years_objects(school_id)
            schedules = await self.list_schedules(school_id)
            
            return {
                "school_id": school_id,
                "sections": [
                    {
                        "id": str(s.id), 
                        "name": s.name, 
                        "is_active": s.is_active,
                        "grade": s.grade.name if s.grade else None,
                        "stage": s.grade.stage.name if s.grade and s.grade.stage else None
                    }
                    for s in sections
                ],
                "academic_years": [
                    {"id": str(y.id), "name": y.name, "is_current": y.is_current}
                    for y in years
                ],
                "existing_schedules": schedules,
                "counts": {
                    "sections": len(sections),
                    "academic_years": len(years),
                    "schedules": len(schedules)
                }
            }
        except Exception as e:
            print(f"❌ Error in check_available_data: {str(e)}")
            return {"error": str(e)}
