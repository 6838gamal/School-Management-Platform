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

logger = logging.getLogger("app.services.auth_service")
logger.setLevel(logging.INFO)

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, delete

from app.core.config import settings
from app.core.database import engine, get_db, Base
from app.core.exceptions import register_exception_handlers, set_templates
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
    schedules_router as api_schedules,  # ✅ API schedules
)
from app.routes.api.v1.students import router as api_students_router
from app.routes.api.v1.teachers import router as api_teachers_router

# ============= استيراد Web routes =============
from app.routes.web.academics import router as web_academics
from app.routes.web.auth import router as web_auth
from app.routes.web.dashboard import router as web_dashboard
from app.routes.web.modules import (
    activities_router as web_activities,
    attendance_router as web_attendance,
    behavior_router as web_behavior,
    grades_router as web_grades,
    homework_router as web_homework,
    notifications_router as web_notifications,
    reports_router as web_reports,
    schedules_router as web_schedules,  # ✅ Web schedules
)
from app.routes.web.students import router as web_students
from app.routes.web.teachers import router as web_teachers

from app.routes.api import router as api_router

templates = Jinja2Templates(directory="app/templates")


async def ensure_user_exists(db, email: str, password: str, full_name: str, school_id: int, role_name: str):
    """التأكد من وجود المستخدم، وإنشائه إذا لم يكن موجوداً"""
    from app.services.auth_service import AuthService
    from app.core.security import hash_password
    
    service = AuthService(db)
    
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        print(f"ℹ️ المستخدم موجود بالفعل: {email}")
        await service.ensure_user_has_role(user.id, role_name, school_id)
        return user
    
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
            
            # 2. تهيئة الصلاحيات والأدوار
            await service.ensure_system_roles_and_permissions(school.id)
            await db.commit()
            print("✅ تم تهيئة الصلاحيات والأدوار")
            
            # 3. إنشاء المستخدمين التجريبيين
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
    
    set_templates(templates)
    await init_database()
    
    yield
    
    await engine.dispose()
    print("✅ Database connection closed.")


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.APP_DEBUG,
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

register_exception_handlers(app)

# ============= Web routes =============
app.include_router(web_auth)
app.include_router(web_dashboard)
app.include_router(web_students)
app.include_router(web_teachers)
app.include_router(web_academics)
app.include_router(web_attendance)
app.include_router(web_grades)
app.include_router(web_schedules)      # ✅ Web schedules (مرة واحدة)
app.include_router(web_homework)
app.include_router(web_activities)
app.include_router(web_behavior)
app.include_router(web_notifications)
app.include_router(web_reports)

# ============= API v1 routes =============
api_prefix = "/api/v1"
app.include_router(api_auth_router, prefix=api_prefix)
app.include_router(api_students_router, prefix=api_prefix)
app.include_router(api_teachers_router, prefix=api_prefix)
app.include_router(api_academics, prefix=api_prefix)
app.include_router(api_attendance, prefix=api_prefix)
app.include_router(api_grades, prefix=api_prefix)
app.include_router(api_schedules, prefix=api_prefix)  # ✅ API schedules (مرة واحدة)
app.include_router(api_homework, prefix=api_prefix)
app.include_router(api_activities, prefix=api_prefix)
app.include_router(api_behavior, prefix=api_prefix)
app.include_router(api_notifications, prefix=api_prefix)
app.include_router(api_reports, prefix=api_prefix)

# ============= Routes إضافية =============
app.include_router(api_router)  # ✅ API router العام


@app.get("/")
async def root(request: Request):
    return RedirectResponse("/login", status_code=302)


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
