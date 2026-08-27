from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.templating import templates  # ✅ استيراد templates من core.templating
from app.core.dependencies import get_current_user
from app.models.users import User, Role, UserRole
from app.services.auth_service import AuthService
from app.schemas.auth import RegisterUserRequest

router = APIRouter(prefix="/deputy", tags=["Deputy"])


@router.get("/", response_class=HTMLResponse)
async def deputy_list(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """صفحة قائمة وكلاء المدرسة"""
    
    # جلب دور deputy
    result = await db.execute(
        select(Role).where(Role.key == 'deputy')
    )
    deputy_role = result.scalar_one_or_none()
    
    deputies = []
    if deputy_role:
        result = await db.execute(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .where(UserRole.role_id == deputy_role.id)
        )
        deputies = result.scalars().all()
    
    return templates.TemplateResponse(
        "deputy/list.html",
        {
            "request": request,
            "user": current_user,
            "deputies": deputies,
            "page_title": "وكلاء المدرسة"
        }
    )


@router.get("/create", response_class=HTMLResponse)
async def deputy_create_form(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """صفحة إنشاء وكيل جديد"""
    
    # جلب المدارس للاختيار
    from app.models.schools import School
    result = await db.execute(select(School))
    schools = result.scalars().all()
    
    return templates.TemplateResponse(
        "deputy/create.html",
        {
            "request": request,
            "user": current_user,
            "schools": schools,
            "page_title": "إضافة وكيل جديد"
        }
    )


@router.post("/create")
async def deputy_create(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """إنشاء وكيل جديد"""
    form_data = await request.form()
    
    try:
        service = AuthService(db)
        
        # إنشاء مستخدم جديد بدور deputy
        user_data = RegisterUserRequest(
            email=form_data.get("email"),
            password=form_data.get("password"),
            full_name=form_data.get("full_name"),
            phone=form_data.get("phone"),
            school_code=form_data.get("school_code"),
            role_name="deputy"
        )
        
        result = await service.register_user(user_data)
        
        return RedirectResponse(
            url="/deputy/?success=true",
            status_code=303
        )
        
    except Exception as e:
        return RedirectResponse(
            url="/deputy/create?error=" + str(e),
            status_code=303
        )


@router.get("/{deputy_id}/update", response_class=HTMLResponse)
async def deputy_update_form(
    request: Request,
    deputy_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """صفحة تعديل وكيل"""
    
    # جلب المستخدم
    result = await db.execute(
        select(User).where(User.id == deputy_id)
    )
    deputy = result.scalar_one_or_none()
    
    if not deputy:
        raise HTTPException(status_code=404, detail="الوكيل غير موجود")
    
    # جلب المدارس للاختيار
    from app.models.schools import School
    result = await db.execute(select(School))
    schools = result.scalars().all()
    
    return templates.TemplateResponse(
        "deputy/update.html",
        {
            "request": request,
            "user": current_user,
            "deputy": deputy,
            "schools": schools,
            "page_title": "تعديل وكيل"
        }
    )


@router.post("/{deputy_id}/update")
async def deputy_update(
    request: Request,
    deputy_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """تحديث بيانات وكيل"""
    form_data = await request.form()
    
    try:
        # جلب المستخدم
        result = await db.execute(
            select(User).where(User.id == deputy_id)
        )
        deputy = result.scalar_one_or_none()
        
        if not deputy:
            raise HTTPException(status_code=404, detail="الوكيل غير موجود")
        
        # تحديث البيانات
        deputy.full_name = form_data.get("full_name")
        deputy.phone = form_data.get("phone")
        deputy.is_active = form_data.get("is_active") == "on"
        
        # تحديث كلمة المرور إذا تم إدخالها
        new_password = form_data.get("password")
        if new_password and len(new_password) >= 6:
            from app.core.security import hash_password
            deputy.password_hash = hash_password(new_password)
        
        await db.commit()
        
        return RedirectResponse(
            url="/deputy/?success=true",
            status_code=303
        )
        
    except Exception as e:
        return RedirectResponse(
            url=f"/deputy/{deputy_id}/update?error=" + str(e),
            status_code=303
        )


@router.post("/{deputy_id}/delete")
async def deputy_delete(
    request: Request,
    deputy_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """حذف وكيل"""
    try:
        # جلب المستخدم
        result = await db.execute(
            select(User).where(User.id == deputy_id)
        )
        deputy = result.scalar_one_or_none()
        
        if not deputy:
            raise HTTPException(status_code=404, detail="الوكيل غير موجود")
        
        # حذف العلاقات أولاً
        await db.execute(
            UserRole.__table__.delete().where(UserRole.user_id == deputy_id)
        )
        
        # حذف المستخدم
        await db.delete(deputy)
        await db.commit()
        
        return RedirectResponse(
            url="/deputy/?deleted=true",
            status_code=303
        )
        
    except Exception as e:
        return RedirectResponse(
            url="/deputy/?error=" + str(e),
            status_code=303
        )
