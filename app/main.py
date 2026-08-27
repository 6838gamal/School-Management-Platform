"""
Application entry point.

Assembles the FastAPI app, mounts static files, configures Jinja2,
registers all web and API routers, and wires exception handlers.
"""
import logging

# إعداد logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# تعيين مستوى logging لخدمة المصادقة
logger = logging.getLogger("app.services.auth_service")
logger.setLevel(logging.INFO)

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, text

from app.core.config import settings
from app.core.database import engine, get_db, Base
from app.core.exceptions import register_exception_handlers
from app.core.templating import set_templates, get_templates
from app.core.security import hash_password
from app.models.users import User, Role, Permission, UserRole, RolePermission
from app.models.schools import School
from app.core.permissions import PERMISSIONS, ROLE_PERMISSIONS, ROLE_LABELS

# ============= استيراد API routes =============
from app.routes.api.v1.auth import router as api_auth_router
from app.routes.api.v1.modules import (
    academics_router as api_academics,
    activities_router as api_activities,
    attendance_router as api_attendance,
    behavior_router as api_behavior,
    grades_router as api_grades,
    homework_router as api_homework,
    notifications_router as api_notifications,
    reports_router as api_reports,
    schedules_router as api_schedules,
)
from app.routes.api.v1.students import router as api_students_router
from app.routes.api.v1.teachers import router as api_teachers_router

# ============= استيراد Web routes =============
from app.routes.web.academics import router as web_academics
from app.routes.web.auth import router as web_auth
from app.routes.web.dashboard import router as web_dashboard
from app.routes.web.students import router as web_students
from app.routes.web.teachers import router as web_teachers
from app.routes.web.schedules import router as web_schedules
from app.routes.web.deputy import router as web_deputy
from app.routes.web.activity_managers import router as web_activity_managers
from app.routes.web.modules import (
    activities_router as web_activities,
    attendance_router as web_attendance,
    behavior_router as web_behavior,
    grades_router as web_grades,
    homework_router as web_homework,
    notifications_router as web_notifications,
    reports_router as web_reports,
)

from app.routes.web.teachers import router as teachers_router

from app.routes.api import router as api_router

# ============= إنشاء مثيل templates =============
templates = Jinja2Templates(directory="app/templates")


# ============= دالة can للقوالب =============
def can(permission: str, request: Request = None) -> bool:
    """
    التحقق من أن المستخدم لديه صلاحية معينة (للاستخدام في القوالب)
    
    ملاحظة: هذه الدالة تستخدم في القوالب، لذلك يجب أن تقبل permission كمعامل أول
    """
    # إذا لم يتم تمرير request، حاول الحصول عليه من السياق
    if request is None:
        # في القوالب، يتم تمرير request كجزء من السياق
        # ولكن الدالة تستدعى بـ can('permission') فقط
        # لذلك نستخدم طريقة مختلفة للتحقق
        return False
    
    if not hasattr(request, 'state'):
        return False
    
    # التحقق من وجود المستخدم في request.state
    if not hasattr(request.state, 'user') or request.state.user is None:
        return False
    
    # التحقق من الصلاحيات
    if hasattr(request.state, 'permissions'):
        return permission in request.state.permissions
    
    return False


# تسجيل دالة can في Jinja2 (بدون request)
templates.env.globals['can'] = lambda permission: can(permission)


async def ensure_user_exists(db, email: str, password: str, full_name: str, school_id: int, role_name: str):
    """التأكد من وجود المستخدم، وإنشائه إذا لم يكن موجوداً"""
    from app.services.auth_service import AuthService
    from app.core.security import hash_password
    
    service = AuthService(db)
    
    # التحقق من وجود المستخدم
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        print(f"ℹ️ المستخدم موجود بالفعل: {email}")
        await service.ensure_user_has_role(user.id, role_name, school_id)
        return user
    
    # إنشاء المستخدم الجديد
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        school_id=school_id,
        is_active=True
    )
    db.add(user)
    await db.flush()
    
    await service.ensure_user_has_role(user.id, role_name, school_id)
    
    print(f"✅ تم إنشاء المستخدم: {email} (الدور: {role_name})")
    return user


async def ensure_database_schema():
    """التأكد من وجود جميع الأعمدة المطلوبة في قاعدة البيانات"""
    print("🔧 جاري التحقق من هيكل قاعدة البيانات...")
    
    async for db in get_db():
        try:
            # 1. التحقق من وجود عمود academic_year_id في جدول schedules
            await db.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'schedules' AND column_name = 'academic_year_id'
                    ) THEN
                        ALTER TABLE schedules ADD COLUMN academic_year_id VARCHAR(36);
                        CREATE INDEX IF NOT EXISTS ix_schedules_academic_year_id ON schedules (academic_year_id);
                        RAISE NOTICE '✅ تم إضافة العمود academic_year_id إلى جدول schedules';
                    ELSE
                        RAISE NOTICE 'ℹ️ العمود academic_year_id موجود بالفعل في جدول schedules';
                    END IF;
                END $$;
            """))
            await db.commit()
            print("✅ تم التحقق من هيكل قاعدة البيانات بنجاح")
            break
        except Exception as e:
            print(f"⚠️ خطأ في التحقق من هيكل قاعدة البيانات: {str(e)}")
            await db.rollback()
            break


async def ensure_role_permissions_updated(school_id: str):
    """
    التأكد من أن جميع الأدوار لديها الصلاحيات المطلوبة
    هذه الدالة تضمن إضافة الصلاحيات الجديدة للأدوار الموجودة
    """
    from app.core.permissions import ROLE_PERMISSIONS
    from app.models.users import Role, Permission, RolePermission
    from sqlalchemy import select
    
    print("🔄 جاري تحديث صلاحيات الأدوار...")
    
    async for db in get_db():
        try:
            # 1. جلب جميع الصلاحيات الموجودة
            stmt = select(Permission)
            result = await db.execute(stmt)
            all_perms = {p.key: p for p in result.scalars().all()}
            print(f"📊 عدد الصلاحيات الكلي: {len(all_perms)}")
            
            # 2. جلب جميع الأدوار للمدرسة
            stmt = select(Role).where(Role.school_id == school_id)
            result = await db.execute(stmt)
            roles = result.scalars().all()
            print(f"📊 عدد الأدوار: {len(roles)}")
            
            updated_count = 0
            
            # 3. لكل دور، تأكد من وجود جميع الصلاحيات المطلوبة
            for role in roles:
                # جلب الصلاحيات الحالية للدور
                stmt = select(RolePermission).where(RolePermission.role_id == role.id)
                result = await db.execute(stmt)
                existing_perms = {rp.permission_id for rp in result.scalars().all()}
                
                # جلب الصلاحيات المطلوبة للدور من ROLE_PERMISSIONS
                required_perm_keys = ROLE_PERMISSIONS.get(role.key, [])
                
                # إضافة الصلاحيات المفقودة
                for perm_key in required_perm_keys:
                    if perm_key in all_perms:
                        perm = all_perms[perm_key]
                        if perm.id not in existing_perms:
                            role_perm = RolePermission(
                                role_id=role.id,
                                permission_id=perm.id
                            )
                            db.add(role_perm)
                            updated_count += 1
                            print(f"   ✅ إضافة صلاحية '{perm_key}' للدور '{role.key}'")
                    else:
                        print(f"   ⚠️ صلاحية '{perm_key}' غير موجودة في قاعدة البيانات")
                
                await db.flush()
            
            await db.commit()
            print(f"✅ تم تحديث صلاحيات الأدوار: تم إضافة {updated_count} صلاحية جديدة")
            
        except Exception as e:
            print(f"❌ خطأ في تحديث صلاحيات الأدوار: {str(e)}")
            await db.rollback()
        break


async def init_database():
    """تهيئة قاعدة البيانات وإنشاء المستخدمين الأوليين."""
    from app.services.auth_service import AuthService
    
    print("🌱 جاري تهيئة قاعدة البيانات...")
    
    async for db in get_db():
        try:
            service = AuthService(db)
            
            # 1. التحقق من وجود مدرسة
            stmt = select(School).where(School.code == "SCHOOL001")
            result = await db.execute(stmt)
            school = result.scalar_one_or_none()
            
            if not school:
                school = School(
                    name="مدرسة النموذج",
                    code="SCHOOL001",
                    onboarding_complete=True,
                    is_active=True
                )
                db.add(school)
                await db.flush()
                print("✅ تم إنشاء المدرسة")
            
            # 2. التأكد من وجود جميع الصلاحيات (إضافة المفقودة فقط)
            await service.ensure_permissions_exist(school.id)
            
            # 3. تهيئة الصلاحيات والأدوار الأساسية
            await service.ensure_system_roles_and_permissions(school.id)
            await db.commit()
            print("✅ تم تهيئة الصلاحيات والأدوار الأساسية")
            
            # 4. تحديث صلاحيات الأدوار الموجودة (إضافة الصلاحيات الجديدة)
            await ensure_role_permissions_updated(school.id)
            
            # 5. إنشاء المستخدمين التجريبيين
            demo_users = [
                {"email": "admin@school.edu", "password": "admin123", "full_name": "أحمد المدير", "role": "director"},
                {"email": "deputy@school.edu", "password": "deputy123", "full_name": "خالد الوكيل", "role": "deputy"},
                {"email": "activities@school.edu", "password": "activities123", "full_name": "سارة الأنشطة", "role": "activities_manager"},
                {"email": "teacher@school.edu", "password": "teacher123", "full_name": "محمد المعلم", "role": "teacher"}
            ]
            
            for user_data in demo_users:
                await ensure_user_exists(
                    db,
                    email=user_data["email"],
                    password=user_data["password"],
                    full_name=user_data["full_name"],
                    school_id=school.id,
                    role_name=user_data["role"]
                )
            
            await db.commit()
            
            # عرض الملخص
            stmt = select(User)
            result = await db.execute(stmt)
            users_count = len(result.scalars().all())
            
            stmt = select(Role).where(Role.school_id == school.id)
            result = await db.execute(stmt)
            roles_count = len(result.scalars().all())
            
            stmt = select(Permission)
            result = await db.execute(stmt)
            perms_count = len(result.scalars().all())
            
            print("\n" + "="*50)
            print("🎉 تم تهيئة قاعدة البيانات بنجاح!")
            print("="*50)
            print(f"\n📊 إحصائيات:")
            print(f"   🏫 مدرسة: 1")
            print(f"   👤 مستخدمين: {users_count}")
            print(f"   🎭 أدوار: {roles_count}")
            print(f"   🔑 صلاحيات: {perms_count}")
            print("\n📝 بيانات تسجيل الدخول:")
            print("   👨‍💼 admin@school.edu / admin123 (مدير)")
            print("   👨‍🏫 deputy@school.edu / deputy123 (وكيل)")
            print("   🎯 activities@school.edu / activities123 (مسؤول أنشطة)")
            print("   📚 teacher@school.edu / teacher123 (معلم)")
            print("="*50 + "\n")
            
        except Exception as e:
            print(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
            await db.rollback()
        break


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    print("🚀 Starting application...")
    print(f"📊 Database: {settings.DATABASE_URL}")
    
    # تعيين القوالب للتطبيق - يجب أن يكون قبل أي استخدام
    set_templates(templates)
    print("✅ تم تعيين القوالب للتطبيق")
    
    # التحقق من تعيين templates
    if get_templates() is None:
        print("❌ فشل تعيين templates!")
    else:
        print(f"✅ تم تأكيد تعيين templates: {get_templates() is not None}")
    
    # 1. التحقق من هيكل قاعدة البيانات (إضافة الأعمدة المفقودة)
    await ensure_database_schema()
    
    # 2. تهيئة قاعدة البيانات (المستخدمين والصلاحيات)
    await init_database()
    
    yield
    
    # إغلاق اتصال قاعدة البيانات عند الإيقاف
    await engine.dispose()
    print("✅ Database connection closed.")


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.APP_DEBUG,
    lifespan=lifespan,
)

# ============= Mount static files =============
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ============= Register exception handlers =============
register_exception_handlers(app)

# ============= Web routes =============
app.include_router(web_auth)
app.include_router(web_dashboard)
app.include_router(web_students)
app.include_router(web_teachers)
app.include_router(web_academics)
app.include_router(web_schedules)
app.include_router(web_deputy)
app.include_router(web_activity_managers)
app.include_router(web_attendance)
app.include_router(web_grades)
app.include_router(web_homework)
app.include_router(web_activities)
app.include_router(web_behavior)
app.include_router(web_notifications)
app.include_router(web_reports)
app.include_router(teachers_router)

# ============= API v1 routes =============
api_prefix = "/api/v1"
app.include_router(api_auth_router, prefix=api_prefix)
app.include_router(api_students_router, prefix=api_prefix)
app.include_router(api_teachers_router, prefix=api_prefix)
app.include_router(api_academics, prefix=api_prefix)
app.include_router(api_attendance, prefix=api_prefix)
app.include_router(api_grades, prefix=api_prefix)
app.include_router(api_schedules, prefix=api_prefix)
app.include_router(api_homework, prefix=api_prefix)
app.include_router(api_activities, prefix=api_prefix)
app.include_router(api_behavior, prefix=api_prefix)
app.include_router(api_notifications, prefix=api_prefix)
app.include_router(api_reports, prefix=api_prefix)

# ============= Additional routes =============
app.include_router(api_router)


@app.get("/")
async def root(request: Request):
    return RedirectResponse("/login", status_code=302)


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
