"""Attendance service for students and teachers."""
from datetime import datetime, timezone
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

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
from app.models.academics import Section, Period

logger = logging.getLogger(__name__)


class AttendanceService:
    """خدمة الحضور المتكاملة مع Students و Academics."""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.student_att = StudentAttendanceRepository(db)
        self.teacher_att = TeacherAttendanceRepository(db)

    # ============================================================
    # 1️⃣ تسجيل حضور طالب (مع التحقق من Students و Academics)
    # ============================================================

    async def record_student(
        self, 
        school_id: str, 
        user_id: str, 
        req: StudentAttendanceCreate
    ) -> Dict[str, Any]:
        """
        تسجيل حضور طالب مع التحقق من:
        - وجود الطالب (Students Routes)
        - نشاط الطالب (Students Routes)
        - وجود الشعبة (Academics Routes)
        - وجود الحصة (Academics Routes)
        """
        logger.info(f"Recording student attendance: student_id={req.student_id}, date={req.date}")
        
        # --- 1. التحقق من وجود الطالب من Students Routes ---
        result = await self.db.execute(
            select(Student).where(Student.id == req.student_id)
        )
        student = result.scalar_one_or_none()
        if not student:
            raise NotFoundException(f"الطالب {req.student_id} غير موجود")
        
        if student.school_id != school_id:
            raise ValidationException("الطالب لا ينتمي إلى مدرستك")
        
        if not student.is_active:
            raise ValidationException(f"الطالب {student.full_name} غير نشط")
        
        # --- 2. التحقق من وجود الشعبة من Academics Routes (إذا تم تحديدها) ---
        if req.section_id:
            result = await self.db.execute(
                select(Section).where(Section.id == req.section_id)
            )
            section = result.scalar_one_or_none()
            if not section:
                raise NotFoundException(f"الشعبة {req.section_id} غير موجودة")
            
            if section.school_id != school_id:
                raise ValidationException("الشعبة لا تنتمي إلى مدرستك")
            
            if not section.is_active:
                raise ValidationException(f"الشعبة {section.name} غير نشطة")
        
        # --- 3. التحقق من وجود الحصة من Academics Routes (إذا تم تحديدها) ---
        if req.period_id:
            result = await self.db.execute(
                select(Period).where(Period.id == req.period_id)
            )
            period = result.scalar_one_or_none()
            if not period:
                raise NotFoundException(f"الحصة {req.period_id} غير موجودة")
            
            if period.school_id != school_id:
                raise ValidationException("الحصة لا تنتمي إلى مدرستك")
            
            if not period.is_active:
                raise ValidationException(f"الحصة {period.name} غير نشطة")
        
        # --- 4. التحقق من وجود سجل سابق ---
        existing = await self.student_att.get_by_student_date(
            req.student_id, 
            req.date, 
            req.period_id
        )
        
        if existing:
            logger.info(f"Updating existing attendance record: {existing.id}")
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
        
        # --- 5. إنشاء سجل جديد ---
        logger.info(f"Creating new attendance record for student: {req.student_id}")
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
    # 2️⃣ تسجيل حضور طلاب (دفعة واحدة مع التحقق الكامل)
    # ============================================================

    async def batch_record(
        self, 
        school_id: str, 
        user_id: str, 
        req: StudentAttendanceBatch
    ) -> Dict[str, Any]:
        """
        تسجيل حضور طلاب دفعة واحدة مع التحقق من:
        - وجود الطلاب (Students Routes)
        - نشاط الطلاب (Students Routes)
        - وجود الشعبة (Academics Routes)
        - وجود الحصة (Academics Routes)
        """
        logger.info(f"Batch recording attendance: section_id={req.section_id}, date={req.date}")
        
        # --- 1. التحقق من وجود الشعبة من Academics Routes ---
        if req.section_id:
            result = await self.db.execute(
                select(Section).where(Section.id == req.section_id)
            )
            section = result.scalar_one_or_none()
            if not section:
                raise NotFoundException(f"الشعبة {req.section_id} غير موجودة")
            
            if section.school_id != school_id:
                raise ValidationException("الشعبة لا تنتمي إلى مدرستك")
            
            if not section.is_active:
                raise ValidationException(f"الشعبة {section.name} غير نشطة")
        
        # --- 2. التحقق من وجود الحصة من Academics Routes ---
        if req.period_id:
            result = await self.db.execute(
                select(Period).where(Period.id == req.period_id)
            )
            period = result.scalar_one_or_none()
            if not period:
                raise NotFoundException(f"الحصة {req.period_id} غير موجودة")
            
            if period.school_id != school_id:
                raise ValidationException("الحصة لا تنتمي إلى مدرستك")
            
            if not period.is_active:
                raise ValidationException(f"الحصة {period.name} غير نشطة")
        
        # --- 3. معالجة كل طالب ---
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
                # --- التحقق من وجود الطالب من Students Routes ---
                result = await self.db.execute(
                    select(Student).where(Student.id == student_id)
                )
                student = result.scalar_one_or_none()
                if not student:
                    errors.append(f"الطالب {student_id} غير موجود")
                    skipped_count += 1
                    continue
                
                if student.school_id != school_id:
                    errors.append(f"الطالب {student.full_name} لا ينتمي إلى مدرستك")
                    skipped_count += 1
                    continue
                
                if not student.is_active:
                    errors.append(f"الطالب {student.full_name} غير نشط")
                    skipped_count += 1
                    continue
                
                # --- التحقق من وجود سجل سابق ---
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
    # 3️⃣ تسجيل حضور معلم (مع التحقق من وجود المعلم)
    # ============================================================

    async def record_teacher(
        self, 
        school_id: str, 
        user_id: str, 
        req: TeacherAttendanceCreate
    ) -> Dict[str, Any]:
        """
        تسجيل حضور معلم مع التحقق من:
        - وجود المعلم
        - نشاط المعلم
        """
        logger.info(f"Recording teacher attendance: teacher_id={req.teacher_id}, date={req.date}")
        
        # --- 1. التحقق من وجود المعلم ---
        result = await self.db.execute(
            select(Teacher).where(Teacher.id == req.teacher_id)
        )
        teacher = result.scalar_one_or_none()
        if not teacher:
            raise NotFoundException(f"المعلم {req.teacher_id} غير موجود")
        
        if teacher.school_id != school_id:
            raise ValidationException("المعلم لا ينتمي إلى مدرستك")
        
        if not teacher.is_active:
            raise ValidationException(f"المعلم {teacher.full_name} غير نشط")
        
        # --- 2. التحقق من وجود سجل سابق ---
        existing = await self.teacher_att.get_by_teacher_date(req.teacher_id, req.date)
        
        if existing:
            logger.info(f"Updating existing teacher attendance record: {existing.id}")
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
        
        # --- 3. إنشاء سجل جديد ---
        logger.info(f"Creating new teacher attendance record: {req.teacher_id}")
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
    # 4️⃣ جلب ملخص حضور الطلاب (مدمج مع Academics)
    # ============================================================

    async def student_summary(
        self, 
        school_id: str, 
        date: str,
        section_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        جلب ملخص حضور الطلاب مع تفاصيل من Academics Routes.
        """
        # --- جلب الملخص الأساسي ---
        summary = await self.student_att.summary(school_id, date)
        
        if not summary:
            return {
                "total": 0,
                "present": 0,
                "absent": 0,
                "late": 0,
                "excused": 0,
                "percentage": 0,
                "section_id": section_id,
                "date": date,
            }
        
        # --- جلب إجمالي عدد الطلاب من Students Routes ---
        stmt = select(func.count()).select_from(Student).where(
            Student.school_id == school_id,
            Student.is_active == True
        )
        if section_id:
            stmt = stmt.where(Student.section_id == section_id)
        
        total_students = (await self.db.execute(stmt)).scalar() or 0
        
        # --- حساب النسبة المئوية ---
        present = summary.get("present", 0)
        percentage = round((present / total_students) * 100, 2) if total_students > 0 else 0
        
        return {
            **summary,
            "total": total_students,
            "percentage": percentage,
            "section_id": section_id,
            "date": date,
        }

    # ============================================================
    # 5️⃣ جلب المعلمين الغائبين (مع تفاصيل من Teacher)
    # ============================================================

    async def absent_teachers(
        self, 
        school_id: str, 
        date: str
    ) -> List[Dict[str, Any]]:
        """
        جلب المعلمين الغائبين مع تفاصيلهم.
        """
        records = await self.teacher_att.absent_teachers(school_id, date)
        
        result = []
        for r in records:
            # جلب تفاصيل المعلم
            res = await self.db.execute(
                select(Teacher).where(Teacher.id == r.teacher_id)
            )
            teacher = res.scalar_one_or_none()
            if teacher:
                result.append({
                    "teacher_id": r.teacher_id,
                    "teacher_name": teacher.full_name,
                    "teacher_number": teacher.teacher_number,
                    "email": teacher.email,
                    "phone": teacher.phone,
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
    # 6️⃣ جلب حضور شعبة مع تفاصيل الطلاب (مدمج مع Students)
    # ============================================================

    async def section_attendance(
        self, 
        section_id: str, 
        date: str,
        period_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        جلب حضور شعبة مع تفاصيل الطلاب من Students Routes.
        """
        # --- جلب سجلات الحضور ---
        records = await self.student_att.list_by_section_date(
            section_id, 
            date,
            period_id
        )
        
        # --- جلب تفاصيل الطلاب ---
        result = []
        for r in records:
            res = await self.db.execute(
                select(Student).where(Student.id == r.student_id)
            )
            student = res.scalar_one_or_none()
            if student:
                result.append({
                    "student_id": r.student_id,
                    "student_number": student.student_number,
                    "student_name": student.full_name,
                    "status": r.status,
                    "note": r.note,
                    "date": r.date,
                    "section_id": r.section_id,
                    "period_id": r.period_id,
                    "recorded_by": r.recorded_by,
                })
            else:
                result.append({
                    "student_id": r.student_id,
                    "student_name": "غير معروف",
                    "status": r.status,
                    "note": r.note,
                    "date": r.date,
                })
        
        return result
