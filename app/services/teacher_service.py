"""Teacher service with assignment logic."""
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import ConflictException, NotFoundException
from app.core.security import hash_password
from app.models.users import User
from app.models.teachers import Teacher
from app.repositories.teachers import AssignmentRepository, TeacherRepository
from app.repositories.users import RoleRepository, UserRoleRepository, UserRepository
from app.schemas.teachers import AssignmentCreate, TeacherCreate, TeacherUpdate


class TeacherService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.teachers = TeacherRepository(db)
        self.assignments = AssignmentRepository(db)
        self.users = UserRepository(db)
        self.roles = RoleRepository(db)
        self.user_roles = UserRoleRepository(db)

    async def create_teacher(self, school_id: str, req: TeacherCreate) -> dict:
        existing = await self.teachers.get_by_number(school_id, req.employee_number)
        if existing:
            raise ConflictException("رقم الموظف مستخدم بالفعل")
        user_id = None
        if req.create_user and req.user_email and req.user_password:
            existing_user = await self.users.get_by_email(req.user_email)
            if existing_user:
                raise ConflictException("البريد الإلكتروني مستخدم بالفعل")
            user = await self.users.create(
                email=req.user_email,
                password_hash=hash_password(req.user_password),
                full_name=f"{req.first_name} {req.last_name}",
                school_id=school_id,
                is_active=True,
            )
            user_id = user.id
            teacher_role = await self.roles.get_by_key(school_id, "teacher")
            if teacher_role:
                await self.user_roles.assign(user.id, teacher_role.id)

        teacher = await self.teachers.create(
            school_id=school_id,
            user_id=user_id,
            employee_number=req.employee_number,
            national_id=req.national_id,
            first_name=req.first_name,
            last_name=req.last_name,
            gender=req.gender,
            phone=req.phone,
            email=req.email,
            specialization=req.specialization,
            qualification=req.qualification,
            hire_date=req.hire_date,
            is_active=True,
        )
        return {"id": teacher.id, "full_name": f"{teacher.first_name} {teacher.last_name}"}

    async def update_teacher(self, teacher_id: str, req: TeacherUpdate) -> dict:
        teacher = await self.teachers.get(teacher_id)
        if not teacher:
            raise NotFoundException("المعلم غير موجود")
        teacher = await self.teachers.update(teacher, **req.model_dump(exclude_unset=True))
        return {"id": teacher.id}

    # ✅ تحديث الدالة: إضافة معامل is_active مع قيمة افتراضية
    async def list_teachers(
        self, 
        school_id: str, 
        page: int = 1, 
        page_size: int = 20, 
        search: str | None = None,
        is_active: bool = True,  # ✅ إضافة المعامل الجديد
    ) -> dict:
        """جلب قائمة المعلمين مع إمكانية التصفية حسب الحالة."""
        items, total = await self.teachers.list_by_school(
            school_id, 
            page, 
            page_size, 
            search,
            is_active=is_active,  # ✅ تمرير المعامل إلى المستودع
        )
        return {
            "items": [
                {
                    "id": t.id,
                    "employee_number": t.employee_number,
                    "full_name": f"{t.first_name} {t.last_name}",
                    "specialization": t.specialization,
                    "phone": t.phone,
                    "is_active": t.is_active,
                }
                for t in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ✅ إضافة دالة جديدة لجلب المعلمين كـ List (للاستخدام في Attendance)
    async def get_teachers_list(
        self, 
        school_id: str, 
        is_active: bool = True,
    ) -> List[Teacher]:
        """جلب قائمة المعلمين كـ List (للاستخدام في Attendance)."""
        from sqlalchemy import select
        
        result = await self.db.execute(
            select(Teacher).where(
                Teacher.school_id == school_id,
                Teacher.is_active == is_active
            ).order_by(Teacher.first_name)
        )
        return list(result.scalars().all())

    async def get_teacher_detail(self, teacher_id: str) -> dict:
        teacher = await self.teachers.get(teacher_id)
        if not teacher:
            raise NotFoundException("المعلم غير موجود")
        assignments = await self.assignments.list_by_teacher(teacher_id)
        return {
            "id": teacher.id,
            "employee_number": teacher.employee_number,
            "first_name": teacher.first_name,
            "last_name": teacher.last_name,
            "full_name": f"{teacher.first_name} {teacher.last_name}",
            "national_id": teacher.national_id,
            "gender": teacher.gender,
            "phone": teacher.phone,
            "email": teacher.email,
            "specialization": teacher.specialization,
            "qualification": teacher.qualification,
            "hire_date": teacher.hire_date,
            "is_active": teacher.is_active,
            "assignments": [
                {"id": a.id, "subject_id": a.subject_id, "section_id": a.section_id, "status": a.status}
                for a in assignments
            ],
        }

    async def assign_teacher(self, req: AssignmentCreate) -> dict:
        existing = await self.assignments.get_existing(req.teacher_id, req.subject_id, req.section_id, req.year_id)
        if existing and existing.status == "active":
            raise ConflictException("التكليف موجود بالفعل")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assignment = await self.assignments.create(
            teacher_id=req.teacher_id,
            school_id=(await self.teachers.get(req.teacher_id)).school_id if await self.teachers.get(req.teacher_id) else "",
            subject_id=req.subject_id,
            section_id=req.section_id,
            year_id=req.year_id,
            status="active",
            assigned_at=now,
        )
        return {"id": assignment.id}
