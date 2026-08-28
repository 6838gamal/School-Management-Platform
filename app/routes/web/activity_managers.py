from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import uuid

from app.core.database import get_db
from app.core.templating import get_templates
from app.core.dependencies import get_current_user
from app.models.users import User, Role, UserRole
from app.services.auth_service import AuthService
from app.schemas.auth import RegisterUserRequest

router = APIRouter(prefix="/activity-managers", tags=["Activity Managers"])
logger = logging.getLogger(__name__)


def is_director(user) -> bool:
    """التحقق من أن المستخدم مدير"""
    if not user:
        return False
    
    # التحقق من خاصية roles
    if hasattr(user, 'roles'):
        roles = user.roles if isinstance(user.roles, list) else [user.roles]
        if 'director' in roles:
            return True
    
    # التحقق من خاصية role (إذا كانت موجودة)
    if hasattr(user, 'role') and user.role == 'director':
        return True
    
    return False


def check_director_access(user):
    """التحقق من صلاحية المدير والوصول"""
    if not user:
        raise HTTPException(status_code=401, detail="يجب تسجيل الدخول")
    
    if not is_director(user):
        logger.warning(f"⚠️ User {user.email} attempted to access admin page without director role")
        raise HTTPException(status_code=403, detail="هذه الصفحة مخصصة للمدراء فقط")


@router.get("/", response_class=HTMLResponse)
async def activity_managers_list(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """صفحة قائمة مديري الأنشطة - للمدراء فقط"""
    try:
        # التحقق من صلاحية المدير
        check_director_access(current_user)
        
        logger.info(f"📄 Activity Managers list page requested by user: {current_user.email}")
        
        # جلب دور activity_managers
        result = await db.execute(
            select(Role).where(Role.key == 'activity_managers')
        )
        activity_role = result.scalars().first()
        
        # إذا لم يكن دور activity_managers موجوداً، قم بإنشائه
        if not activity_role:
            logger.warning("⚠️ Activity Managers role not found, creating it...")
            activity_role = Role(
                id=str(uuid.uuid4()),
                key="activity_managers",
                name_ar="مسؤول أنشطة",  # ✅ استخدام name_ar بدلاً من name
                name_en="Activities Manager"
            )
            db.add(activity_role)
            await db.commit()
            await db.refresh(activity_role)
            logger.info("✅ Activity Managers role created successfully")
        
        # جلب المستخدمين الذين لديهم دور activity_managers
        result = await db.execute(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .where(UserRole.role_id == activity_role.id)
            .order_by(User.created_at.desc())
        )
        managers = result.scalars().all()
        
        logger.info(f"📊 Found {len(managers)} activity managers")
        
        # طباعة تفاصيل المديرين للتصحيح
        for manager in managers:
            logger.info(f"   👤 {manager.full_name} ({manager.email}) - Active: {manager.is_active}")
        
        templates = get_templates()
        if templates is None:
            logger.error("❌ Templates is None!")
            raise HTTPException(status_code=500, detail="Templates not initialized")
        
        logger.info(f"✅ Templates is set successfully")
        
        return templates.TemplateResponse(
            "activity_managers/list.html",
            {
                "request": request,
                "user": current_user,
                "managers": managers,
                "page_title": "مديرو الأنشطة",
                "is_director": True,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in activity_managers_list: {str(e)}", exc_info=True)
        raise


@router.get("/create", response_class=HTMLResponse)
async def activity_managers_create_form(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """صفحة إنشاء مدير نشاط جديد - للمدراء فقط"""
    try:
        # التحقق من صلاحية المدير
        check_director_access(current_user)
        
        logger.info(f"📝 Activity Manager create form requested by user: {current_user.email}")
        
        from app.models.schools import School
        result = await db.execute(select(School))
        schools = result.scalars().all()
        
        templates = get_templates()
        if templates is None:
            raise HTTPException(status_code=500, detail="Templates not initialized")
        
        return templates.TemplateResponse(
            "activity_managers/create.html",
            {
                "request": request,
                "user": current_user,
                "schools": schools,
                "page_title": "إضافة مدير نشاط جديد",
                "is_director": True,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in activity_managers_create_form: {str(e)}", exc_info=True)
        raise


@router.post("/create")
async def activity_managers_create(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """إنشاء مدير نشاط جديد - للمدراء فقط"""
    try:
        # التحقق من صلاحية المدير
        check_director_access(current_user)
        
        form_data = await request.form()
        
        # طباعة البيانات المستلمة للتصحيح
        logger.info(f"📝 Creating activity manager with data:")
        logger.info(f"   - Full Name: {form_data.get('full_name')}")
        logger.info(f"   - Email: {form_data.get('email')}")
        logger.info(f"   - Phone: {form_data.get('phone')}")
        
        # التأكد من وجود دور activity_managers
        activity_role_result = await db.execute(
            select(Role).where(Role.key == 'activity_managers')
        )
        activity_role = activity_role_result.scalars().first()
        
        if not activity_role:
            logger.warning("⚠️ Activity Managers role not found, creating it...")
            activity_role = Role(
                id=str(uuid.uuid4()),
                key="activity_managers",
                name_ar="مسؤول أنشطة",  # ✅ استخدام name_ar بدلاً من name
                name_en="Activities Manager"
            )
            db.add(activity_role)
            await db.commit()
            await db.refresh(activity_role)
            logger.info("✅ Activity Managers role created successfully")
        
        # إنشاء المستخدم
        service = AuthService(db)
        
        user_data = RegisterUserRequest(
            email=form_data.get("email"),
            password=form_data.get("password"),
            full_name=form_data.get("full_name"),
            phone=form_data.get("phone"),
            school_code=form_data.get("school_code") or "SCH001",
            role_name="activity_managers"
        )
        
        result = await service.register_user(user_data)
        
        # التحقق من نجاح التسجيل والتعامل مع النتيجة بشكل صحيح
        if result and isinstance(result, dict) and result.get("user"):
            # النتيجة هي قاموس يحتوي على مفتاح 'user'
            new_user = result.get("user")
            logger.info(f"✅ Activity Manager created successfully: {new_user.email if hasattr(new_user, 'email') else new_user.get('email')}")
            
            # الحصول على ID المستخدم بشكل آمن
            user_id = new_user.id if hasattr(new_user, 'id') else new_user.get('id')
            
            # التحقق من ربط المستخدم بدور activity_managers
            user_role_result = await db.execute(
                select(UserRole)
                .where(
                    UserRole.user_id == user_id,
                    UserRole.role_id == activity_role.id
                )
            )
            existing_role = user_role_result.scalars().first()
            
            if not existing_role:
                # ربط المستخدم بدور activity_managers
                user_role = UserRole(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    role_id=activity_role.id
                )
                db.add(user_role)
                await db.commit()
                logger.info(f"✅ User linked to activity_managers role")
            else:
                logger.info(f"✅ User already has activity_managers role")
        else:
            logger.error(f"❌ Failed to create activity manager: {result}")
            return RedirectResponse(
                url="/activity-managers/create?error=فشل إنشاء مدير النشاط",
                status_code=303
            )
        
        return RedirectResponse(
            url="/activity-managers/?success=true",
            status_code=303
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating activity manager: {str(e)}", exc_info=True)
        return RedirectResponse(
            url=f"/activity-managers/create?error={str(e)}",
            status_code=303
        )


@router.get("/{manager_id}/update", response_class=HTMLResponse)
async def activity_managers_update_form(
    request: Request,
    manager_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """صفحة تعديل مدير نشاط - للمدراء فقط"""
    try:
        # التحقق من صلاحية المدير
        check_director_access(current_user)
        
        result = await db.execute(
            select(User).where(User.id == manager_id)
        )
        manager = result.scalar_one_or_none()
        
        if not manager:
            raise HTTPException(status_code=404, detail="مدير النشاط غير موجود")
        
        from app.models.schools import School
        result = await db.execute(select(School))
        schools = result.scalars().all()
        
        templates = get_templates()
        if templates is None:
            raise HTTPException(status_code=500, detail="Templates not initialized")
        
        return templates.TemplateResponse(
            "activity_managers/update.html",
            {
                "request": request,
                "user": current_user,
                "manager": manager,
                "schools": schools,
                "page_title": "تعديل مدير نشاط",
                "is_director": True,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in activity_managers_update_form: {str(e)}", exc_info=True)
        raise


@router.post("/{manager_id}/update")
async def activity_managers_update(
    request: Request,
    manager_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """تحديث بيانات مدير نشاط - للمدراء فقط"""
    try:
        # التحقق من صلاحية المدير
        check_director_access(current_user)
        
        form_data = await request.form()
        
        result = await db.execute(
            select(User).where(User.id == manager_id)
        )
        manager = result.scalar_one_or_none()
        
        if not manager:
            raise HTTPException(status_code=404, detail="مدير النشاط غير موجود")
        
        manager.full_name = form_data.get("full_name")
        manager.phone = form_data.get("phone")
        manager.is_active = form_data.get("is_active") == "on"
        
        new_password = form_data.get("password")
        if new_password and len(new_password) >= 6:
            from app.core.security import hash_password
            manager.password_hash = hash_password(new_password)
        
        await db.commit()
        
        logger.info(f"✅ Activity Manager updated successfully: {manager.email}")
        
        return RedirectResponse(
            url="/activity-managers/?success=true",
            status_code=303
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating activity manager: {str(e)}", exc_info=True)
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
    """حذف مدير نشاط - للمدراء فقط"""
    try:
        # التحقق من صلاحية المدير
        check_director_access(current_user)
        
        result = await db.execute(
            select(User).where(User.id == manager_id)
        )
        manager = result.scalar_one_or_none()
        
        if not manager:
            raise HTTPException(status_code=404, detail="مدير النشاط غير موجود")
        
        # حذف علاقات المستخدم بالأدوار أولاً
        from sqlalchemy import delete
        await db.execute(
            delete(UserRole).where(UserRole.user_id == manager_id)
        )
        
        # حذف المستخدم
        await db.delete(manager)
        await db.commit()
        
        logger.info(f"✅ Activity Manager deleted successfully: {manager.email}")
        
        return RedirectResponse(
            url="/activity-managers/?deleted=true",
            status_code=303
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting activity manager: {str(e)}", exc_info=True)
        return RedirectResponse(
            url="/activity-managers/?error=" + str(e),
            status_code=303
        )
