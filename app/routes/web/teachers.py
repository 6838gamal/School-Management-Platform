"""Teachers web routes."""
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_any_permission, template_context
from app.services.teacher_service import TeacherService

# محاولة استيراد الموديلات
try:
    from app.models.teacher import Teacher
    from app.models.user import User
except ImportError:
    # تعريف الموديلات مؤقتاً
    from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
    from sqlalchemy.sql import func
    from app.core.database import Base
    
    class Teacher(Base):
        __tablename__ = "teachers"
        id = Column(String(36), primary_key=True)
        school_id = Column(String(36), ForeignKey("schools.id"))
        employee_number = Column(String(50), unique=True, nullable=False)
        full_name = Column(String(255), nullable=False)
        specialization = Column(String(255))
        phone = Column(String(20))
        email = Column(String(255))
        is_active = Column(Boolean, default=True)
        created_at = Column(DateTime(timezone=True), server_default=func.now())
        updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    class User(Base):
        __tablename__ = "users"
        id = Column(String(36), primary_key=True)
        email = Column(String(255), unique=True, nullable=False)
        full_name = Column(String(255), nullable=False)
        school_id = Column(String(36), ForeignKey("schools.id"))
        hashed_password = Column(String(255), nullable=False)
        is_active = Column(Boolean, default=True)
        created_at = Column(DateTime(timezone=True), server_default=func.now())
        updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# استيراد دالة التشفير (الاسم الصحيح هو hash_password)
from app.core.security import hash_password

router = APIRouter(prefix="/teachers", tags=["teachers"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/new")
async def teacher_new(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("teachers.create")),
    ctx: dict = Depends(template_context),
):
    return templates.TemplateResponse(
        "teachers/form.html",
        {**ctx, "title": "إضافة معلم", "mode": "create"},
    )


@router.get("")
async def teachers_list(
    request: Request,
    page: int = 1,
    search: str = "",
    user: CurrentUser = Depends(require_any_permission("teachers.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = TeacherService(db)
    result = await service.list_teachers(user.school_id, page, 20, search or None)
    return templates.TemplateResponse(
        "teachers/list.html",
        {**ctx, "title": "المعلمون", "teachers": result["items"], "total": result["total"],
         "page": page, "page_size": 20, "search": search},
    )


@router.post("")
async def teacher_create(
    request: Request,
    employee_number: str = Form(...),
    full_name: str = Form(...),
    specialization: str = Form(None),
    phone: str = Form(None),
    email: str = Form(None),
    is_active: bool = Form(False),
    create_user: bool = Form(False),
    user: CurrentUser = Depends(require_any_permission("teachers.create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new teacher."""
    try:
        # التحقق من عدم وجود رقم موظف مكرر
        existing = await db.execute(
            select(Teacher).where(Teacher.employee_number == employee_number)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="رقم الموظف موجود مسبقاً")
        
        # إنشاء المعلم
        teacher = Teacher(
            id=str(uuid.uuid4()),
            school_id=user.school_id,
            full_name=full_name,
            employee_number=employee_number,
            specialization=specialization,
            phone=phone,
            email=email,
            is_active=is_active
        )
        db.add(teacher)
        await db.flush()
        
        # إنشاء حساب مستخدم إذا تم اختياره
        if create_user and email:
            # التحقق من عدم وجود بريد إلكتروني مكرر
            existing_user = await db.execute(
                select(User).where(User.email == email)
            )
            if not existing_user.scalar_one_or_none():
                # استخدام hash_password بدلاً من get_password_hash
                new_user = User(
                    id=str(uuid.uuid4()),
                    email=email,
                    full_name=full_name,
                    school_id=user.school_id,
                    hashed_password=hash_password("password123"),  # ✅ استخدمنا الدالة الصحيحة
                    is_active=is_active
                )
                db.add(new_user)
                await db.flush()
        
        await db.commit()
        return RedirectResponse(url="/teachers?success=created", status_code=303)
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error creating teacher: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{teacher_id}/update")
async def teacher_edit(
    request: Request,
    teacher_id: str,
    user: CurrentUser = Depends(require_any_permission("teachers.update")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = TeacherService(db)
    teacher = await service.get_teacher_detail(teacher_id)
    return templates.TemplateResponse(
        "teachers/form.html",
        {**ctx, "title": "تعديل معلم", "mode": "edit", "teacher": teacher},
    )


@router.post("/{teacher_id}/update")
async def teacher_update(
    teacher_id: str,
    employee_number: str = Form(...),
    full_name: str = Form(...),
    specialization: str = Form(None),
    phone: str = Form(None),
    email: str = Form(None),
    is_active: bool = Form(False),
    user: CurrentUser = Depends(require_any_permission("teachers.update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a teacher."""
    try:
        result = await db.execute(
            select(Teacher).where(Teacher.id == teacher_id)
        )
        teacher = result.scalar_one_or_none()
        
        if not teacher:
            raise HTTPException(status_code=404, detail="المعلم غير موجود")
        
        existing = await db.execute(
            select(Teacher).where(
                Teacher.employee_number == employee_number,
                Teacher.id != teacher_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="رقم الموظف موجود مسبقاً")
        
        teacher.full_name = full_name
        teacher.employee_number = employee_number
        teacher.specialization = specialization
        teacher.phone = phone
        teacher.email = email
        teacher.is_active = is_active
        
        await db.commit()
        return RedirectResponse(url=f"/teachers/{teacher_id}?success=updated", status_code=303)
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error updating teacher: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{teacher_id}")
async def teacher_detail(
    request: Request,
    teacher_id: str,
    user: CurrentUser = Depends(require_any_permission("teachers.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    service = TeacherService(db)
    detail = await service.get_teacher_detail(teacher_id)
    return templates.TemplateResponse(
        "teachers/detail.html",
        {**ctx, "title": detail["full_name"], "teacher": detail},
    )


@router.post("/{teacher_id}/delete")
async def teacher_delete(
    teacher_id: str,
    user: CurrentUser = Depends(require_any_permission("teachers.delete")),
    db: AsyncSession = Depends(get_db),
):
    service = TeacherService(db)
    await service.delete_teacher(teacher_id)
    return RedirectResponse(url="/teachers", status_code=303)
