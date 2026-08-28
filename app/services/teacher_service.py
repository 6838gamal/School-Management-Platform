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
    """خدمة إدارة المعلمين المتكاملة."""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.teachers = TeacherRepository(db)
        self.assignments = AssignmentRepository(db)
        self.users = UserRepository(db)
        self.roles = RoleRepository(db)
        self.user_roles = UserRoleRepository(db)

    # ============================================================
    # 1️⃣ إنشاء معلم جديد
    # ============================================================

    async def create_teacher(self, school_id: str, req: TeacherCreate) -> dict:
        """
        إنشاء معلم جديد مع إمكانية إنشاء حساب مستخدم مرتبط.
        """
        # التحقق من عدم تكرار رقم الموظف
        existing = await self.teachers.get_by_number(school_id, req.employee_number)
        if existing:
            raise ConflictException("رقم الموظف مستخدم بالفعل")
        
        user_id = None
        
        # إنشاء حساب مستخدم إذا طلب ذلك
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
            
            # تعيين دور "معلم" للمستخدم
            teacher_role = await self.roles.get_by_key(school_id, "teacher")
            if teacher_role:
                await self.user_roles.assign(user.id, teacher_role.id)

        # إنشاء سجل المعلم
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
        
        return {
            "id": teacher.id,
            "full_name": f"{teacher.first_name} {teacher.last_name}",
            "user_id": user_id,
        }

    # ============================================================
    # 2️⃣ تحديث بيانات معلم
    # ============================================================

    async def update_teacher(self, teacher_id: str, req: TeacherUpdate) -> dict:
        """
        تحديث بيانات معلم.
        """
        teacher = await self.teachers.get_by_id(teacher_id)
        if not teacher:
            raise NotFoundException("المعلم غير موجود")
        
        teacher = await self.teachers.update(teacher, **req.model_dump(exclude_unset=True))
        return {"id": teacher.id}

    # ============================================================
    # 3️⃣ جلب قائمة المعلمين (مع Pagination)
    # ============================================================

    async def list_teachers(
        self, 
        school_id: str, 
        page: int = 1, 
        page_size: int = 20, 
        search: str | None = None,
        is_active: bool = True,
    ) -> dict:
        """
        جلب قائمة المعلمين مع إمكانية التصفية والبحث والترقيم.
        
        Args:
            school_id: معرف المدرسة
            page: رقم الصفحة
            page_size: عدد العناصر في الصفحة
            search: كلمة البحث (اختياري)
            is_active: حالة المعلم (True = نشط, False = غير نشط)
        
        Returns:
            dict: قائمة المعلمين مع معلومات الترقيم
        """
        items, total = await self.teachers.list_by_school(
            school_id, 
            page, 
            page_size, 
            search,
            is_active=is_active,
        )
        
        return {
            "items": [
                {
                    "id": t.id,
                    "employee_number": t.employee_number,
                    "full_name": f"{t.first_name} {t.last_name}",
                    "specialization": t.specialization,
                    "phone": t.phone,
                    "email": t.email,
                    "is_active": t.is_active,
                }
                for t in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }

    # ============================================================
    # 4️⃣ جلب قائمة المعلمين كـ List (للاستخدام في Attendance)
    # ============================================================

    async def get_teachers_list(
        self, 
        school_id: str, 
        is_active: bool = True,
    ) -> List[Teacher]:
        """
        جلب قائمة المعلمين كـ List (للاستخدام في Attendance و Web Routes).
        
        Args:
            school_id: معرف المدرسة
            is_active: حالة المعلم (True = نشط, False = غير نشط)
        
        Returns:
            List[Teacher]: قائمة المعلمين
        """
        # استخدام الدالة المباشرة من المستودع
        if is_active:
            return await self.teachers.list_active_teachers(school_id)
        else:
            items, _ = await self.teachers.list_by_school(
                school_id, 
                page=1, 
                page_size=1000, 
                is_active=is_active
            )
            return items

    # ============================================================
    # 5️⃣ جلب تفاصيل معلم (مع التكليفات)
    # ============================================================

    async def get_teacher_detail(self, teacher_id: str) -> dict:
        """
        جلب تفاصيل معلم مع تكليفاته.
        """
        teacher = await self.teachers.get_by_id(teacher_id)
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
            "user_id": teacher.user_id,
            "assignments": [
                {
                    "id": a.id,
                    "subject_id": a.subject_id,
                    "section_id": a.section_id,
                    "year_id": a.year_id,
                    "status": a.status,
                    "assigned_at": a.assigned_at,
                }
                for a in assignments
            ],
        }

    # ============================================================
    # 6️⃣ تكليف معلم بمادة وشعبة
    # ============================================================

    async def assign_teacher(self, req: AssignmentCreate) -> dict:
        """
        تكليف معلم بمادة وشعبة.
        """
        # التحقق من وجود المعلم
        teacher = await self.teachers.get_by_id(req.teacher_id)
        if not teacher:
            raise NotFoundException("المعلم غير موجود")
        
        # التحقق من عدم وجود تكليف مكرر
        existing = await self.assignments.get_existing(
            req.teacher_id, 
            req.subject_id, 
            req.section_id, 
            req.year_id
        )
        if existing and existing.status == "active":
            raise ConflictException("التكليف موجود بالفعل")
        
        now = datetime.now(timezone.utc).isoformat()
        
        assignment = await self.assignments.create(
            teacher_id=req.teacher_id,
            school_id=teacher.school_id,
            subject_id=req.subject_id,
            section_id=req.section_id,
            year_id=req.year_id,
            status="active",
            assigned_at=now,
        )
        
        return {
            "id": assignment.id,
            "teacher_id": req.teacher_id,
            "subject_id": req.subject_id,
            "section_id": req.section_id,
            "year_id": req.year_id,
            "status": "active",
        }

    # ============================================================
    # 7️⃣ إلغاء تكليف معلم
    # ============================================================

    async def unassign_teacher(self, assignment_id: str) -> dict:
        """
        إلغاء تكليف معلم (تعطيل التكليف).
        """
        assignment = await self.assignments.get_by_id(assignment_id)
        if not assignment:
            raise NotFoundException("التكليف غير موجود")
        
        assignment.status = "inactive"
        await self.db.flush()
        
        return {
            "id": assignment.id,
            "status": "inactive",
            "message": "تم إلغاء التكليف بنجاح",
        }

    # ============================================================
    # 8️⃣ جلب تكليفات معلم
    # ============================================================

    async def get_teacher_assignments(
        self, 
        teacher_id: str, 
        year_id: str | None = None
    ) -> List[dict]:
        """
        جلب جميع تكليفات معلم.
        """
        teacher = await self.teachers.get_by_id(teacher_id)
        if not teacher:
            raise NotFoundException("المعلم غير موجود")
        
        assignments = await self.assignments.list_by_teacher(teacher_id, year_id)
        
        return [
            {
                "id": a.id,
                "subject_id": a.subject_id,
                "section_id": a.section_id,
                "year_id": a.year_id,
                "status": a.status,
                "assigned_at": a.assigned_at,
            }
            for a in assignments
        ]

    # ============================================================
    # 9️⃣ جلب المعلمين حسب الشعبة
    # ============================================================

    async def get_teachers_by_section(
        self, 
        section_id: str, 
        year_id: str
    ) -> List[dict]:
        """
        جلب المعلمين المكلفين في شعبة معينة.
        """
        assignments = await self.assignments.list_by_section(section_id, year_id)
        
        result = []
        for a in assignments:
            teacher = await self.teachers.get_by_id(a.teacher_id)
            if teacher:
                result.append({
                    "id": teacher.id,
                    "full_name": f"{teacher.first_name} {teacher.last_name}",
                    "employee_number": teacher.employee_number,
                    "specialization": teacher.specialization,
                    "phone": teacher.phone,
                    "email": teacher.email,
                    "assignment_id": a.id,
                    "subject_id": a.subject_id,
                })
        
        return result

    # ============================================================
    # 🔟 حساب عدد المعلمين
    # ============================================================

    async def count_teachers(
        self,
        school_id: str,
        is_active: bool = True,
    ) -> int:
        """
        حساب عدد المعلمين.
        """
        return await self.teachers.count(school_id, is_active)
