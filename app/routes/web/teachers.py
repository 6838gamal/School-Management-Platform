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
from app.models.teachers import Teacher
from app.models.users import User
from app.core.security import hash_password

router = APIRouter(prefix="/teachers", tags=["teachers"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/new")
async def teacher_new(
    request: Request,
    user: CurrentUser = Depends(require_any_permission("teachers.create")),
    ctx: dict = Depends(template_context),
):
    """Display teacher creation form."""
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
    """List all teachers with pagination and search."""
    service = TeacherService(db)
    result = await service.list_teachers(user.school_id, page, 20, search or None)
    return templates.TemplateResponse(
        "teachers/list.html",
        {
            **ctx,
            "title": "المعلمون",
            "teachers": result["items"],
            "total": result["total"],
            "page": page,
            "page_size": 20,
            "search": search,
        },
    )


@router.post("")
async def teacher_create(
    request: Request,
    employee_number: str = Form(...),
    full_name: str = Form(...),
    specialization: str = Form(None),
    phone: str = Form(None),
    email: str = Form(None),
    gender: str = Form(None),
    national_id: str = Form(None),
    qualification: str = Form(None),
    hire_date: str = Form(None),
    is_active: bool = Form(False),
    create_user: bool = Form(False),
    user: CurrentUser = Depends(require_any_permission("teachers.create")),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new teacher.
    
    Splits full_name into first_name and last_name for the Teacher model.
    Optionally creates a user account if create_user is checked.
    """
    try:
        # Check for duplicate employee number
        existing = await db.execute(
            select(Teacher).where(Teacher.employee_number == employee_number)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="رقم الموظف موجود مسبقاً")
        
        # Split full_name into first_name and last_name
        name_parts = full_name.strip().split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        # Create teacher with correct fields
        teacher = Teacher(
            id=str(uuid.uuid4()),
            school_id=user.school_id,
            first_name=first_name,
            last_name=last_name,
            employee_number=employee_number,
            specialization=specialization,
            phone=phone,
            email=email,
            gender=gender,
            national_id=national_id,
            qualification=qualification,
            hire_date=hire_date,
            is_active=is_active
        )
        db.add(teacher)
        await db.flush()
        
        # Create user account if requested and email is provided
        if create_user and email:
            # Check for duplicate email
            existing_user = await db.execute(
                select(User).where(User.email == email)
            )
            if not existing_user.scalar_one_or_none():
                new_user = User(
                    id=str(uuid.uuid4()),
                    email=email,
                    full_name=full_name,
                    school_id=user.school_id,
                    hashed_password=hash_password("password123"),
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
    """Display teacher edit form."""
    service = TeacherService(db)
    teacher = await service.get_teacher_detail(teacher_id)
    
    # Combine first_name and last_name for the form
    full_name = f"{teacher.get('first_name', '')} {teacher.get('last_name', '')}".strip()
    teacher['full_name'] = full_name
    
    return templates.TemplateResponse(
        "teachers/form.html",
        {
            **ctx,
            "title": f"تعديل معلم: {full_name}",
            "mode": "edit",
            "teacher": teacher,
        },
    )


@router.post("/{teacher_id}/update")
async def teacher_update(
    teacher_id: str,
    employee_number: str = Form(...),
    full_name: str = Form(...),
    specialization: str = Form(None),
    phone: str = Form(None),
    email: str = Form(None),
    gender: str = Form(None),
    national_id: str = Form(None),
    qualification: str = Form(None),
    hire_date: str = Form(None),
    is_active: bool = Form(False),
    user: CurrentUser = Depends(require_any_permission("teachers.update")),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing teacher."""
    try:
        result = await db.execute(
            select(Teacher).where(Teacher.id == teacher_id)
        )
        teacher = result.scalar_one_or_none()
        
        if not teacher:
            raise HTTPException(status_code=404, detail="المعلم غير موجود")
        
        # Check for duplicate employee number (excluding current teacher)
        existing = await db.execute(
            select(Teacher).where(
                Teacher.employee_number == employee_number,
                Teacher.id != teacher_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="رقم الموظف موجود مسبقاً")
        
        # Split full_name into first_name and last_name
        name_parts = full_name.strip().split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        # Update teacher fields
        teacher.first_name = first_name
        teacher.last_name = last_name
        teacher.employee_number = employee_number
        teacher.specialization = specialization
        teacher.phone = phone
        teacher.email = email
        teacher.gender = gender
        teacher.national_id = national_id
        teacher.qualification = qualification
        teacher.hire_date = hire_date
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
    """View teacher details."""
    service = TeacherService(db)
    detail = await service.get_teacher_detail(teacher_id)
    
    # Create full name for display
    full_name = f"{detail.get('first_name', '')} {detail.get('last_name', '')}".strip()
    
    return templates.TemplateResponse(
        "teachers/detail.html",
        {
            **ctx,
            "title": full_name,
            "teacher": detail,
            "full_name": full_name,
        },
    )


@router.post("/{teacher_id}/delete")
async def teacher_delete(
    teacher_id: str,
    user: CurrentUser = Depends(require_any_permission("teachers.delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a teacher."""
    service = TeacherService(db)
    await service.delete_teacher(teacher_id)
    return RedirectResponse(url="/teachers?success=deleted", status_code=303)


@router.get("/{teacher_id}/assignments")
async def teacher_assignments(
    request: Request,
    teacher_id: str,
    user: CurrentUser = Depends(require_any_permission("teachers.view")),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(template_context),
):
    """View teacher assignments."""
    service = TeacherService(db)
    detail = await service.get_teacher_detail(teacher_id)
    
    full_name = f"{detail.get('first_name', '')} {detail.get('last_name', '')}".strip()
    
    return templates.TemplateResponse(
        "teachers/assignments.html",
        {
            **ctx,
            "title": f"توزيعات {full_name}",
            "teacher": detail,
            "assignments": detail.get("assignments", []),
            "full_name": full_name,
        },
    )


@router.post("/{teacher_id}/assign")
async def teacher_assign_subject(
    teacher_id: str,
    subject_id: str = Form(...),
    section_id: str = Form(...),
    year_id: str = Form(...),
    user: CurrentUser = Depends(require_any_permission("teachers.update")),
    db: AsyncSession = Depends(get_db),
):
    """Assign a teacher to a subject and section."""
    try:
        from app.models.teacher_assignment import TeacherAssignment
        
        # Check if assignment already exists
        existing = await db.execute(
            select(TeacherAssignment).where(
                TeacherAssignment.teacher_id == teacher_id,
                TeacherAssignment.subject_id == subject_id,
                TeacherAssignment.section_id == section_id,
                TeacherAssignment.year_id == year_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="هذا التوزيع موجود مسبقاً")
        
        # Create assignment
        from datetime import datetime
        assignment = TeacherAssignment(
            id=str(uuid.uuid4()),
            teacher_id=teacher_id,
            school_id=user.school_id,
            subject_id=subject_id,
            section_id=section_id,
            year_id=year_id,
            status="active",
            assigned_at=datetime.now().isoformat()
        )
        db.add(assignment)
        await db.commit()
        
        return RedirectResponse(
            url=f"/teachers/{teacher_id}/assignments?success=assigned",
            status_code=303
        )
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error assigning teacher: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/assignments/{assignment_id}/end")
async def teacher_assignment_end(
    assignment_id: str,
    user: CurrentUser = Depends(require_any_permission("teachers.update")),
    db: AsyncSession = Depends(get_db),
):
    """End a teacher assignment."""
    try:
        from app.models.teacher_assignment import TeacherAssignment
        from datetime import datetime
        
        result = await db.execute(
            select(TeacherAssignment).where(TeacherAssignment.id == assignment_id)
        )
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            raise HTTPException(status_code=404, detail="التوزيع غير موجود")
        
        assignment.status = "ended"
        assignment.ended_at = datetime.now().isoformat()
        
        await db.commit()
        
        return RedirectResponse(
            url=f"/teachers/{assignment.teacher_id}/assignments?success=ended",
            status_code=303
        )
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error ending assignment: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
