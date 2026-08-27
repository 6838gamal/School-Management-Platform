from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.models.students import Student, Enrollment
from app.schemas.students import StudentCreate, StudentUpdate
from app.core.exceptions import NotFoundError, ValidationError


class StudentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_students(self, school_id: str, page: int, page_size: int, search: Optional[str] = None) -> Dict[str, Any]:
        query = select(Student).where(
            Student.school_id == school_id,
            Student.is_active == True
        )
        count_query = select(func.count()).select_from(Student).where(
            Student.school_id == school_id,
            Student.is_active == True
        )
        
        if search:
            search_filter = or_(
                Student.first_name.ilike(f"%{search}%"),
                Student.last_name.ilike(f"%{search}%"),
                Student.student_number.ilike(f"%{search}%"),
                Student.national_id.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        students = result.scalars().all()
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        return {"items": students, "total": total}

    async def get_student_detail(self, student_id: str) -> Dict[str, Any]:
        query = select(Student).where(Student.id == student_id).options(
            selectinload(Student.enrollments)
        )
        result = await self.db.execute(query)
        student = result.scalar_one_or_none()
        
        if not student:
            raise NotFoundError("الطالب غير موجود")
        
        # تحويل إلى قاموس مع معلومات إضافية
        detail = {
            "id": student.id,
            "school_id": student.school_id,
            "student_number": student.student_number,
            "national_id": student.national_id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "full_name": student.full_name,
            "gender": student.gender,
            "birth_date": student.birth_date,
            "guardian_name": student.guardian_name,
            "guardian_phone": student.guardian_phone,
            "guardian_email": student.guardian_email,
            "address": student.address,
            "photo_url": student.photo_url,
            "is_active": student.is_active,
            "created_at": student.created_at.isoformat() if student.created_at else None,
            "updated_at": student.updated_at.isoformat() if student.updated_at else None,
            "enrollments": []
        }
        
        # إضافة معلومات التسجيل
        for enrollment in student.enrollments:
            enrollment_data = {
                "id": enrollment.id,
                "student_id": enrollment.student_id,
                "year_id": enrollment.year_id,
                "section_id": enrollment.section_id,
                "status": enrollment.status,
                "enrolled_at": enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None,
                "ended_at": enrollment.ended_at.isoformat() if enrollment.ended_at else None,
                "year_name": enrollment.year.name if enrollment.year else None,
                "section_name": enrollment.section.name if enrollment.section else None,
            }
            detail["enrollments"].append(enrollment_data)
        
        # إضافة year_id و section_id من أحدث تسجيل نشط
        active_enrollment = next(
            (e for e in student.enrollments if e.status == "active"), 
            student.enrollments[-1] if student.enrollments else None
        )
        if active_enrollment:
            detail["year_id"] = active_enrollment.year_id
            detail["section_id"] = active_enrollment.section_id
            detail["year_name"] = active_enrollment.year.name if active_enrollment.year else None
            detail["section_name"] = active_enrollment.section.name if active_enrollment.section else None
        
        return detail

    async def get_student(self, student_id: str) -> Optional[Student]:
        result = await self.db.execute(select(Student).where(Student.id == student_id))
        return result.scalar_one_or_none()

    async def create_student(self, data: StudentCreate, user_id: str, school_id: str) -> Student:
        # التحقق من عدم تكرار رقم الطالب
        existing = await self.db.execute(
            select(Student).where(
                Student.school_id == school_id,
                Student.student_number == data.student_number
            )
        )
        if existing.scalar_one_or_none():
            raise ValidationError("رقم الطالب موجود بالفعل")
        
        # التحقق من عدم تكرار الرقم الوطني
        if data.national_id:
            existing = await self.db.execute(
                select(Student).where(
                    Student.school_id == school_id,
                    Student.national_id == data.national_id
                )
            )
            if existing.scalar_one_or_none():
                raise ValidationError("الرقم الوطني موجود بالفعل")
        
        student = Student(
            school_id=school_id,
            student_number=data.student_number,
            national_id=data.national_id,
            first_name=data.first_name,
            last_name=data.last_name,
            gender=data.gender,
            birth_date=data.birth_date,
            guardian_name=data.guardian_name,
            guardian_phone=data.guardian_phone,
            guardian_email=data.guardian_email,
            address=data.address,
            is_active=True,
            created_by=user_id,
            updated_by=user_id
        )
        
        self.db.add(student)
        await self.db.flush()  # للحصول على ID
        
        # إنشاء تسجيل إذا تم تحديد year_id
        if data.year_id:
            enrollment = Enrollment(
                student_id=student.id,
                year_id=data.year_id,
                section_id=data.section_id,
                status="active",
                enrolled_at=func.now(),
                created_by=user_id,
                updated_by=user_id
            )
            self.db.add(enrollment)
        
        await self.db.commit()
        await self.db.refresh(student)
        return student

    async def update_student(self, student_id: str, data: StudentUpdate) -> Student:
        student = await self.get_student(student_id)
        if not student:
            raise NotFoundError("الطالب غير موجود")
        
        update_data = data.model_dump(exclude_unset=True)
        
        # التحقق من عدم تكرار الرقم الوطني (إذا تم تغييره)
        if "national_id" in update_data and update_data["national_id"]:
            existing = await self.db.execute(
                select(Student).where(
                    Student.school_id == student.school_id,
                    Student.national_id == update_data["national_id"],
                    Student.id != student_id
                )
            )
            if existing.scalar_one_or_none():
                raise ValidationError("الرقم الوطني موجود بالفعل")
        
        for key, value in update_data.items():
            setattr(student, key, value)
        
        await self.db.commit()
        await self.db.refresh(student)
        return student

    async def delete_student(self, student_id: str) -> None:
        student = await self.get_student(student_id)
        if not student:
            raise NotFoundError("الطالب غير موجود")
        
        # حذف سجلات التسجيل المرتبطة
        enrollments = await self.db.execute(
            select(Enrollment).where(Enrollment.student_id == student_id)
        )
        for enrollment in enrollments.scalars().all():
            await self.db.delete(enrollment)
        
        await self.db.delete(student)
        await self.db.commit()
