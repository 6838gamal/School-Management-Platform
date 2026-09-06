"""Schedule service with full academic hierarchy support - Manual queries only."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, text, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import json
import traceback

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

    # ============================================================
    # 1️⃣ دوال مساعدة للبحث والتحقق (Finders - بدون علاقات)
    # ============================================================

    async def find_section_by_id(self, section_id: str) -> Optional[Section]:
        """البحث عن شعبة بالمعرف - بدون استخدام العلاقات"""
        try:
            result = await self.db.execute(
                select(Section).where(Section.id == section_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"⚠️ Error in find_section_by_id: {str(e)}")
            return None

    async def find_academic_year_by_id(self, year_id: str) -> Optional[AcademicYear]:
        """البحث عن عام دراسي بالمعرف"""
        try:
            result = await self.db.execute(
                select(AcademicYear).where(AcademicYear.id == year_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"⚠️ Error in find_academic_year_by_id: {str(e)}")
            return None

    async def find_subject_by_id(self, subject_id: str) -> Optional[Subject]:
        """البحث عن مادة بالمعرف"""
        try:
            result = await self.db.execute(
                select(Subject).where(Subject.id == subject_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"⚠️ Error in find_subject_by_id: {str(e)}")
            return None

    async def find_teacher_by_id(self, teacher_id: str) -> Optional[Teacher]:
        """البحث عن معلم بالمعرف"""
        try:
            result = await self.db.execute(
                select(Teacher).where(Teacher.id == teacher_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"⚠️ Error in find_teacher_by_id: {str(e)}")
            return None

    async def find_room_by_id(self, room_id: str) -> Optional[Room]:
        """البحث عن قاعة بالمعرف"""
        try:
            result = await self.db.execute(
                select(Room).where(Room.id == room_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"⚠️ Error in find_room_by_id: {str(e)}")
            return None

    async def find_period_by_id(self, period_id: str) -> Optional[Period]:
        """البحث عن فترة بالمعرف"""
        try:
            result = await self.db.execute(
                select(Period).where(Period.id == period_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"⚠️ Error in find_period_by_id: {str(e)}")
            return None

    async def find_schedule_duplicate(
        self, 
        school_id: str, 
        section_id: str, 
        academic_year_id: str
    ) -> Optional[Schedule]:
        """البحث عن جدول مكرر"""
        try:
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
        except Exception as e:
            print(f"⚠️ Error in find_schedule_duplicate: {str(e)}")
            return None

    async def find_entry_conflict(
        self,
        schedule_id: str,
        day: int,
        period: int
    ) -> Optional[ScheduleEntry]:
        """البحث عن تعارض في الحصص (نفس اليوم والفترة)"""
        try:
            result = await self.db.execute(
                select(ScheduleEntry)
                .where(
                    ScheduleEntry.schedule_id == schedule_id,
                    ScheduleEntry.day_of_week == day,
                    ScheduleEntry.period_id == period
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"⚠️ Error in find_entry_conflict: {str(e)}")
            return None

    # ============================================================
    # 2️⃣ دوال مساعدة لجلب الأسماء والتفاصيل (بحث يدوي)
    # ============================================================

    async def get_grade_by_id(self, grade_id: str) -> Optional[Grade]:
        """جلب الصف بالمعرف"""
        try:
            if not grade_id:
                return None
            result = await self.db.execute(
                select(Grade).where(Grade.id == grade_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"⚠️ Error in get_grade_by_id: {str(e)}")
            return None

    async def get_stage_by_id(self, stage_id: str) -> Optional[Stage]:
        """جلب المرحلة بالمعرف"""
        try:
            if not stage_id:
                return None
            result = await self.db.execute(
                select(Stage).where(Stage.id == stage_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"⚠️ Error in get_stage_by_id: {str(e)}")
            return None

    async def get_section_details(self, section_id: str) -> Dict[str, Any]:
        """جلب تفاصيل الشعبة مع الصف والمرحلة والسنة - بحث يدوي"""
        try:
            if not section_id:
                return {
                    "name": None, 
                    "grade_name": None, 
                    "stage_name": None, 
                    "grade_id": None, 
                    "stage_id": None,
                    "year_id": None,
                    "year_name": None,
                    "display_name": None
                }
            
            # 1. جلب الشعبة
            section = await self.find_section_by_id(section_id)
            if not section:
                return {
                    "name": None, 
                    "grade_name": None, 
                    "stage_name": None, 
                    "grade_id": None, 
                    "stage_id": None,
                    "year_id": None,
                    "year_name": None,
                    "display_name": None
                }
            
            # 2. جلب الصف يدوياً
            grade = None
            grade_name = None
            stage_id = None
            stage_name = None
            year_id = None
            year_name = None
            
            if section.grade_id:
                grade = await self.get_grade_by_id(section.grade_id)
                if grade:
                    grade_name = grade.name
                    year_id = grade.year_id
                    
                    # 3. جلب المرحلة يدوياً
                    if grade.stage_id:
                        stage = await self.get_stage_by_id(grade.stage_id)
                        if stage:
                            stage_id = stage.id
                            stage_name = stage.name
                    
                    # 4. جلب السنة يدوياً
                    if year_id:
                        year = await self.find_academic_year_by_id(year_id)
                        if year:
                            year_name = year.name
            
            return {
                "name": section.name,
                "grade_name": grade_name,
                "stage_name": stage_name,
                "grade_id": str(section.grade_id) if section.grade_id else None,
                "stage_id": str(stage_id) if stage_id else None,
                "year_id": str(year_id) if year_id else None,
                "year_name": year_name,
                "display_name": f"{stage_name if stage_name else ''} - {grade_name if grade_name else ''} - {section.name}".strip(" - ")
            }
        except Exception as e:
            print(f"⚠️ Error in get_section_details: {str(e)}")
            traceback.print_exc()
            return {
                "name": None, 
                "grade_name": None, 
                "stage_name": None, 
                "grade_id": None, 
                "stage_id": None,
                "year_id": None,
                "year_name": None,
                "display_name": None
            }

    async def get_academic_year_name(self, year_id: str) -> Optional[str]:
        """جلب اسم العام الدراسي"""
        try:
            if not year_id:
                return None
            year = await self.find_academic_year_by_id(year_id)
            return year.name if year else None
        except Exception as e:
            print(f"⚠️ Error in get_academic_year_name: {str(e)}")
            return None

    async def get_subject_name(self, subject_id: str) -> Optional[str]:
        """جلب اسم المادة"""
        try:
            if not subject_id:
                return None
            subject = await self.find_subject_by_id(subject_id)
            return subject.name if subject else None
        except Exception as e:
            print(f"⚠️ Error in get_subject_name: {str(e)}")
            return None

    async def get_teacher_name(self, teacher_id: str) -> Optional[str]:
        """جلب اسم المعلم"""
        try:
            if not teacher_id:
                return None
            teacher = await self.find_teacher_by_id(teacher_id)
            if teacher:
                return f"{teacher.first_name} {teacher.last_name}".strip() or teacher.full_name
            return None
        except Exception as e:
            print(f"⚠️ Error in get_teacher_name: {str(e)}")
            return None

    async def get_room_name(self, room_id: str) -> Optional[str]:
        """جلب اسم القاعة"""
        try:
            if not room_id:
                return None
            room = await self.find_room_by_id(room_id)
            return room.name if room else None
        except Exception as e:
            print(f"⚠️ Error in get_room_name: {str(e)}")
            return None

    async def get_period_name(self, period_id: str) -> Optional[str]:
        """جلب اسم الفترة"""
        try:
            if not period_id:
                return None
            period = await self.find_period_by_id(period_id)
            return period.name if period else None
        except Exception as e:
            print(f"⚠️ Error in get_period_name: {str(e)}")
            return None

    # ============================================================
    # 3️⃣ دوال التصفية المتدرجة (Hierarchy - بحث يدوي)
    # ============================================================

    async def get_academic_years(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب السنوات الدراسية النشطة للمدرسة"""
        try:
            result = await self.db.execute(
                select(AcademicYear)
                .where(
                    AcademicYear.school_id == school_id,
                    AcademicYear.is_active == True
                )
                .order_by(AcademicYear.start_date.desc())
            )
            years = result.scalars().all()
            
            return [
                {
                    "id": str(year.id),
                    "name": year.name,
                    "start_date": year.start_date,
                    "end_date": year.end_date,
                    "is_current": year.is_current,
                    "is_active": year.is_active
                }
                for year in years
            ]
        except Exception as e:
            print(f"⚠️ Error in get_academic_years: {str(e)}")
            return []

    async def get_stages_by_year(
        self, 
        school_id: str, 
        year_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """جلب المراحل حسب السنة الدراسية - بحث يدوي"""
        try:
            stmt = select(Stage).where(
                Stage.school_id == school_id,
                Stage.is_active == True
            )
            if year_id:
                stmt = stmt.where(Stage.year_id == year_id)
            stmt = stmt.order_by(Stage.order)
            
            result = await self.db.execute(stmt)
            stages = result.scalars().all()
            
            return [
                {
                    "id": str(stage.id),
                    "name": stage.name,
                    "name_en": stage.name_en,
                    "year_id": str(stage.year_id) if stage.year_id else None,
                    "order": stage.order,
                    "is_active": getattr(stage, 'is_active', True)
                }
                for stage in stages
            ]
        except Exception as e:
            print(f"⚠️ Error in get_stages_by_year: {str(e)}")
            return []

    async def get_grades_by_stage(
        self, 
        school_id: str, 
        stage_id: Optional[str] = None,
        year_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """جلب الصفوف حسب المرحلة - بحث يدوي"""
        try:
            stmt = select(Grade).where(
                Grade.school_id == school_id,
                Grade.is_active == True
            )
            if stage_id:
                stmt = stmt.where(Grade.stage_id == stage_id)
            if year_id:
                stmt = stmt.where(Grade.year_id == year_id)
            stmt = stmt.order_by(Grade.order)
            
            result = await self.db.execute(stmt)
            grades = result.scalars().all()
            
            return [
                {
                    "id": str(grade.id),
                    "name": grade.name,
                    "name_en": grade.name_en,
                    "stage_id": str(grade.stage_id) if grade.stage_id else None,
                    "year_id": str(grade.year_id) if grade.year_id else None,
                    "order": grade.order,
                    "is_active": grade.is_active
                }
                for grade in grades
            ]
        except Exception as e:
            print(f"⚠️ Error in get_grades_by_stage: {str(e)}")
            return []

    async def get_sections_by_grade(
        self, 
        school_id: str, 
        grade_id: Optional[str] = None,
        year_id: Optional[str] = None,
        stage_id: Optional[str] = None,
        include_all: bool = False
    ) -> List[Dict[str, Any]]:
        """جلب الشعب حسب الصف - بحث يدوي بدون علاقات"""
        try:
            stmt = select(Section).where(
                Section.school_id == school_id,
                Section.is_active == True
            )
            
            if grade_id:
                stmt = stmt.where(Section.grade_id == grade_id)
            elif year_id and stage_id and not include_all:
                # جلب الصفوف في السنة والمرحلة المحددة
                grades_result = await self.db.execute(
                    select(Grade.id).where(
                        Grade.school_id == school_id,
                        Grade.year_id == year_id,
                        Grade.stage_id == stage_id,
                        Grade.is_active == True
                    )
                )
                grade_ids = [row[0] for row in grades_result.all()]
                if grade_ids:
                    stmt = stmt.where(Section.grade_id.in_(grade_ids))
                else:
                    return []
            elif year_id and not include_all:
                grades_result = await self.db.execute(
                    select(Grade.id).where(
                        Grade.school_id == school_id,
                        Grade.year_id == year_id,
                        Grade.is_active == True
                    )
                )
                grade_ids = [row[0] for row in grades_result.all()]
                if grade_ids:
                    stmt = stmt.where(Section.grade_id.in_(grade_ids))
                else:
                    return []
            elif stage_id and not include_all:
                grades_result = await self.db.execute(
                    select(Grade.id).where(
                        Grade.school_id == school_id,
                        Grade.stage_id == stage_id,
                        Grade.is_active == True
                    )
                )
                grade_ids = [row[0] for row in grades_result.all()]
                if grade_ids:
                    stmt = stmt.where(Section.grade_id.in_(grade_ids))
                else:
                    return []
            
            stmt = stmt.order_by(Section.grade_id, Section.name)
            
            result = await self.db.execute(stmt)
            sections = result.scalars().all()
            
            # جلب تفاصيل إضافية لكل شعبة - يدوياً
            sections_data = []
            for section in sections:
                # جلب الصف
                grade_name = None
                stage_name = None
                year_name = None
                grade_stage_id = None
                grade_year_id = None
                
                if section.grade_id:
                    grade = await self.get_grade_by_id(section.grade_id)
                    if grade:
                        grade_name = grade.name
                        grade_year_id = grade.year_id
                        grade_stage_id = grade.stage_id
                        
                        # جلب المرحلة
                        if grade.stage_id:
                            stage = await self.get_stage_by_id(grade.stage_id)
                            if stage:
                                stage_name = stage.name
                        
                        # جلب السنة
                        if grade.year_id:
                            year = await self.find_academic_year_by_id(grade.year_id)
                            if year:
                                year_name = year.name
                
                sections_data.append({
                    "id": str(section.id),
                    "name": section.name,
                    "grade_id": str(section.grade_id) if section.grade_id else None,
                    "grade_name": grade_name,
                    "stage_id": str(grade_stage_id) if grade_stage_id else None,
                    "stage_name": stage_name,
                    "year_id": str(grade_year_id) if grade_year_id else None,
                    "year_name": year_name,
                    "capacity": section.capacity,
                    "is_active": section.is_active,
                    "display_name": f"{stage_name if stage_name else ''} - {grade_name if grade_name else ''} - {section.name}".strip(" - ")
                })
            
            return sections_data
        except Exception as e:
            print(f"⚠️ Error in get_sections_by_grade: {str(e)}")
            traceback.print_exc()
            return []

    async def get_full_hierarchy(
        self,
        school_id: str,
        year_id: Optional[str] = None,
        stage_id: Optional[str] = None,
        grade_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """جلب التسلسل الهرمي الكامل - بحث يدوي"""
        try:
            years = await self.get_academic_years(school_id)
            stages = await self.get_stages_by_year(school_id, year_id)
            grades = await self.get_grades_by_stage(school_id, stage_id, year_id)
            sections = await self.get_sections_by_grade(
                school_id, grade_id, year_id, stage_id
            )
            
            return {
                "years": years,
                "stages": stages,
                "grades": grades,
                "sections": sections,
                "selected_year": year_id,
                "selected_stage": stage_id,
                "selected_grade": grade_id,
            }
        except Exception as e:
            print(f"⚠️ Error in get_full_hierarchy: {str(e)}")
            traceback.print_exc()
            return {"years": [], "stages": [], "grades": [], "sections": []}

    # ============================================================
    # 4️⃣ دوال جلب القوائم (للنماذج - بحث يدوي)
    # ============================================================

    async def get_all_sections(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع الشعب كقواميس مع تفاصيل الصف والمرحلة"""
        try:
            return await self.get_sections_by_grade(school_id, include_all=True)
        except Exception as e:
            print(f"❌ Error in get_all_sections: {str(e)}")
            return []

    async def get_sections_objects(self, school_id: str) -> List[Section]:
        """جلب جميع الشعب كـ ORM Objects"""
        try:
            result = await self.db.execute(
                select(Section)
                .where(Section.school_id == school_id)
                .where(Section.is_active == True)
                .order_by(Section.grade_id, Section.name)
            )
            return list(result.scalars().all())
        except Exception as e:
            print(f"❌ Error in get_sections_objects: {str(e)}")
            return []

    async def get_academic_years_objects(self, school_id: str) -> List[AcademicYear]:
        """جلب جميع الأعوام الدراسية كـ ORM Objects"""
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

    async def get_all_periods(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع الفترات"""
        try:
            result = await self.db.execute(
                select(Period)
                .where(Period.school_id == school_id)
                .order_by(Period.order)
            )
            periods = list(result.scalars().all())
            return [
                {
                    "id": str(p.id), 
                    "name": p.name, 
                    "order": p.order, 
                    "start_time": p.start_time, 
                    "end_time": p.end_time,
                    "is_break": p.is_break,
                    "is_active": getattr(p, 'is_active', True)
                }
                for p in periods
            ]
        except Exception as e:
            print(f"❌ Error in get_all_periods: {str(e)}")
            return []

    async def get_all_subjects(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع المواد"""
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
                    "id": str(s.id), 
                    "name": s.name, 
                    "name_en": s.name_en,
                    "code": s.code,
                    "color": s.color,
                    "is_active": s.is_active
                }
                for s in subjects
            ]
        except Exception as e:
            print(f"❌ Error in get_all_subjects: {str(e)}")
            return []

    async def get_all_teachers(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع المعلمين"""
        try:
            result = await self.db.execute(
                select(Teacher)
                .where(Teacher.school_id == school_id)
                .where(Teacher.is_active == True)
                .order_by(Teacher.first_name, Teacher.last_name)
            )
            teachers = list(result.scalars().all())
            
            return [
                {
                    "id": str(t.id),
                    "full_name": f"{t.first_name} {t.last_name}".strip() or t.full_name,
                    "first_name": t.first_name,
                    "last_name": t.last_name,
                    "employee_number": t.employee_number,
                    "email": t.email,
                    "phone": getattr(t, 'phone', None),
                    "specialization": t.specialization,
                    "is_active": t.is_active
                }
                for t in teachers
            ]
        except Exception as e:
            print(f"❌ Error in get_all_teachers: {str(e)}")
            return []

    async def get_all_rooms(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع القاعات"""
        try:
            result = await self.db.execute(
                select(Room)
                .where(Room.school_id == school_id)
                .where(Room.is_active == True)
                .order_by(Room.name)
            )
            rooms = list(result.scalars().all())
            return [
                {
                    "id": str(r.id), 
                    "name": r.name,
                    "building": r.building,
                    "floor": r.floor,
                    "capacity": r.capacity,
                    "is_active": r.is_active
                }
                for r in rooms
            ]
        except Exception as e:
            print(f"❌ Error in get_all_rooms: {str(e)}")
            return []

    # ============================================================
    # 5️⃣ دوال الجداول (CRUD)
    # ============================================================

    async def list_schedules(self, school_id: str) -> List[Dict[str, Any]]:
        """جلب جميع الجداول مع الأسماء والتفاصيل الكاملة - بحث يدوي"""
        try:
            print("=" * 60)
            print("📊 جلب قائمة الجداول للمدرسة:", school_id)
            print("=" * 60)
            
            result = await self.db.execute(
                select(Schedule)
                .where(Schedule.school_id == school_id)
                .order_by(Schedule.created_at.desc())
            )
            schedules = list(result.scalars().all())
            
            if not schedules:
                print("📊 لا توجد جداول للمدرسة", school_id)
                return []
            
            print(f"📊 تم العثور على {len(schedules)} جدول")
            
            result_list = []
            for idx, schedule in enumerate(schedules, 1):
                print(f"\n📋 الجدول #{idx}:")
                print(f"   🆔 ID: {schedule.id}")
                print(f"   📝 الاسم: {schedule.name}")
                print(f"   📚 الشعبة: {schedule.section_id}")
                print(f"   📅 العام الدراسي: {schedule.year_id}")
                
                # جلب تفاصيل الشعبة - بحث يدوي
                section_details = await self.get_section_details(schedule.section_id)
                print(f"   🏷️ اسم الشعبة: {section_details.get('name')}")
                print(f"   🏷️ الصف: {section_details.get('grade_name')}")
                print(f"   🏷️ المرحلة: {section_details.get('stage_name')}")
                print(f"   🏷️ السنة: {section_details.get('year_name')}")
                
                # جلب اسم العام الدراسي
                year_name = await self.get_academic_year_name(schedule.year_id)
                print(f"   🏷️ اسم العام: {year_name}")
                
                # حساب عدد الحصص
                entries_count_result = await self.db.execute(
                    select(func.count(ScheduleEntry.id))
                    .where(ScheduleEntry.schedule_id == schedule.id)
                )
                entries_count = entries_count_result.scalar() or 0
                print(f"   📚 عدد الحصص: {entries_count}")
                
                result_list.append({
                    "id": str(schedule.id),
                    "name": schedule.name,
                    "school_id": str(schedule.school_id),
                    "section_id": str(schedule.section_id) if schedule.section_id else None,
                    "section_name": section_details.get("name"),
                    "grade_id": section_details.get("grade_id"),
                    "grade_name": section_details.get("grade_name"),
                    "stage_id": section_details.get("stage_id"),
                    "stage_name": section_details.get("stage_name"),
                    "year_id": str(schedule.year_id) if schedule.year_id else None,
                    "year_name": year_name,
                    "academic_year_name": year_name,
                    "academic_year_id": str(schedule.year_id) if schedule.year_id else None,
                    "is_active": schedule.is_active,
                    "status": schedule.status,
                    "created_at": schedule.created_at,
                    "updated_at": schedule.updated_at,
                    "entries_count": entries_count,
                    "display_name": f"{section_details.get('stage_name', '')} - {section_details.get('grade_name', '')} - {section_details.get('name', '')} - {schedule.name}".strip(" - ")
                })
            
            print(f"\n✅ تم جلب {len(result_list)} جدول للمدرسة {school_id}")
            print("=" * 60)
            return result_list
            
        except Exception as e:
            print(f"❌ Error in list_schedules: {str(e)}")
            traceback.print_exc()
            return []

    async def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """جلب جدول بواسطة المعرف مع الأسماء - بحث يدوي"""
        try:
            print("=" * 60)
            print(f"🔍 جلب تفاصيل الجدول: {schedule_id}")
            print("=" * 60)
            
            result = await self.db.execute(
                select(Schedule).where(Schedule.id == schedule_id)
            )
            schedule = result.scalar_one_or_none()
            if not schedule:
                print(f"❌ الجدول غير موجود: {schedule_id}")
                return None
            
            print(f"📝 اسم الجدول: {schedule.name}")
            print(f"📚 الشعبة: {schedule.section_id}")
            print(f"📅 العام: {schedule.year_id}")
            
            section_details = await self.get_section_details(schedule.section_id)
            year_name = await self.get_academic_year_name(schedule.year_id)
            
            print(f"🏷️ اسم الشعبة: {section_details.get('name')}")
            print(f"🏷️ الصف: {section_details.get('grade_name')}")
            print(f"🏷️ المرحلة: {section_details.get('stage_name')}")
            print(f"🏷️ العام الدراسي: {year_name}")
            
            return {
                "id": str(schedule.id),
                "name": schedule.name,
                "school_id": str(schedule.school_id),
                "section_id": str(schedule.section_id) if schedule.section_id else None,
                "section_name": section_details.get("name"),
                "grade_id": section_details.get("grade_id"),
                "grade_name": section_details.get("grade_name"),
                "stage_id": section_details.get("stage_id"),
                "stage_name": section_details.get("stage_name"),
                "year_id": str(schedule.year_id) if schedule.year_id else None,
                "year_name": year_name,
                "academic_year_name": year_name,
                "academic_year_id": str(schedule.year_id) if schedule.year_id else None,
                "is_active": schedule.is_active,
                "status": schedule.status,
                "created_at": schedule.created_at,
                "updated_at": schedule.updated_at,
                "display_name": f"{section_details.get('stage_name', '')} - {section_details.get('grade_name', '')} - {section_details.get('name', '')} - {schedule.name}".strip(" - ")
            }
        except Exception as e:
            print(f"❌ Error in get_schedule: {str(e)}")
            return None

    async def get_schedule_with_entries(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """جلب جدول مع جميع مدخلاته - بحث يدوي"""
        try:
            print("=" * 60)
            print(f"🔍 جلب تفاصيل الجدول مع الحصص: {schedule_id}")
            print("=" * 60)
            
            schedule_data = await self.get_schedule(schedule_id)
            if not schedule_data:
                return None
            
            entries_result = await self.db.execute(
                select(ScheduleEntry)
                .where(ScheduleEntry.schedule_id == schedule_id)
                .order_by(ScheduleEntry.day_of_week, ScheduleEntry.period_id)
            )
            entries = list(entries_result.scalars().all())
            
            print(f"\n📚 عدد الحصص: {len(entries)}")
            
            entries_with_names = []
            for idx, entry in enumerate(entries, 1):
                subject_name = await self.get_subject_name(entry.subject_id)
                teacher_name = await self.get_teacher_name(entry.teacher_id)
                room_name = await self.get_room_name(entry.room_id)
                period_name = await self.get_period_name(str(entry.period_id)) if entry.period_id else None
                
                print(f"\n   📖 الحصة #{idx}:")
                print(f"      📅 اليوم: {entry.day_of_week}")
                print(f"      ⏰ الفترة: {entry.period_id}")
                print(f"      📘 المادة: {subject_name}")
                print(f"      👨‍🏫 المعلم: {teacher_name}")
                
                entries_with_names.append({
                    "id": str(entry.id),
                    "day": entry.day_of_week,
                    "day_of_week": entry.day_of_week,
                    "day_name": entry.day_name,
                    "day_name_en": entry.day_name_en,
                    "period": entry.period_id,
                    "period_id": str(entry.period_id) if entry.period_id else None,
                    "period_name": period_name,
                    "subject_id": str(entry.subject_id) if entry.subject_id else None,
                    "subject_name": subject_name,
                    "teacher_id": str(entry.teacher_id) if entry.teacher_id else None,
                    "teacher_name": teacher_name,
                    "room_id": str(entry.room_id) if entry.room_id else None,
                    "room_name": room_name,
                    "notes": entry.notes,
                    "created_at": entry.created_at,
                    "updated_at": entry.updated_at,
                })
            
            schedule_data["entries"] = entries_with_names
            schedule_data["entries_count"] = len(entries_with_names)
            
            print(f"\n✅ تم جلب {len(entries_with_names)} حصة للجدول {schedule_data.get('name')}")
            print("=" * 60)
            
            return schedule_data
            
        except Exception as e:
            print(f"❌ Error in get_schedule_with_entries: {str(e)}")
            return None

    # ============================================================
    # 6️⃣ إنشاء وتحديث وحذف الجداول
    # ============================================================

    async def create_schedule(self, school_id: str, req: ScheduleCreate) -> Schedule:
        """إنشاء جدول جديد - بحث يدوي"""
        try:
            print("=" * 60)
            print("📝 إنشاء جدول جديد:")
            print(f"   school_id: {school_id}")
            print(f"   name: {req.name}")
            print(f"   section_id: {req.section_id}")
            print(f"   year_id: {req.year_id}")
            print(f"   is_active: {req.is_active}")
            print(f"   entries_count: {len(req.entries)}")
            print("=" * 60)
            
            if not school_id:
                raise ValidationException("معرف المدرسة غير موجود")
            
            if not req.section_id:
                raise ValidationException("معرف الشعبة مطلوب")
            
            # التحقق من وجود الشعبة - بحث يدوي
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
                is_active=req.is_active,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.db.add(schedule)
            await self.db.flush()
            
            print(f"✅ تم إنشاء الجدول: {schedule.id}")
            
            # إضافة الحصص
            for idx, entry_data in enumerate(req.entries, 1):
                print(f"\n   📖 إضافة حصة #{idx}:")
                print(f"      📅 اليوم: {entry_data.day}")
                print(f"      ⏰ الفترة: {entry_data.period}")
                print(f"      📘 المادة: {entry_data.subject_id}")
                print(f"      👨‍🏫 المعلم: {entry_data.teacher_id}")
                
                # التحقق من وجود المادة
                subject = await self.find_subject_by_id(entry_data.subject_id)
                if not subject:
                    raise ValidationException(f"المادة غير موجودة: {entry_data.subject_id}")
                print(f"      ✅ المادة: {subject.name}")
                
                # التحقق من وجود المعلم
                if entry_data.teacher_id:
                    teacher = await self.find_teacher_by_id(entry_data.teacher_id)
                    if not teacher:
                        raise ValidationException(f"المعلم غير موجود: {entry_data.teacher_id}")
                    print(f"      ✅ المعلم: {teacher.first_name} {teacher.last_name}")
                
                # التحقق من عدم وجود تعارض
                conflict = await self.find_entry_conflict(
                    schedule.id, entry_data.day, entry_data.period
                )
                if conflict:
                    raise ValidationException(f"يوجد بالفعل حصة في اليوم {entry_data.day} والفترة {entry_data.period}")
                print(f"      ✅ لا يوجد تعارض")
                
                # إنشاء الحصة
                entry = ScheduleEntry(
                    id=str(uuid.uuid4()),
                    schedule_id=schedule.id,
                    school_id=school_id,
                    section_id=req.section_id,
                    day_of_week=entry_data.day,
                    period_id=entry_data.period,
                    subject_id=entry_data.subject_id,
                    teacher_id=entry_data.teacher_id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                self.db.add(entry)
                print(f"      ✅ تم إضافة الحصة: {entry.id}")
            
            await self.db.flush()
            await self.db.refresh(schedule)
            
            print(f"\n✅ تم إنشاء الجدول بنجاح: {schedule.id}")
            print(f"📚 عدد الحصص: {len(req.entries)}")
            print("=" * 60)
            return schedule
            
        except ValidationException:
            raise
        except Exception as e:
            print(f"❌ Error in create_schedule: {str(e)}")
            traceback.print_exc()
            raise

    async def update_schedule(self, schedule_id: str, req: ScheduleUpdate) -> Schedule:
        """تحديث جدول"""
        try:
            print("=" * 60)
            print(f"📝 تحديث الجدول: {schedule_id}")
            print("=" * 60)
            
            result = await self.db.execute(
                select(Schedule).where(Schedule.id == schedule_id)
            )
            schedule = result.scalar_one_or_none()
            if not schedule:
                raise NotFoundException("الجدول غير موجود")
            
            print(f"📝 الاسم الحالي: {schedule.name}")
            
            update_data = req.model_dump(exclude_unset=True)
            excluded_fields = ['grade_id', 'stage_id']
            for field in excluded_fields:
                update_data.pop(field, None)
            
            for key, value in update_data.items():
                if hasattr(schedule, key):
                    setattr(schedule, key, value)
                    print(f"   ✅ تحديث {key}: {value}")
            
            schedule.updated_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(schedule)
            
            print(f"✅ تم تحديث الجدول: {schedule.id}")
            print("=" * 60)
            return schedule
            
        except NotFoundException:
            raise
        except Exception as e:
            print(f"❌ Error in update_schedule: {str(e)}")
            raise

    async def delete_schedule(self, schedule_id: str) -> bool:
        """حذف جدول (تعطيل فقط)"""
        try:
            print("=" * 60)
            print(f"🗑️ حذف الجدول: {schedule_id}")
            print("=" * 60)
            
            result = await self.db.execute(
                select(Schedule).where(Schedule.id == schedule_id)
            )
            schedule = result.scalar_one_or_none()
            if not schedule:
                raise NotFoundException("الجدول غير موجود")
            
            print(f"📝 اسم الجدول: {schedule.name}")
            
            schedule.is_active = False
            schedule.updated_at = datetime.utcnow()
            
            entries_result = await self.db.execute(
                select(ScheduleEntry).where(ScheduleEntry.schedule_id == schedule_id)
            )
            entries = list(entries_result.scalars().all())
            print(f"📚 عدد الحصص المحذوفة: {len(entries)}")
            
            for entry in entries:
                await self.db.delete(entry)
            
            await self.db.flush()
            
            print(f"✅ تم حذف الجدول: {schedule.id}")
            print("=" * 60)
            return True
            
        except NotFoundException:
            raise
        except Exception as e:
            print(f"❌ Error in delete_schedule: {str(e)}")
            raise

    # ============================================================
    # 7️⃣ دوال الحصص (Entries)
    # ============================================================

    async def add_entry(self, schedule_id: str, req: ScheduleEntryCreate) -> ScheduleEntry:
        """إضافة مدخل (حصة) إلى الجدول"""
        try:
            print("=" * 60)
            print("📝 إضافة حصة جديدة:")
            print(f"   schedule_id: {schedule_id}")
            print(f"   day: {req.day}")
            print(f"   period: {req.period}")
            print(f"   subject_id: {req.subject_id}")
            print(f"   teacher_id: {req.teacher_id}")
            print("=" * 60)
            
            schedule_result = await self.db.execute(
                select(Schedule).where(Schedule.id == schedule_id)
            )
            schedule = schedule_result.scalar_one_or_none()
            if not schedule:
                raise NotFoundException("الجدول غير موجود")
            
            print(f"📝 اسم الجدول: {schedule.name}")
            
            subject = await self.find_subject_by_id(req.subject_id)
            if not subject:
                raise ValidationException(f"المادة غير موجودة: {req.subject_id}")
            print(f"✅ تم العثور على المادة: {subject.name}")
            
            if req.teacher_id:
                teacher = await self.find_teacher_by_id(req.teacher_id)
                if not teacher:
                    raise ValidationException(f"المعلم غير موجود: {req.teacher_id}")
                print(f"✅ تم العثور على المعلم: {teacher.first_name} {teacher.last_name}")
            
            conflict = await self.find_entry_conflict(
                schedule_id, req.day, req.period
            )
            if conflict:
                raise ValidationException("يوجد بالفعل حصة في هذا اليوم والفترة")
            
            print("✅ لا يوجد تعارض")
            
            entry = ScheduleEntry(
                id=str(uuid.uuid4()),
                schedule_id=schedule_id,
                school_id=schedule.school_id,
                section_id=schedule.section_id,
                day_of_week=req.day,
                period_id=req.period,
                subject_id=req.subject_id,
                teacher_id=req.teacher_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.db.add(entry)
            await self.db.flush()
            await self.db.refresh(entry)
            
            print(f"✅ تم إضافة الحصة بنجاح: {entry.id}")
            print("=" * 60)
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
            print("=" * 60)
            print(f"📝 تحديث الحصة: {entry_id}")
            print("=" * 60)
            
            result = await self.db.execute(
                select(ScheduleEntry).where(ScheduleEntry.id == entry_id)
            )
            entry = result.scalar_one_or_none()
            if not entry:
                raise NotFoundException("المدخل غير موجود")
            
            print(f"📅 اليوم الحالي: {entry.day_of_week}")
            print(f"⏰ الفترة الحالية: {entry.period_id}")
            
            update_data = req.model_dump(exclude_unset=True)
            
            if 'day' in update_data:
                update_data['day_of_week'] = update_data.pop('day')
            if 'period' in update_data:
                update_data['period_id'] = update_data.pop('period')
            
            for key, value in update_data.items():
                if hasattr(entry, key):
                    setattr(entry, key, value)
                    print(f"   ✅ تحديث {key}: {value}")
            
            entry.updated_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(entry)
            
            print(f"✅ تم تحديث الحصة: {entry.id}")
            print("=" * 60)
            return entry
            
        except NotFoundException:
            raise
        except Exception as e:
            print(f"❌ Error in update_entry: {str(e)}")
            raise

    async def delete_entry(self, entry_id: str) -> bool:
        """حذف مدخل (حصة) من الجدول"""
        try:
            print("=" * 60)
            print(f"🗑️ حذف الحصة: {entry_id}")
            print("=" * 60)
            
            result = await self.db.execute(
                select(ScheduleEntry).where(ScheduleEntry.id == entry_id)
            )
            entry = result.scalar_one_or_none()
            if not entry:
                raise NotFoundException("المدخل غير موجود")
            
            print(f"📅 اليوم: {entry.day_of_week}")
            print(f"⏰ الفترة: {entry.period_id}")
            
            await self.db.delete(entry)
            await self.db.flush()
            
            print(f"✅ تم حذف الحصة: {entry.id}")
            print("=" * 60)
            return True
            
        except NotFoundException:
            raise
        except Exception as e:
            print(f"❌ Error in delete_entry: {str(e)}")
            raise

    # ============================================================
    # 8️⃣ دوال تشخيصية
    # ============================================================

    async def check_available_data(self, school_id: str) -> Dict[str, Any]:
        """التحقق من البيانات المتاحة للمدرسة"""
        try:
            print("=" * 60)
            print(f"🔍 التحقق من البيانات للمدرسة: {school_id}")
            print("=" * 60)
            
            sections = await self.get_sections_objects(school_id)
            years = await self.get_academic_years_objects(school_id)
            schedules = await self.list_schedules(school_id)
            
            print(f"\n📊 النتائج:")
            print(f"   📚 الشعب: {len(sections)}")
            print(f"   📅 السنوات الدراسية: {len(years)}")
            print(f"   📋 الجداول: {len(schedules)}")
            
            return {
                "school_id": school_id,
                "sections": [
                    {
                        "id": str(s.id), 
                        "name": s.name, 
                        "is_active": s.is_active,
                        "grade_id": str(s.grade_id) if s.grade_id else None
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


# ============================================================
# التصدير
# ============================================================

__all__ = [
    "ScheduleService",
]
