"""Teacher repositories."""
from typing import Optional, List, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.teachers import Teacher, TeacherAssignment
from app.repositories.base import BaseRepository


class TeacherRepository(BaseRepository[Teacher]):
    model = Teacher

    # ✅ تحديث الدالة: إضافة معامل is_active
    async def list_by_school(
        self, 
        school_id: str, 
        page: int = 1, 
        page_size: int = 20, 
        search: str | None = None,
        is_active: bool = True,  # ✅ إضافة المعامل الجديد
    ) -> Tuple[List[Teacher], int]:
        """
        جلب قائمة المعلمين في مدرسة مع البحث والترقيم.
        
        Args:
            school_id: معرف المدرسة
            page: رقم الصفحة
            page_size: عدد العناصر في الصفحة
            search: كلمة البحث (اختياري)
            is_active: حالة المعلم (True = نشط, False = غير نشط)
        
        Returns:
            Tuple[List[Teacher], int]: قائمة المعلمين والعدد الإجمالي
        """
        stmt = select(Teacher).where(
            Teacher.school_id == school_id,
            Teacher.is_active == is_active  # ✅ تصفية حسب الحالة
        )
        count_stmt = select(func.count()).select_from(Teacher).where(
            Teacher.school_id == school_id,
            Teacher.is_active == is_active
        )
        
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                (Teacher.first_name.ilike(like)) | 
                (Teacher.last_name.ilike(like)) | 
                (Teacher.employee_number.ilike(like)) |
                (Teacher.email.ilike(like)) |
                (Teacher.specialization.ilike(like))
            )
            count_stmt = count_stmt.where(
                (Teacher.first_name.ilike(like)) | 
                (Teacher.last_name.ilike(like)) | 
                (Teacher.employee_number.ilike(like)) |
                (Teacher.email.ilike(like)) |
                (Teacher.specialization.ilike(like))
            )
        
        total = (await self.db.execute(count_stmt)).scalar() or 0
        offset = (page - 1) * page_size
        result = await self.db.execute(
            stmt.order_by(Teacher.first_name)
            .offset(offset)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_by_number(self, school_id: str, number: str) -> Teacher | None:
        """جلب معلم برقم الموظف."""
        result = await self.db.execute(
            select(Teacher).where(
                Teacher.school_id == school_id, 
                Teacher.employee_number == number
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: str) -> Teacher | None:
        """جلب معلم بواسطة معرف المستخدم."""
        result = await self.db.execute(
            select(Teacher).where(Teacher.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, teacher_id: str) -> Teacher | None:
        """جلب معلم بالمعرف."""
        result = await self.db.execute(
            select(Teacher).where(Teacher.id == teacher_id)
        )
        return result.scalar_one_or_none()

    # ✅ إضافة دالة جديدة لجلب المعلمين النشطين فقط
    async def list_active_teachers(
        self, 
        school_id: str,
    ) -> List[Teacher]:
        """جلب قائمة المعلمين النشطين فقط."""
        result = await self.db.execute(
            select(Teacher).where(
                Teacher.school_id == school_id,
                Teacher.is_active == True
            ).order_by(Teacher.first_name)
        )
        return list(result.scalars().all())


class AssignmentRepository(BaseRepository[TeacherAssignment]):
    model = TeacherAssignment

    async def list_by_teacher(
        self, 
        teacher_id: str, 
        year_id: str | None = None
    ) -> List[TeacherAssignment]:
        """جلب تكليفات معلم."""
        stmt = select(TeacherAssignment).where(
            TeacherAssignment.teacher_id == teacher_id,
            TeacherAssignment.status == "active"
        )
        if year_id:
            stmt = stmt.where(TeacherAssignment.year_id == year_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_section(
        self, 
        section_id: str, 
        year_id: str
    ) -> List[TeacherAssignment]:
        """جلب تكليفات حسب الشعبة والعام الدراسي."""
        result = await self.db.execute(
            select(TeacherAssignment).where(
                TeacherAssignment.section_id == section_id,
                TeacherAssignment.year_id == year_id,
                TeacherAssignment.status == "active",
            )
        )
        return list(result.scalars().all())

    async def get_existing(
        self, 
        teacher_id: str, 
        subject_id: str, 
        section_id: str, 
        year_id: str
    ) -> TeacherAssignment | None:
        """جلب تكليف موجود."""
        result = await self.db.execute(
            select(TeacherAssignment).where(
                TeacherAssignment.teacher_id == teacher_id,
                TeacherAssignment.subject_id == subject_id,
                TeacherAssignment.section_id == section_id,
                TeacherAssignment.year_id == year_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        teacher_id: str,
        school_id: str,
        subject_id: str,
        section_id: str,
        year_id: str,
        status: str = "active",
        assigned_at: Optional[str] = None,
    ) -> TeacherAssignment:
        """إنشاء تكليف جديد."""
        from datetime import datetime
        if not assigned_at:
            assigned_at = datetime.now().isoformat()
        
        assignment = TeacherAssignment(
            teacher_id=teacher_id,
            school_id=school_id,
            subject_id=subject_id,
            section_id=section_id,
            year_id=year_id,
            status=status,
            assigned_at=assigned_at,
        )
        self.db.add(assignment)
        await self.db.flush()
        await self.db.refresh(assignment)
        return assignment
