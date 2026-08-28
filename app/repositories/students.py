"""Student repositories."""
from typing import List, Optional, Tuple
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.students import Student, StudentEnrollment
from app.repositories.base import BaseRepository


class StudentRepository(BaseRepository[Student]):
    """مستودع الطلاب."""
    model = Student

    async def get_by_id(self, id: str) -> Optional[Student]:
        """جلب طالب بالمعرف."""
        result = await self.db.execute(
            select(Student).where(Student.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_student_number(self, student_number: str) -> Optional[Student]:
        """جلب طالب برقم الطالب."""
        result = await self.db.execute(
            select(Student).where(Student.student_number == student_number)
        )
        return result.scalar_one_or_none()

    async def get_by_national_id(self, national_id: str) -> Optional[Student]:
        """جلب طالب بالرقم الوطني."""
        result = await self.db.execute(
            select(Student).where(Student.national_id == national_id)
        )
        return result.scalar_one_or_none()

    async def list_by_school(
        self, 
        school_id: str, 
        page: int = 1, 
        page_size: int = 20, 
        search: Optional[str] = None
    ) -> Tuple[List[Student], int]:
        """جلب قائمة الطلاب في مدرسة مع البحث والترقيم."""
        stmt = select(Student).where(Student.school_id == school_id)
        count_stmt = select(func.count()).select_from(Student).where(Student.school_id == school_id)
        
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                (Student.first_name.ilike(like)) | 
                (Student.last_name.ilike(like)) | 
                (Student.student_number.ilike(like))
            )
            count_stmt = count_stmt.where(
                (Student.first_name.ilike(like)) | 
                (Student.last_name.ilike(like)) | 
                (Student.student_number.ilike(like))
            )
        
        total = (await self.db.execute(count_stmt)).scalar() or 0
        offset = (page - 1) * page_size
        result = await self.db.execute(
            stmt.order_by(Student.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    # ✅ دالة get_by_section باستخدام StudentEnrollment فقط (بدون علاقات)
    async def get_by_section(
        self, 
        school_id: str, 
        section_id: str, 
        is_active: bool = True,
        year_id: Optional[str] = None,
    ) -> List[Student]:
        """
        جلب الطلاب حسب الشعبة باستخدام StudentEnrollment.
        
        الطريقة: 
        1. نبحث في StudentEnrollment عن section_id المطلوب
        2. نجلب student_id من السجلات
        3. نجلب الطلاب من جدول Student
        """
        # الخطوة 1: جلب student_id من StudentEnrollment
        enrollment_stmt = select(StudentEnrollment.student_id).where(
            StudentEnrollment.section_id == section_id,
            StudentEnrollment.status == "active"
        )
        
        if year_id:
            enrollment_stmt = enrollment_stmt.where(StudentEnrollment.year_id == year_id)
        
        # تنفيذ الاستعلام للحصول على قائمة student_id
        result = await self.db.execute(enrollment_stmt)
        student_ids = [row[0] for row in result.all()]
        
        if not student_ids:
            return []
        
        # الخطوة 2: جلب الطلاب من جدول Student
        student_stmt = select(Student).where(
            Student.school_id == school_id,
            Student.is_active == is_active,
            Student.id.in_(student_ids)
        ).order_by(Student.first_name, Student.last_name)
        
        result = await self.db.execute(student_stmt)
        return list(result.scalars().all())

    async def create(
        self,
        school_id: str,
        student_number: str,
        first_name: str,
        last_name: str,
        national_id: Optional[str] = None,
        gender: Optional[str] = None,
        birth_date: Optional[str] = None,
        guardian_name: Optional[str] = None,
        guardian_phone: Optional[str] = None,
        guardian_email: Optional[str] = None,
        address: Optional[str] = None,
        section_id: Optional[str] = None,
        year_id: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Student:
        """إنشاء طالب جديد."""
        student = Student(
            school_id=school_id,
            student_number=student_number,
            national_id=national_id,
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            birth_date=birth_date,
            guardian_name=guardian_name,
            guardian_phone=guardian_phone,
            guardian_email=guardian_email,
            address=address,
            is_active=True,
        )
        self.db.add(student)
        await self.db.flush()
        await self.db.refresh(student)
        
        # إذا تم تحديد شعبة، إنشاء تسجيل في StudentEnrollment
        if section_id and year_id:
            from datetime import datetime
            enrollment = StudentEnrollment(
                student_id=student.id,
                school_id=school_id,
                year_id=year_id,
                section_id=section_id,
                status="active",
                enrolled_at=datetime.now(timezone.utc).isoformat(),
            )
            self.db.add(enrollment)
            await self.db.flush()
        
        return student

    async def update(self, id: str, data: dict) -> Optional[Student]:
        """تحديث بيانات طالب."""
        student = await self.get_by_id(id)
        if not student:
            return None
        
        for key, value in data.items():
            if hasattr(student, key) and value is not None:
                setattr(student, key, value)
        
        await self.db.flush()
        await self.db.refresh(student)
        return student

    async def delete(self, id: str) -> bool:
        """حذف طالب (تعطيل فقط)."""
        student = await self.get_by_id(id)
        if not student:
            return False
        
        student.is_active = False
        await self.db.flush()
        return True

    async def count(
        self,
        school_id: str,
        section_id: Optional[str] = None,
        is_active: Optional[bool] = True,
        year_id: Optional[str] = None,
    ) -> int:
        """حساب عدد الطلاب."""
        stmt = select(func.count()).select_from(Student).where(
            Student.school_id == school_id,
            Student.is_active == is_active if is_active is not None else True
        )
        
        # إذا تم تحديد الشعبة، نستخدم StudentEnrollment
        if section_id:
            # جلب student_id من StudentEnrollment
            enrollment_stmt = select(StudentEnrollment.student_id).where(
                StudentEnrollment.section_id == section_id,
                StudentEnrollment.status == "active"
            )
            if year_id:
                enrollment_stmt = enrollment_stmt.where(StudentEnrollment.year_id == year_id)
            
            result = await self.db.execute(enrollment_stmt)
            student_ids = [row[0] for row in result.all()]
            
            if not student_ids:
                return 0
            
            stmt = stmt.where(Student.id.in_(student_ids))
        
        return (await self.db.execute(stmt)).scalar() or 0


class EnrollmentRepository(BaseRepository[StudentEnrollment]):
    """مستودع تسجيلات الطلاب."""
    model = StudentEnrollment

    async def get_active(self, student_id: str, year_id: str) -> Optional[StudentEnrollment]:
        """جلب التسجيل النشط لطالب في عام دراسي."""
        result = await self.db.execute(
            select(StudentEnrollment).where(
                StudentEnrollment.student_id == student_id,
                StudentEnrollment.year_id == year_id,
                StudentEnrollment.status == "active",
            )
        )
        return result.scalar_one_or_none()

    async def get_active_by_student(self, student_id: str) -> Optional[StudentEnrollment]:
        """جلب التسجيل النشط لطالب (أحدث تسجيل)."""
        result = await self.db.execute(
            select(StudentEnrollment)
            .where(
                StudentEnrollment.student_id == student_id,
                StudentEnrollment.status == "active",
            )
            .order_by(StudentEnrollment.enrolled_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_section(self, section_id: str, year_id: str) -> List[StudentEnrollment]:
        """جلب تسجيلات الطلاب حسب الشعبة والعام الدراسي."""
        result = await self.db.execute(
            select(StudentEnrollment).where(
                StudentEnrollment.section_id == section_id,
                StudentEnrollment.year_id == year_id,
                StudentEnrollment.status == "active",
            )
        )
        return list(result.scalars().all())

    async def list_by_student(self, student_id: str) -> List[StudentEnrollment]:
        """جلب جميع تسجيلات طالب."""
        result = await self.db.execute(
            select(StudentEnrollment)
            .where(StudentEnrollment.student_id == student_id)
            .order_by(StudentEnrollment.enrolled_at.desc())
        )
        return list(result.scalars().all())

    async def create_enrollment(
        self,
        student_id: str,
        school_id: str,
        section_id: str,
        year_id: str,
        enrolled_by: Optional[str] = None,
    ) -> StudentEnrollment:
        """إنشاء تسجيل جديد لطالب."""
        from datetime import datetime
        
        enrollment = StudentEnrollment(
            student_id=student_id,
            school_id=school_id,
            section_id=section_id,
            year_id=year_id,
            status="active",
            enrolled_at=datetime.now(timezone.utc).isoformat(),
        )
        self.db.add(enrollment)
        await self.db.flush()
        await self.db.refresh(enrollment)
        return enrollment

    async def deactivate_all(self, student_id: str) -> None:
        """تعطيل جميع تسجيلات الطالب."""
        enrollments = await self.list_by_student(student_id)
        for enrollment in enrollments:
            if enrollment.status == "active":
                enrollment.status = "inactive"
        await self.db.flush()

    async def transfer(
        self,
        student_id: str,
        new_section_id: str,
        year_id: str,
        performed_by: Optional[str] = None,
    ) -> StudentEnrollment:
        """
        نقل طالب إلى شعبة جديدة.
        
        يتم تعطيل التسجيل الحالي وإنشاء تسجيل جديد.
        """
        from datetime import datetime
        
        # تعطيل التسجيلات النشطة
        await self.deactivate_all(student_id)
        
        # إنشاء تسجيل جديد
        enrollment = StudentEnrollment(
            student_id=student_id,
            school_id=student_id,  # سيتم استبداله بـ school_id الفعلي
            section_id=new_section_id,
            year_id=year_id,
            status="active",
            enrolled_at=datetime.now(timezone.utc).isoformat(),
        )
        self.db.add(enrollment)
        await self.db.flush()
        await self.db.refresh(enrollment)
        return enrollment
