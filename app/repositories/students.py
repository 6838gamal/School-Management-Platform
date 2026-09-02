"""Student repositories."""
from typing import List, Optional, Tuple
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

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

    async def get_by_student_number(self, student_number: str, school_id: Optional[str] = None) -> Optional[Student]:
        """جلب طالب برقم الطالب."""
        stmt = select(Student).where(Student.student_number == student_number)
        if school_id:
            stmt = stmt.where(Student.school_id == school_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_national_id(self, national_id: str, school_id: Optional[str] = None) -> Optional[Student]:
        """جلب طالب بالرقم الوطني."""
        stmt = select(Student).where(Student.national_id == national_id)
        if school_id:
            stmt = stmt.where(Student.school_id == school_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_school(
        self, 
        school_id: str, 
        page: int = 1, 
        page_size: int = 20, 
        search: Optional[str] = None,
        year_id: Optional[str] = None,
        grade_id: Optional[str] = None,
        section_id: Optional[str] = None,
    ) -> Tuple[List[Student], int]:
        """جلب قائمة الطلاب في مدرسة مع البحث والترقيم والتصفية."""
        stmt = select(Student).where(Student.school_id == school_id)
        count_stmt = select(func.count()).select_from(Student).where(Student.school_id == school_id)
        
        # البحث
        if search:
            like = f"%{search}%"
            search_condition = or_(
                Student.first_name.ilike(like),
                Student.last_name.ilike(like),
                Student.student_number.ilike(like),
                Student.national_id.ilike(like),
            )
            stmt = stmt.where(search_condition)
            count_stmt = count_stmt.where(search_condition)
        
        # ✅ تصفية حسب السنة
        if year_id:
            stmt = stmt.where(Student.year_id == year_id)
            count_stmt = count_stmt.where(Student.year_id == year_id)
        
        # ✅ تصفية حسب الصف
        if grade_id:
            stmt = stmt.where(Student.grade_id == grade_id)
            count_stmt = count_stmt.where(Student.grade_id == grade_id)
        
        # ✅ تصفية حسب الشعبة
        if section_id:
            stmt = stmt.where(Student.section_id == section_id)
            count_stmt = count_stmt.where(Student.section_id == section_id)
        
        total = (await self.db.execute(count_stmt)).scalar() or 0
        offset = (page - 1) * page_size
        result = await self.db.execute(
            stmt.order_by(Student.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def list_by_section(
        self, 
        school_id: str, 
        section_id: str, 
        is_active: bool = True,
        year_id: Optional[str] = None,
    ) -> List[Student]:
        """✅ جلب الطلاب حسب الشعبة مباشرة من جدول Student."""
        stmt = select(Student).where(
            Student.school_id == school_id,
            Student.section_id == section_id,
            Student.is_active == is_active
        )
        
        if year_id:
            stmt = stmt.where(Student.year_id == year_id)
        
        result = await self.db.execute(stmt.order_by(Student.first_name, Student.last_name))
        return list(result.scalars().all())

    async def list_by_grade(
        self, 
        school_id: str, 
        grade_id: str, 
        is_active: bool = True,
        year_id: Optional[str] = None,
    ) -> List[Student]:
        """✅ جلب الطلاب حسب الصف مباشرة من جدول Student."""
        stmt = select(Student).where(
            Student.school_id == school_id,
            Student.grade_id == grade_id,
            Student.is_active == is_active
        )
        
        if year_id:
            stmt = stmt.where(Student.year_id == year_id)
        
        result = await self.db.execute(stmt.order_by(Student.first_name, Student.last_name))
        return list(result.scalars().all())

    async def list_by_year(
        self, 
        school_id: str, 
        year_id: str, 
        is_active: bool = True,
    ) -> List[Student]:
        """✅ جلب الطلاب حسب السنة الدراسية مباشرة من جدول Student."""
        stmt = select(Student).where(
            Student.school_id == school_id,
            Student.year_id == year_id,
            Student.is_active == is_active
        )
        result = await self.db.execute(stmt.order_by(Student.first_name, Student.last_name))
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
        year_id: Optional[str] = None,
        grade_id: Optional[str] = None,
        section_id: Optional[str] = None,
        
        created_by: Optional[str] = None,
        first_name_ar: Optional[str] = None,
        last_name_ar: Optional[str] = None,
        nationality: Optional[str] = None,
        guardian_relation: Optional[str] = None,
        phone: Optional[str] = None,
        photo_url: Optional[str] = None,
    ) -> Student:
        """✅ إنشاء طالب جديد مع جميع الحقول."""
        student = Student(
            school_id=school_id,
            student_number=student_number,
            national_id=national_id,
            first_name=first_name,
            last_name=last_name,
            first_name_ar=first_name_ar,
            last_name_ar=last_name_ar,
            gender=gender,
            birth_date=birth_date,
            nationality=nationality,
            guardian_name=guardian_name,
            guardian_phone=guardian_phone,
            guardian_email=guardian_email,
            guardian_relation=guardian_relation,
            phone=phone,
            address=address,
            photo_url=photo_url,
            # ✅ الحقول الأكاديمية الجديدة
            year_id=year_id,
            grade_id=grade_id,
            section_id=section_id,
        
            is_active=True,
            enrollment_status="active",
        )
        self.db.add(student)
        await self.db.flush()
        await self.db.refresh(student)
        
        # ✅ إذا تم تحديد شعبة، إنشاء تسجيل في StudentEnrollment
        if section_id and year_id:
            enrollment = StudentEnrollment(
                student_id=student.id,
                school_id=school_id,
                academic_year_id=year_id,  # استخدام academic_year_id
                section_id=section_id,
                status="active",
                enrolled_at=datetime.now(timezone.utc).date(),
            )
            self.db.add(enrollment)
            await self.db.flush()
        
        return student

    async def update(self, id: str, data: dict) -> Optional[Student]:
        """✅ تحديث بيانات طالب مع الحقول الأكاديمية."""
        student = await self.get_by_id(id)
        if not student:
            return None
        
        # الحقول المسموح بتحديثها
        allowed_fields = [
            'first_name', 'last_name', 'first_name_ar', 'last_name_ar',
            'national_id', 'gender', 'birth_date', 'nationality',
            'guardian_name', 'guardian_phone', 'guardian_email', 'guardian_relation',
            'phone', 'address', 'photo_url',
            'year_id', 'grade_id', 'section_id', 'period_id',
            'is_active', 'enrollment_status'
        ]
        
        for key, value in data.items():
            if key in allowed_fields and value is not None:
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
        grade_id: Optional[str] = None,
        year_id: Optional[str] = None,
        is_active: Optional[bool] = True,
    ) -> int:
        """✅ حساب عدد الطلاب مع خيارات التصفية."""
        stmt = select(func.count()).select_from(Student).where(
            Student.school_id == school_id
        )
        
        if is_active is not None:
            stmt = stmt.where(Student.is_active == is_active)
        
        if section_id:
            stmt = stmt.where(Student.section_id == section_id)
        
        if grade_id:
            stmt = stmt.where(Student.grade_id == grade_id)
        
        if year_id:
            stmt = stmt.where(Student.year_id == year_id)
        
        return (await self.db.execute(stmt)).scalar() or 0


class EnrollmentRepository(BaseRepository[StudentEnrollment]):
    """مستودع تسجيلات الطلاب."""
    model = StudentEnrollment

    async def get_active(self, student_id: str, academic_year_id: str) -> Optional[StudentEnrollment]:
        """جلب التسجيل النشط لطالب في عام دراسي."""
        result = await self.db.execute(
            select(StudentEnrollment).where(
                StudentEnrollment.student_id == student_id,
                StudentEnrollment.academic_year_id == academic_year_id,
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

    async def list_by_section(self, section_id: str, academic_year_id: str) -> List[StudentEnrollment]:
        """جلب تسجيلات الطلاب حسب الشعبة والعام الدراسي."""
        result = await self.db.execute(
            select(StudentEnrollment).where(
                StudentEnrollment.section_id == section_id,
                StudentEnrollment.academic_year_id == academic_year_id,
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
        academic_year_id: str,
        enrolled_by: Optional[str] = None,
    ) -> StudentEnrollment:
        """إنشاء تسجيل جديد لطالب."""
        enrollment = StudentEnrollment(
            student_id=student_id,
            school_id=school_id,
            section_id=section_id,
            academic_year_id=academic_year_id,
            status="active",
            enrolled_at=datetime.now(timezone.utc).date(),
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
        academic_year_id: str,
        school_id: str,
        performed_by: Optional[str] = None,
    ) -> StudentEnrollment:
        """
        نقل طالب إلى شعبة جديدة.
        
        يتم تعطيل التسجيل الحالي وإنشاء تسجيل جديد.
        """
        # تعطيل التسجيلات النشطة
        await self.deactivate_all(student_id)
        
        # إنشاء تسجيل جديد
        enrollment = StudentEnrollment(
            student_id=student_id,
            school_id=school_id,
            section_id=new_section_id,
            academic_year_id=academic_year_id,
            status="active",
            enrolled_at=datetime.now(timezone.utc).date(),
        )
        self.db.add(enrollment)
        await self.db.flush()
        await self.db.refresh(enrollment)
        return enrollment

    async def get_students_by_section(
        self,
        section_id: str,
        academic_year_id: str,
        is_active: bool = True,
    ) -> List[Student]:
        """✅ جلب الطلاب المسجلين في شعبة معينة."""
        # جلب student_id من StudentEnrollment
        enrollment_stmt = select(StudentEnrollment.student_id).where(
            StudentEnrollment.section_id == section_id,
            StudentEnrollment.academic_year_id == academic_year_id,
            StudentEnrollment.status == "active",
        )
        result = await self.db.execute(enrollment_stmt)
        student_ids = [row[0] for row in result.all()]
        
        if not student_ids:
            return []
        
        # جلب الطلاب من جدول Student
        student_stmt = select(Student).where(
            Student.id.in_(student_ids),
            Student.is_active == is_active
        ).order_by(Student.first_name, Student.last_name)
        
        result = await self.db.execute(student_stmt)
        return list(result.scalars().all())
