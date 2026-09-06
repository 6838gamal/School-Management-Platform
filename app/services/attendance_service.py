"""Attendance service for students and teachers - Like schedules module."""
from datetime import datetime, timezone
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.core.exceptions import NotFoundException, ValidationException
from app.repositories.attendance import StudentAttendanceRepository, TeacherAttendanceRepository
from app.schemas.attendance import (
    StudentAttendanceBatch, 
    StudentAttendanceCreate, 
    TeacherAttendanceCreate,
    StudentAttendanceStatus,
    TeacherAttendanceStatus,
)
from app.models.students import Student
from app.models.teachers import Teacher
from app.models.academics import Section, Period, Grade, Stage, AcademicYear
from app.models.attendance import StudentAttendance, TeacherAttendance

logger = logging.getLogger(__name__)


class AttendanceService:
    """خدمة الحضور المتكاملة - مثل نظام الجداول."""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.student_att = StudentAttendanceRepository(db)
        self.teacher_att = TeacherAttendanceRepository(db)

    # ============================================================
    # 1️⃣ دوال التصفية المتدرجة (Hierarchy) - مثل ScheduleService
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
            
            logger.info(f"✅ Found {len(years)} academic years for school {school_id}")
            
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
            logger.error(f"Error in get_academic_years: {str(e)}")
            return []

    async def get_stages_by_year(
        self, 
        school_id: str, 
        year_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """جلب المراحل حسب السنة الدراسية"""
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
            
            logger.info(f"✅ Found {len(stages)} stages for school {school_id} with year_id={year_id}")
            
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
            logger.error(f"Error in get_stages_by_year: {str(e)}")
            return []

    async def get_grades_by_stage(
        self, 
        school_id: str, 
        stage_id: Optional[str] = None,
        year_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """جلب الصفوف حسب المرحلة والسنة"""
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
            
            logger.info(f"✅ Found {len(grades)} grades for school {school_id} with stage_id={stage_id}")
            
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
            logger.error(f"Error in get_grades_by_stage: {str(e)}")
            return []

    async def get_sections_by_grade(
        self, 
        school_id: str, 
        grade_id: Optional[str] = None,
        year_id: Optional[str] = None,
        stage_id: Optional[str] = None,
        include_all: bool = False
    ) -> List[Dict[str, Any]]:
        """جلب الشعب حسب الصف - مثل ScheduleService"""
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
            
            logger.info(f"✅ Found {len(sections)} sections for school {school_id} with grade_id={grade_id}")
            
            # جلب تفاصيل إضافية لكل شعبة - بحث يدوي
            sections_data = []
            for section in sections:
                grade_name = None
                stage_name = None
                year_name = None
                
                if section.grade_id:
                    grade_result = await self.db.execute(
                        select(Grade).where(Grade.id == section.grade_id)
                    )
                    grade = grade_result.scalar_one_or_none()
                    if grade:
                        grade_name = grade.name
                        
                        if grade.stage_id:
                            stage_result = await self.db.execute(
                                select(Stage).where(Stage.id == grade.stage_id)
                            )
                            stage = stage_result.scalar_one_or_none()
                            if stage:
                                stage_name = stage.name
                        
                        if grade.year_id:
                            year_result = await self.db.execute(
                                select(AcademicYear).where(AcademicYear.id == grade.year_id)
                            )
                            year = year_result.scalar_one_or_none()
                            if year:
                                year_name = year.name
                
                sections_data.append({
                    "id": str(section.id),
                    "name": section.name,
                    "grade_id": str(section.grade_id) if section.grade_id else None,
                    "grade_name": grade_name,
                    "stage_id": str(grade.stage_id) if grade and grade.stage_id else None,
                    "stage_name": stage_name,
                    "year_id": str(grade.year_id) if grade and grade.year_id else None,
                    "year_name": year_name,
                    "capacity": section.capacity,
                    "is_active": section.is_active,
                    "display_name": f"{stage_name if stage_name else ''} - {grade_name if grade_name else ''} - {section.name}".strip(" - ")
                })
            
            return sections_data
        except Exception as e:
            logger.error(f"Error in get_sections_by_grade: {str(e)}")
            return []

    async def get_full_hierarchy(
        self,
        school_id: str,
        year_id: Optional[str] = None,
        stage_id: Optional[str] = None,
        grade_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """جلب التسلسل الهرمي الكامل - مثل ScheduleService"""
        try:
            logger.info(f"🔍 Getting full hierarchy for school {school_id}")
            logger.info(f"   year_id: {year_id}, stage_id: {stage_id}, grade_id: {grade_id}")
            
            # 1. جلب السنوات
            years = await self.get_academic_years(school_id)
            logger.info(f"   📊 Years: {len(years)}")
            
            # 2. جلب المراحل (حسب السنة إذا كانت محددة)
            stages = await self.get_stages_by_year(school_id, year_id)
            logger.info(f"   📊 Stages: {len(stages)}")
            
            # 3. جلب الصفوف (حسب المرحلة والسنة إذا كانت محددة)
            grades = await self.get_grades_by_stage(school_id, stage_id, year_id)
            logger.info(f"   📊 Grades: {len(grades)}")
            
            # 4. جلب الشعب (حسب الصف إذا كان محددا)
            sections = await self.get_sections_by_grade(
                school_id, grade_id, year_id, stage_id
            )
            logger.info(f"   📊 Sections: {len(sections)}")
            
            result = {
                "years": years,
                "stages": stages,
                "grades": grades,
                "sections": sections,
                "selected_year": year_id,
                "selected_stage": stage_id,
                "selected_grade": grade_id,
            }
            
            logger.info(f"✅ Hierarchy complete: years={len(years)}, stages={len(stages)}, grades={len(grades)}, sections={len(sections)}")
            return result
        except Exception as e:
            logger.error(f"Error in get_full_hierarchy: {str(e)}")
            return {"years": [], "stages": [], "grades": [], "sections": []}

    # ============================================================
    # 2️⃣ دوال البحث اليدوي
    # ============================================================

    async def _get_student_by_id(self, student_id: str) -> Optional[Student]:
        """جلب طالب بالمعرف - بحث يدوي"""
        try:
            result = await self.db.execute(
                select(Student).where(Student.id == student_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error in _get_student_by_id: {str(e)}")
            return None

    async def _get_teacher_by_id(self, teacher_id: str) -> Optional[Teacher]:
        """جلب معلم بالمعرف - بحث يدوي"""
        try:
            result = await self.db.execute(
                select(Teacher).where(Teacher.id == teacher_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error in _get_teacher_by_id: {str(e)}")
            return None

    async def _get_section_by_id(self, section_id: str) -> Optional[Section]:
        """جلب شعبة بالمعرف - بحث يدوي"""
        try:
            result = await self.db.execute(
                select(Section).where(Section.id == section_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error in _get_section_by_id: {str(e)}")
            return None

    async def _get_period_by_id(self, period_id: str) -> Optional[Period]:
        """جلب حصة بالمعرف - بحث يدوي"""
        try:
            result = await self.db.execute(
                select(Period).where(Period.id == period_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error in _get_period_by_id: {str(e)}")
            return None

    async def _get_grade_by_id(self, grade_id: str) -> Optional[Grade]:
        """جلب صف بالمعرف - بحث يدوي"""
        try:
            result = await self.db.execute(
                select(Grade).where(Grade.id == grade_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error in _get_grade_by_id: {str(e)}")
            return None

    async def _get_stage_by_id(self, stage_id: str) -> Optional[Stage]:
        """جلب مرحلة بالمعرف - بحث يدوي"""
        try:
            result = await self.db.execute(
                select(Stage).where(Stage.id == stage_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error in _get_stage_by_id: {str(e)}")
            return None

    async def _get_academic_year_by_id(self, year_id: str) -> Optional[AcademicYear]:
        """جلب سنة دراسية بالمعرف - بحث يدوي"""
        try:
            result = await self.db.execute(
                select(AcademicYear).where(AcademicYear.id == year_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error in _get_academic_year_by_id: {str(e)}")
            return None

    async def _get_section_details(self, section_id: str) -> Dict[str, Any]:
        """جلب تفاصيل الشعبة - بحث يدوي"""
        try:
            if not section_id:
                return {"name": None, "grade_name": None, "stage_name": None}
            
            section = await self._get_section_by_id(section_id)
            if not section:
                return {"name": None, "grade_name": None, "stage_name": None}
            
            grade_name = None
            stage_name = None
            
            if section.grade_id:
                grade = await self._get_grade_by_id(section.grade_id)
                if grade:
                    grade_name = grade.name
                    if grade.stage_id:
                        stage = await self._get_stage_by_id(grade.stage_id)
                        if stage:
                            stage_name = stage.name
            
            return {
                "name": section.name,
                "grade_name": grade_name,
                "stage_name": stage_name,
            }
        except Exception as e:
            logger.error(f"Error in _get_section_details: {str(e)}")
            return {"name": None, "grade_name": None, "stage_name": None}

    def _get_status_arabic(self, status: str) -> str:
        """الحصول على اسم الحالة بالعربية"""
        mapping = {
            "present": "✅ حاضر",
            "absent": "❌ غائب",
            "late": "⏰ متأخر",
            "excused": "📝 معذور",
        }
        return mapping.get(status, status)

    # ============================================================
    # 3️⃣ جلب الطلاب مع تفاصيلهم
    # ============================================================

    async def get_students_with_details(
        self,
        school_id: str,
        section_id: Optional[str] = None,
        date: Optional[str] = None,
        period_id: Optional[str] = None,
        include_attendance: bool = True
    ) -> List[Dict[str, Any]]:
        """جلب الطلاب مع تفاصيلهم وحالة الحضور"""
        try:
            stmt = select(Student).where(
                Student.school_id == school_id,
                Student.is_active == True
            )
            if section_id:
                stmt = stmt.where(Student.section_id == section_id)
            stmt = stmt.order_by(Student.first_name, Student.last_name)
            
            result = await self.db.execute(stmt)
            students = result.scalars().all()
            
            logger.info(f"✅ Found {len(students)} students for school {school_id} with section_id={section_id}")
            
            students_data = []
            for student in students:
                section_details = await self._get_section_details(student.section_id)
                
                student_dict = {
                    "id": str(student.id),
                    "student_number": student.student_number,
                    "full_name": student.full_name,
                    "first_name": student.first_name,
                    "last_name": student.last_name,
                    "section_id": str(student.section_id) if student.section_id else None,
                    "section_name": section_details.get("name"),
                    "grade_id": str(student.grade_id) if student.grade_id else None,
                    "grade_name": section_details.get("grade_name"),
                    "stage_id": str(student.stage_id) if student.stage_id else None,
                    "stage_name": section_details.get("stage_name"),
                    "year_id": str(student.year_id) if student.year_id else None,
                    "attendance_status": None,
                    "attendance_id": None,
                    "attendance_note": None,
                    "has_attendance": False,
                }
                
                if include_attendance and date:
                    att_stmt = select(StudentAttendance).where(
                        StudentAttendance.student_id == student.id,
                        StudentAttendance.date == date
                    )
                    if period_id:
                        att_stmt = att_stmt.where(StudentAttendance.period_id == period_id)
                    
                    att_result = await self.db.execute(att_stmt)
                    attendance = att_result.scalar_one_or_none()
                    
                    if attendance:
                        student_dict["attendance_status"] = attendance.status
                        student_dict["attendance_status_arabic"] = self._get_status_arabic(attendance.status)
                        student_dict["attendance_id"] = str(attendance.id)
                        student_dict["attendance_note"] = attendance.note
                        student_dict["has_attendance"] = True
                
                students_data.append(student_dict)
            
            return students_data
        except Exception as e:
            logger.error(f"Error in get_students_with_details: {str(e)}")
            return []

    # ============================================================
    # 4️⃣ جلب سجلات الحضور مع التفاصيل
    # ============================================================

    async def get_attendance_records_with_details(
        self,
        school_id: str,
        date: str,
        section_id: Optional[str] = None,
        period_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """جلب سجلات الحضور مع تفاصيل الطالب"""
        try:
            stmt = select(StudentAttendance).where(
                StudentAttendance.school_id == school_id,
                StudentAttendance.date == date
            )
            if section_id:
                stmt = stmt.where(StudentAttendance.section_id == section_id)
            if period_id:
                stmt = stmt.where(StudentAttendance.period_id == period_id)
            
            result = await self.db.execute(stmt)
            records = result.scalars().all()
            
            logger.info(f"✅ Found {len(records)} attendance records for school {school_id} date={date}")
            
            records_data = []
            for record in records:
                student = await self._get_student_by_id(record.student_id)
                student_name = student.full_name if student else "غير معروف"
                student_number = student.student_number if student else ""
                
                section_details = await self._get_section_details(record.section_id)
                
                records_data.append({
                    "id": str(record.id),
                    "student_id": str(record.student_id),
                    "student_name": student_name,
                    "student_number": student_number,
                    "section_id": str(record.section_id) if record.section_id else None,
                    "section_name": section_details.get("name"),
                    "grade_id": str(record.grade_id) if record.grade_id else None,
                    "grade_name": section_details.get("grade_name"),
                    "stage_id": str(record.stage_id) if record.stage_id else None,
                    "stage_name": section_details.get("stage_name"),
                    "year_id": str(record.year_id) if record.year_id else None,
                    "date": record.date,
                    "status": record.status,
                    "status_arabic": self._get_status_arabic(record.status),
                    "note": record.note,
                    "recorded_by": str(record.recorded_by) if record.recorded_by else None,
                })
            
            return records_data
        except Exception as e:
            logger.error(f"Error in get_attendance_records_with_details: {str(e)}")
            return []

    # ============================================================
    # 5️⃣ جلب ملخص الحضور
    # ============================================================

    async def get_attendance_summary(
        self, 
        school_id: str, 
        date: str,
        section_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """جلب ملخص الحضور"""
        try:
            stmt = select(StudentAttendance).where(
                StudentAttendance.school_id == school_id,
                StudentAttendance.date == date
            )
            if section_id:
                stmt = stmt.where(StudentAttendance.section_id == section_id)
            
            result = await self.db.execute(stmt)
            records = result.scalars().all()
            
            total = len(records)
            present = sum(1 for r in records if r.status == "present")
            absent = sum(1 for r in records if r.status == "absent")
            late = sum(1 for r in records if r.status == "late")
            excused = sum(1 for r in records if r.status == "excused")
            
            total_students = 0
            if section_id:
                student_stmt = select(func.count(Student.id)).where(
                    Student.school_id == school_id,
                    Student.section_id == section_id,
                    Student.is_active == True
                )
                total_students = await self.db.scalar(student_stmt) or 0
            
            return {
                "total": total_students or total,
                "present": present,
                "absent": absent,
                "late": late,
                "excused": excused,
                "rate": round((present / total_students * 100) if total_students > 0 else 0, 1)
            }
        except Exception as e:
            logger.error(f"Error in get_attendance_summary: {str(e)}")
            return {"total": 0, "present": 0, "absent": 0, "late": 0, "excused": 0, "rate": 0}

    # ============================================================
    # 6️⃣ student_summary - مهم! هذه الدالة مستخدمة في الروتس
    # ============================================================

    async def student_summary(
        self, 
        school_id: str, 
        date: str,
        section_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        جلب ملخص حضور الطلاب - هذه الدالة مستخدمة في الروتس
        وهي نفسها get_attendance_summary ولكن باسم مختلف
        """
        return await self.get_attendance_summary(school_id, date, section_id)

    # ============================================================
    # 7️⃣ جلب حضور شعبة مع تفاصيل الطلاب
    # ============================================================

    async def section_attendance(
        self, 
        section_id: str, 
        date: str,
        period_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """جلب حضور شعبة مع تفاصيل الطلاب"""
        records = await self.student_att.list_by_section_date(section_id, date)
        
        if period_id:
            records = [r for r in records if r.period_id == period_id]
        
        result = []
        for r in records:
            student = await self._get_student_by_id(r.student_id)
            section_details = await self._get_section_details(r.section_id)
            
            if student:
                result.append({
                    "id": str(r.id),
                    "student_id": r.student_id,
                    "student_number": student.student_number,
                    "student_name": student.full_name,
                    "status": r.status,
                    "status_arabic": self._get_status_arabic(r.status),
                    "note": r.note,
                    "date": r.date,
                    "section_id": r.section_id,
                    "section_name": section_details.get("name"),
                    "grade_name": section_details.get("grade_name"),
                    "stage_name": section_details.get("stage_name"),
                    "period_id": r.period_id,
                    "recorded_by": r.recorded_by,
                    "created_at": r.created_at,
                })
            else:
                result.append({
                    "id": str(r.id),
                    "student_id": r.student_id,
                    "student_name": "غير معروف",
                    "student_number": "",
                    "status": r.status,
                    "status_arabic": self._get_status_arabic(r.status),
                    "note": r.note,
                    "date": r.date,
                    "section_id": r.section_id,
                    "section_name": section_details.get("name"),
                    "grade_name": section_details.get("grade_name"),
                    "stage_name": section_details.get("stage_name"),
                    "period_id": r.period_id,
                    "recorded_by": r.recorded_by,
                    "created_at": r.created_at,
                })
        
        return result

    # ============================================================
    # 8️⃣ جلب سجل حضور طالب تاريخي
    # ============================================================

    async def get_student_attendance_history(
        self,
        student_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """جلب سجل حضور طالب تاريخي"""
        student = await self._get_student_by_id(student_id)
        if not student:
            raise NotFoundException(f"الطالب {student_id} غير موجود")
        
        stmt = select(StudentAttendance).where(
            StudentAttendance.student_id == student_id
        )
        
        if date_from:
            stmt = stmt.where(StudentAttendance.date >= date_from)
        if date_to:
            stmt = stmt.where(StudentAttendance.date <= date_to)
        
        stmt = stmt.order_by(StudentAttendance.date.desc()).limit(limit)
        records = await self.db.execute(stmt)
        records = list(records.scalars().all())
        
        result = []
        for r in records:
            period_name = None
            if r.period_id:
                period = await self._get_period_by_id(r.period_id)
                if period:
                    period_name = period.name
            
            section_details = await self._get_section_details(r.section_id)
            
            result.append({
                "id": r.id,
                "date": r.date,
                "status": r.status,
                "status_arabic": self._get_status_arabic(r.status),
                "note": r.note,
                "period_name": period_name,
                "section_name": section_details.get("name"),
                "recorded_at": r.created_at,
                "recorded_by": r.recorded_by,
            })
        
        return result

    # ============================================================
    # 9️⃣ تسجيل حضور طالب
    # ============================================================

    async def record_student(
        self, 
        school_id: str, 
        user_id: str, 
        req: StudentAttendanceCreate
    ) -> Dict[str, Any]:
        """تسجيل حضور طالب مع التحقق"""
        logger.info(f"Recording student attendance: student_id={req.student_id}, date={req.date}")
        
        student = await self._get_student_by_id(req.student_id)
        if not student:
            raise NotFoundException(f"الطالب {req.student_id} غير موجود")
        
        if student.school_id != school_id:
            raise ValidationException("الطالب لا ينتمي إلى مدرستك")
        
        if not student.is_active:
            raise ValidationException(f"الطالب {student.full_name} غير نشط")
        
        if req.section_id:
            section = await self._get_section_by_id(req.section_id)
            if not section:
                raise NotFoundException(f"الشعبة {req.section_id} غير موجودة")
        
        if req.period_id:
            period = await self._get_period_by_id(req.period_id)
            if not period:
                raise NotFoundException(f"الحصة {req.period_id} غير موجودة")
        
        existing = await self.student_att.get_by_student_date(
            req.student_id, 
            req.date, 
            req.period_id
        )
        
        if existing:
            existing.status = req.status
            existing.note = req.note
            existing.recorded_by = user_id
            existing.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
            return {
                "id": existing.id,
                "action": "updated",
                "student_id": req.student_id,
                "student_name": student.full_name,
                "date": req.date,
                "status": req.status,
            }
        
        record = await self.student_att.create(
            school_id=school_id,
            student_id=req.student_id,
            section_id=req.section_id or student.section_id,
            period_id=req.period_id,
            schedule_entry_id=req.schedule_entry_id,
            date=req.date,
            status=req.status,
            note=req.note,
            recorded_by=user_id,
        )
        
        return {
            "id": record.id,
            "action": "created",
            "student_id": req.student_id,
            "student_name": student.full_name,
            "date": req.date,
            "status": req.status,
        }

    # ============================================================
    # 🔟 تسجيل حضور طلاب دفعة
    # ============================================================

    async def batch_record(
        self, 
        school_id: str, 
        user_id: str, 
        req: StudentAttendanceBatch
    ) -> Dict[str, Any]:
        """تسجيل حضور طلاب دفعة واحدة"""
        logger.info(f"Batch recording attendance: section_id={req.section_id}, date={req.date}")
        
        if req.section_id:
            section = await self._get_section_by_id(req.section_id)
            if not section:
                raise NotFoundException(f"الشعبة {req.section_id} غير موجودة")
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        results = []
        
        for r in req.records:
            student_id = r.get("student_id")
            status = r.get("status")
            
            if not student_id or not status:
                skipped_count += 1
                continue
            
            try:
                student = await self._get_student_by_id(student_id)
                if not student:
                    errors.append(f"الطالب {student_id} غير موجود")
                    skipped_count += 1
                    continue
                
                existing = await self.student_att.get_by_student_date(
                    student_id, 
                    req.date, 
                    req.period_id
                )
                
                note = r.get("note")
                
                if existing:
                    existing.status = status
                    existing.note = note
                    existing.recorded_by = user_id
                    existing.updated_at = datetime.now(timezone.utc)
                    updated_count += 1
                else:
                    await self.student_att.create(
                        school_id=school_id,
                        student_id=student_id,
                        section_id=req.section_id or student.section_id,
                        period_id=req.period_id,
                        date=req.date,
                        status=status,
                        note=note,
                        recorded_by=user_id,
                    )
                    created_count += 1
                
                results.append({
                    "student_id": student_id,
                    "student_name": student.full_name,
                    "status": status,
                    "action": "updated" if existing else "created",
                })
                
            except Exception as e:
                logger.error(f"Error processing student {student_id}: {e}")
                errors.append(str(e))
                skipped_count += 1
        
        await self.db.flush()
        
        return {
            "recorded": created_count + updated_count,
            "created": created_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "errors": errors,
            "results": results,
            "date": req.date,
            "section_id": req.section_id,
            "period_id": req.period_id,
        }

    # ============================================================
    # 1️⃣1️⃣ تسجيل حضور معلم
    # ============================================================

    async def record_teacher(
        self, 
        school_id: str, 
        user_id: str, 
        req: TeacherAttendanceCreate
    ) -> Dict[str, Any]:
        """تسجيل حضور معلم مع التحقق"""
        logger.info(f"Recording teacher attendance: teacher_id={req.teacher_id}, date={req.date}")
        
        teacher = await self._get_teacher_by_id(req.teacher_id)
        if not teacher:
            raise NotFoundException(f"المعلم {req.teacher_id} غير موجود")
        
        if teacher.school_id != school_id:
            raise ValidationException("المعلم لا ينتمي إلى مدرستك")
        
        if not teacher.is_active:
            raise ValidationException(f"المعلم {teacher.full_name} غير نشط")
        
        existing = await self.teacher_att.get_by_teacher_date(req.teacher_id, req.date)
        
        if existing:
            existing.status = req.status
            existing.note = req.note
            existing.recorded_by = user_id
            existing.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
            return {
                "id": existing.id,
                "action": "updated",
                "teacher_id": req.teacher_id,
                "teacher_name": teacher.full_name,
                "date": req.date,
                "status": req.status,
            }
        
        record = await self.teacher_att.create(
            school_id=school_id,
            teacher_id=req.teacher_id,
            date=req.date,
            status=req.status,
            note=req.note,
            recorded_by=user_id,
        )
        
        return {
            "id": record.id,
            "action": "created",
            "teacher_id": req.teacher_id,
            "teacher_name": teacher.full_name,
            "date": req.date,
            "status": req.status,
        }

    # ============================================================
    # 1️⃣2️⃣ جلب المعلمين الغائبين
    # ============================================================

    async def absent_teachers(
        self, 
        school_id: str, 
        date: str
    ) -> List[Dict[str, Any]]:
        """جلب المعلمين الغائبين مع تفاصيلهم"""
        records = await self.teacher_att.absent_teachers(school_id, date)
        
        result = []
        for r in records:
            teacher = await self._get_teacher_by_id(r.teacher_id)
            if teacher:
                result.append({
                    "teacher_id": r.teacher_id,
                    "teacher_name": teacher.full_name,
                    "employee_number": teacher.employee_number,
                    "email": teacher.email,
                    "phone": getattr(teacher, 'phone', None),
                    "status": r.status,
                    "note": r.note,
                    "date": r.date,
                })
            else:
                result.append({
                    "teacher_id": r.teacher_id,
                    "teacher_name": "غير معروف",
                    "status": r.status,
                    "note": r.note,
                    "date": r.date,
                })
        
        return result

    # ============================================================
    # 1️⃣3️⃣ جلب إحصائيات الحضور للشعب
    # ============================================================

    async def section_attendance_stats(
        self,
        school_id: str,
        date: str,
    ) -> List[Dict[str, Any]]:
        """جلب إحصائيات الحضور لكل شعبة"""
        result = await self.db.execute(
            select(Section).where(
                Section.school_id == school_id,
                Section.is_active == True
            )
        )
        sections = list(result.scalars().all())
        
        result_list = []
        for section in sections:
            student_count_result = await self.db.execute(
                select(func.count()).select_from(Student).where(
                    Student.section_id == section.id,
                    Student.is_active == True
                )
            )
            student_count = student_count_result.scalar() or 0
            
            section_details = await self._get_section_details(section.id)
            
            if student_count == 0:
                result_list.append({
                    "section_id": section.id,
                    "section_name": section.name,
                    "grade_name": section_details.get("grade_name"),
                    "stage_name": section_details.get("stage_name"),
                    "total_students": 0,
                    "present": 0,
                    "absent": 0,
                    "late": 0,
                    "excused": 0,
                    "attendance_percentage": 0,
                })
                continue
            
            records_result = await self.db.execute(
                select(StudentAttendance).where(
                    StudentAttendance.section_id == section.id,
                    StudentAttendance.date == date
                )
            )
            records = list(records_result.scalars().all())
            
            present = sum(1 for r in records if r.status == "present")
            absent = sum(1 for r in records if r.status == "absent")
            late = sum(1 for r in records if r.status == "late")
            excused = sum(1 for r in records if r.status == "excused")
            
            percentage = round((present / student_count) * 100, 2) if student_count > 0 else 0
            
            result_list.append({
                "section_id": section.id,
                "section_name": section.name,
                "grade_name": section_details.get("grade_name"),
                "stage_name": section_details.get("stage_name"),
                "total_students": student_count,
                "present": present,
                "absent": absent,
                "late": late,
                "excused": excused,
                "attendance_percentage": percentage,
            })
        
        return result_list

    # ============================================================
    # 1️⃣4️⃣ جلب تفاصيل حضور طالب
    # ============================================================

    async def get_student_attendance_details(
        self,
        student_id: str,
        date: Optional[str] = None,
        period_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """جلب تفاصيل حضور طالب"""
        student = await self._get_student_by_id(student_id)
        if not student:
            return None
        
        stmt = select(StudentAttendance).where(
            StudentAttendance.student_id == student_id
        )
        
        if date:
            stmt = stmt.where(StudentAttendance.date == date)
        if period_id:
            stmt = stmt.where(StudentAttendance.period_id == period_id)
        
        record_result = await self.db.execute(stmt)
        record = record_result.scalar_one_or_none()
        
        if not record:
            section_details = await self._get_section_details(student.section_id)
            return {
                "student_id": student.id,
                "student_number": student.student_number,
                "student_name": student.full_name,
                "has_attendance": False,
                "attendance_status": None,
                "section_name": section_details.get("name"),
                "grade_name": section_details.get("grade_name"),
                "stage_name": section_details.get("stage_name"),
            }
        
        period_name = None
        if record.period_id:
            period = await self._get_period_by_id(record.period_id)
            if period:
                period_name = period.name
        
        section_details = await self._get_section_details(record.section_id)
        
        return {
            "student_id": student.id,
            "student_number": student.student_number,
            "student_name": student.full_name,
            "has_attendance": True,
            "attendance_id": record.id,
            "attendance_status": record.status,
            "attendance_status_arabic": self._get_status_arabic(record.status),
            "attendance_note": record.note,
            "attendance_date": record.date,
            "period_name": period_name,
            "section_name": section_details.get("name"),
            "grade_name": section_details.get("grade_name"),
            "stage_name": section_details.get("stage_name"),
            "recorded_by": record.recorded_by,
            "created_at": record.created_at,
        }


# ============================================================
# التصدير
# ============================================================

__all__ = [
    "AttendanceService",
]
