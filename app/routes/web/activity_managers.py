from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.core.database import get_db
from app.core.templating import templates
from app.core.dependencies import get_current_user
from app.models.users import User, Role, UserRole
from app.services.auth_service import AuthService
from app.schemas.auth import RegisterUserRequest

router = APIRouter(prefix="/activity-managers", tags=["Activity Managers"])
logger = logging.getLogger(__name__)


@router.get("/", response_class=HTMLResponse)
async def activity_managers_list(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """صفحة قائمة مديري الأنشطة"""
    try:
        logger.info(f"📄 Activity Managers list page requested by user: {current_user.email}")
        
        # جلب دور activity_managers
        result = await db.execute(
            select(Role).where(Role.key == 'activity_managers')
        )
        activity_role = result.scalars().first()
        
        managers = []
        if activity_role:
            result = await db.execute(
                select(User)
                .join(UserRole, UserRole.user_id == User.id)
                .where(UserRole.role_id == activity_role.id)
            )
            managers = result.scalars().all()
        
        logger.info(f"📊 Found {len(managers)} activity managers")
        
        if templates is None:
            logger.error("❌ Templates is None!")
            raise HTTPException(status_code=500, detail="Templates not initialized")
        
        return templates.TemplateResponse(
            "activity_managers/list.html",
            {
                "request": request,
                "user": current_user,
                "managers": managers,
                "page_title": "مديرو الأنشطة"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Error in activity_managers_list: {str(e)}")
        raise


@router.get("/create", response_class=HTMLResponse)
async def activity_managers_create_form(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """صفحة إنشاء مدير نشاط جديد"""
    try:
        # جلب المدارس للاختيار
        from app.models.schools import School
        result = await db.execute(select(School))
        schools = result.scalars().all()
        
        if templates is None:
            raise HTTPException(status_code=500, detail="Templates not initialized")
        
        return templates.TemplateResponse(
            "activity_managers/create.html",
            {
                "request": request,
                "user": current_user,
                "schools": schools,
                "page_title": "إضافة مدير نشاط جديد"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Error in activity_managers_create_form: {str(e)}")
        raise


@router.post("/create")
async def activity_managers_create(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """إنشاء مدير نشاط جديد"""
    form_data = await request.form()
    
    try:
        service = AuthService(db)
        
        # إنشاء مستخدم جديد بدور activity_managers
        user_data = RegisterUserRequest(
            email=form_data.get("email"),
            password=form_data.get("password"),
            full_name=form_data.get("full_name"),
            phone=form_data.get("phone"),
            school_code=form_data.get("school_code"),
            role_name="activity_managers"
        )
        
        result = await service.register_user(user_data)
        
        return RedirectResponse(
            url="/activity-managers/?success=true",
            status_code=303
        )
        
    except Exception as e:
        logger.error(f"❌ Error creating activity manager: {str(e)}")
        return RedirectResponse(
            url="/activity-managers/create?error=" + str(e),
            status_code=303
        )


@router.get("/{manager_id}/update", response_class=HTMLResponse)
async def activity_managers_update_form(
    request: Request,
    manager_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """صفحة تعديل مدير نشاط"""
    try:
        # جلب المستخدم
        result = await db.execute(
            select(User).where(User.id == manager_id)
        )
        manager = result.scalar_one_or_none()
        
        if not manager:
            raise HTTPException(status_code=404, detail="مدير النشاط غير موجود")
        
        # جلب المدارس للاختيار
        from app.models.schools import School
        result = await db.execute(select(School))
        schools = result.scalars().all()
        
        if templates is None:
            raise HTTPException(status_code=500, detail="Templates not initialized")
        
        return templates.TemplateResponse(
            "activity_managers/update.html",
            {
                "request": request,
                "user": current_user,
                "manager": manager,
                "schools": schools,
                "page_title": "تعديل مدير نشاط"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Error in activity_managers_update_form: {str(e)}")
        raise


@router.post("/{manager_id}/update")
async def activity_managers_update(
    request: Request,
    manager_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """تحديث بيانات مدير نشاط"""
    form_data = await request.form()
    
    try:
        # جلب المستخدم
        result = await db.execute(
            select(User).where(User.id == manager_id)
        )
        manager = result.scalar_one_or_none()
        
        if not manager:
            raise HTTPException(status_code=404, detail="مدير النشاط غير موجود")
        
        # تحديث البيانات
        manager.full_name = form_data.get("full_name")
        manager.phone = form_data.get("phone")
        manager.is_active = form_data.get("is_active") == "on"
        
        # تحديث كلمة المرور إذا تم إدخالها
        new_password = form_data.get("password")
        if new_password and len(new_password) >= 6:
            from app.core.security import hash_password
            manager.password_hash = hash_password(new_password)
        
        await db.commit()
        
        return RedirectResponse(
            url="/activity-managers/?success=true",
            status_code=303
        )
        
    except Exception as e:
        logger.error(f"❌ Error updating activity manager: {str(e)}")
        return RedirectResponse(
            url=f"/activity-managers/{manager_id}/update?error=" + str(e),
            status_code=303
        )


@router.post("/{manager_id}/delete")
async def activity_managers_delete(
    request: Request,
    manager_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """حذف مدير نشاط"""
    try:
        # جلب المستخدم
        result = await db.execute(
            select(User).where(User.id == manager_id)
        )
        manager = result.scalar_one_or_none()
        
        if not manager:
            raise HTTPException(status_code=404, detail="مدير النشاط غير موجود")
        
        # حذف العلاقات أولاً
        from sqlalchemy import delete
        await db.execute(
            delete(UserRole).where(UserRole.user_id == manager_id)
        )
        
        # حذف المستخدم
        await db.delete(manager)
        await db.commit()
        
        return RedirectResponse(
            url="/activity-managers/?deleted=true",
            status_code=303
        )
        
    except Exception as e:
        logger.error(f"❌ Error deleting activity manager: {str(e)}")
        return RedirectResponse(
            url="/activity-managers/?error=" + str(e),
            status_code=303
        )
