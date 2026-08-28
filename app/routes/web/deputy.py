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

router = APIRouter(prefix="/deputy", tags=["Deputy"])
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
async def deputy_list(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """صفحة قائمة وكلاء المدرسة - للمدراء فقط"""
    try:
        # التحقق من صلاحية المدير
        check_director_access(current_user)
        
        logger.info(f"📄 Deputy list page requested by user: {current_user.email}")
        
        # جلب دور deputy
        deputy_role_result = await db.execute(
            select(Role).where(Role.key == 'deputy')
        )
        deputy_role = deputy_role_result.scalars().first()
        
        # إذا لم يكن دور deputy موجوداً، قم بإنشائه
        if not deputy_role:
            logger.warning("⚠️ Deputy role not found, creating it...")
            deputy_role = Role(
                id=str(uuid.uuid4()),
                key="deputy",
                name="وكيل",
                name_en="Deputy Director"
            )
            db.add(deputy_role)
            await db.commit()
            await db.refresh(deputy_role)
            logger.info("✅ Deputy role created successfully")
        
        # جلب المستخدمين الذين لديهم دور deputy
        result = await db.execute(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .where(UserRole.role_id == deputy_role.id)
            .order_by(User.created_at.desc())
        )
        deputies = result.scalars().all()
        
        logger.info(f"📊 Found {len(deputies)} deputies")
        
        # طباعة تفاصيل الوكلاء للتصحيح
        for deputy in deputies:
            logger.info(f"   👤 {deputy.full_name} ({deputy.email}) - Active: {deputy.is_active}")
        
        templates = get_templates()
        if templates is None:
            logger.error("❌ Templates is None!")
            raise HTTPException(status_code=500, detail="Templates not initialized")
        
        logger.info(f"✅ Templates is set successfully")
        
        return templates.TemplateResponse(
            "deputy/list.html",
            {
                "request": request,
                "user": current_user,
                "deputies": deputies,
                "page_title": "وكلاء المدرسة",
                "is_director": True,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in deputy_list: {str(e)}", exc_info=True)
        raise


@router.get("/create", response_class=HTMLResponse)
async def deputy_create_form(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """صفحة إنشاء وكيل جديد - للمدراء فقط"""
    try:
        # التحقق من صلاحية المدير
        check_director_access(current_user)
        
        logger.info(f"📝 Deputy create form requested by user: {current_user.email}")
        
        from app.models.schools import School
        result = await db.execute(select(School))
        schools = result.scalars().all()
        
        templates = get_templates()
        if templates is None:
            raise HTTPException(status_code=500, detail="Templates not initialized")
        
        return templates.TemplateResponse(
            "deputy/create.html",
            {
                "request": request,
                "user": current_user,
                "schools": schools,
                "page_title": "إضافة وكيل جديد",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in deputy_create_form: {str(e)}", exc_info=True)
        raise


@router.post("/create")
async def deputy_create(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """إنشاء وكيل جديد - للمدراء فقط"""
    try:
        # التحقق من صلاحية المدير
        check_director_access(current_user)
        
        form_data = await request.form()
        
        # طباعة البيانات المستلمة للتصحيح
        logger.info(f"📝 Creating deputy with data:")
        logger.info(f"   - Full Name: {form_data.get('full_name')}")
        logger.info(f"   - Email: {form_data.get('email')}")
        logger.info(f"   - Phone: {form_data.get('phone')}")
        
        # التأكد من وجود دور deputy
        deputy_role_result = await db.execute(
            select(Role).where(Role.key == 'deputy')
        )
        deputy_role = deputy_role_result.scalars().first()
        
        if not deputy_role:
            logger.warning("⚠️ Deputy role not found, creating it...")
            deputy_role = Role(
                id=str(uuid.uuid4()),
                key="deputy",
                name="وكيل",
                name_en="Deputy Director"
            )
            db.add(deputy_role)
            await db.commit()
            await db.refresh(deputy_role)
            logger.info("✅ Deputy role created successfully")
        
        # إنشاء المستخدم
        service = AuthService(db)
        
        user_data = RegisterUserRequest(
            email=form_data.get("email"),
            password=form_data.get("password"),
            full_name=form_data.get("full_name"),
            phone=form_data.get("phone"),
            school_code=form_data.get("school_code") or "SCH001",
            role_name="deputy"
        )
        
        result = await service.register_user(user_data)
        
        # ✅ التحقق من نجاح التسجيل والتعامل مع النتيجة بشكل صحيح
        if result and isinstance(result, dict) and result.get("user"):
            # النتيجة هي قاموس يحتوي على مفتاح 'user'
            new_user = result.get("user")
            logger.info(f"✅ Deputy created successfully: {new_user.email if hasattr(new_user, 'email') else new_user.get('email')}")
            
            # ✅ الحصول على ID المستخدم بشكل آمن
            user_id = new_user.id if hasattr(new_user, 'id') else new_user.get('id')
            
            # التحقق من ربط المستخدم بدور deputy
            user_role_result = await db.execute(
                select(UserRole)
                .where(
                    UserRole.user_id == user_id,
                    UserRole.role_id == deputy_role.id
                )
            )
            existing_role = user_role_result.scalars().first()
            
            if not existing_role:
                # ربط المستخدم بدور deputy
                user_role = UserRole(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    role_id=deputy_role.id
                )
                db.add(user_role)
                await db.commit()
                logger.info(f"✅ User {new_user.email if hasattr(new_user, 'email') else new_user.get('email')} linked to deputy role")
            else:
                logger.info(f"✅ User already has deputy role")
        else:
            logger.error(f"❌ Failed to create deputy: {result}")
            return RedirectResponse(
                url="/deputy/create?error=فشل إنشاء الوكيل",
                status_code=303
            )
        
        return RedirectResponse(
            url="/deputy/?success=true",
            status_code=303
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating deputy: {str(e)}", exc_info=True)
        return RedirectResponse(
            url=f"/deputy/create?error={str(e)}",
            status_code=303
        )


@router.get("/{deputy_id}/update", response_class=HTMLResponse)
async def deputy_update_form(
    request: Request,
    deputy_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """صفحة تعديل وكيل - للمدراء فقط"""
    try:
        # التحقق من صلاحية المدير
        check_director_access(current_user)
        
        result = await db.execute(
            select(User).where(User.id == deputy_id)
        )
        deputy = result.scalar_one_or_none()
        
        if not deputy:
            raise HTTPException(status_code=404, detail="الوكيل غير موجود")
        
        from app.models.schools import School
        result = await db.execute(select(School))
        schools = result.scalars().all()
        
        templates = get_templates()
        if templates is None:
            raise HTTPException(status_code=500, detail="Templates not initialized")
        
        return templates.TemplateResponse(
            "deputy/update.html",
            {
                "request": request,
                "user": current_user,
                "deputy": deputy,
                "schools": schools,
                "page_title": "تعديل وكيل",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in deputy_update_form: {str(e)}", exc_info=True)
        raise


@router.post("/{deputy_id}/update")
async def deputy_update(
    request: Request,
    deputy_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """تحديث بيانات وكيل - للمدراء فقط"""
    try:
        # التحقق من صلاحية المدير
        check_director_access(current_user)
        
        form_data = await request.form()
        
        result = await db.execute(
            select(User).where(User.id == deputy_id)
        )
        deputy = result.scalar_one_or_none()
        
        if not deputy:
            raise HTTPException(status_code=404, detail="الوكيل غير موجود")
        
        deputy.full_name = form_data.get("full_name")
        deputy.phone = form_data.get("phone")
        deputy.is_active = form_data.get("is_active") == "on"
        
        new_password = form_data.get("password")
        if new_password and len(new_password) >= 6:
            from app.core.security import hash_password
            deputy.password_hash = hash_password(new_password)
        
        await db.commit()
        
        logger.info(f"✅ Deputy updated successfully: {deputy.email}")
        
        return RedirectResponse(
            url="/deputy/?success=true",
            status_code=303
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating deputy: {str(e)}", exc_info=True)
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
    """حذف وكيل - للمدراء فقط"""
    try:
        # التحقق من صلاحية المدير
        check_director_access(current_user)
        
        result = await db.execute(
            select(User).where(User.id == deputy_id)
        )
        deputy = result.scalar_one_or_none()
        
        if not deputy:
            raise HTTPException(status_code=404, detail="الوكيل غير موجود")
        
        # حذف علاقات المستخدم بالأدوار أولاً
        from sqlalchemy import delete
        await db.execute(
            delete(UserRole).where(UserRole.user_id == deputy_id)
        )
        
        # حذف المستخدم
        await db.delete(deputy)
        await db.commit()
        
        logger.info(f"✅ Deputy deleted successfully: {deputy.email}")
        
        return RedirectResponse(
            url="/deputy/?deleted=true",
            status_code=303
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting deputy: {str(e)}", exc_info=True)
        return RedirectResponse(
            url="/deputy/?error=" + str(e),
            status_code=303
        )
