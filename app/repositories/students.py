"""Student repositories."""
from typing import List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.students import Student, StudentEnrollment
from app.repositories.base import BaseRepository


class StudentRepository(BaseRepository[Student]):
    """مستودع الطلاب."""
    model = Student

    async def list_by_school(
        self, 
        school_id: str, 
        page: int = 1, 
        page_size: int = 20, 
        search: str | None = None
    ) -> Tuple[List[Student], int]:
        """جلب قائمة الطلاب في مدرسة مع البحث والترقيم."""
        stmt = select(Student).where(Student.school_id == school_id)
        count_stmt = select(Student).where(Student.school_id == school_id)
        
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
        
        total = (await self.db.execute(select(func.count()).select_from(count_stmt))).scalar() or 0
        offset = (page - 1) * page_size
        result = await self.db.execute(
            stmt.order_by(Student.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_by_number(self, school_id: str, number: str) -> Student | None:
        """جلب طالب برقم الطالب."""
        result = await self.db.execute(
            select(Student).where(
                Student.school_id == school_id, 
                Student.student_number == number
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, id: str) -> Student | None:
        """جلب طالب بالمعرف."""
        result = await self.db.execute(
            select(Student).where(Student.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_national_id(self, national_id: str) -> Student | None:
        """جلب طالب بالرقم الوطني."""
        result = await self.db.execute(
            select(Student).where(Student.national_id == national_id)
        )
        return result.scalar_one_or_none()

    # ✅ دالة get_by_section يجب أن تكون هنا في StudentRepository
    async def get_by_section(
        self, 
        school_id: str, 
        section_id: str, 
        is_active: bool = True
    ) -> List[Student]:
        """جلب الطلاب حسب الشعبة."""
        result = await self.db.execute(
            select(Student)
            .where(
                Student.school_id == school_id,
                Student.section_id == section_id,
                Student.is_active == is_active
            )
            .order_by(Student.first_name, Student.last_name)
        )
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
            section_id=section_id,
            year_id=year_id,
            created_by=created_by,
            is_active=True,
        )
        self.db.add(student)
        await self.db.flush()
        await self.db.refresh(student)
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
    ) -> int:
        """حساب عدد الطلاب."""
        stmt = select(func.count()).select_from(Student).where(Student.school_id == school_id)
        
        if is_active is not None:
            stmt = stmt.where(Student.is_active == is_active)
        
        if section_id:
            stmt = stmt.where(Student.section_id == section_id)
        
        return (await self.db.execute(stmt)).scalar() or 0


class EnrollmentRepository(BaseRepository[StudentEnrollment]):
    """مستودع تسجيلات الطلاب."""
    model = StudentEnrollment

    async def get_active(self, student_id: str, year_id: str) -> StudentEnrollment | None:
        """جلب التسجيل النشط لطالب في عام دراسي."""
        result = await self.db.execute(
            select(StudentEnrollment).where(
                StudentEnrollment.student_id == student_id,
                StudentEnrollment.year_id == year_id,
                StudentEnrollment.status == "active",
            )
        )
        return result.scalar_one_or_none()

    async def list_by_section(self, section_id: str, year_id: str) -> list[StudentEnrollment]:
        """جلب تسجيلات الطلاب حسب الشعبة والعام الدراسي."""
        result = await self.db.execute(
            select(StudentEnrollment).where(
                StudentEnrollment.section_id == section_id,
                StudentEnrollment.year_id == year_id,
                StudentEnrollment.status == "active",
            )
        )
        return list(result.scalars().all())

    async def list_by_student(self, student_id: str) -> list[StudentEnrollment]:
        """جلب جميع تسجيلات طالب."""
        result = await self.db.execute(
            select(StudentEnrollment)
            .where(StudentEnrollment.student_id == student_id)
            .order_by(StudentEnrollment.enrolled_at.desc())
        )
        return list(result.scalars().all())
