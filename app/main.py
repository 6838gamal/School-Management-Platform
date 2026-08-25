"""
Application entry point.

Assembles the FastAPI app, mounts static files, configures Jinja2,
registers all web and API routers, and wires exception handlers.
"""
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
    schedules_router as web_schedules,
)
from app.routes.web.students import router as web_students
from app.routes.web.teachers import router as web_teachers

templates = Jinja2Templates(directory="app/templates")


async def init_database():
    """تهيئة قاعدة البيانات وإنشاء المستخدمين الأوليين."""
    print("🌱 جاري تهيئة قاعدة البيانات...")
    
    async for db in get_db():
        try:
            # 1. التحقق من وجود مدرسة
            stmt = select(School).where(School.code == "SCHOOL001")
            result = await db.execute(stmt)
            school = result.scalar_one_or_none()
            
            if not school:
                # إنشاء مدرسة
                school = School(
                    name="مدرسة النموذج",
                    code="SCHOOL001",
                    onboarding_complete=True,
                    is_active=True
                )
                db.add(school)
                await db.flush()
                print("✅ تم إنشاء المدرسة")
            
            # 2. إنشاء الصلاحيات إذا لم توجد
            for perm_def in PERMISSIONS:
                stmt = select(Permission).where(Permission.key == perm_def.key)
                result = await db.execute(stmt)
                existing_perm = result.scalar_one_or_none()
                if not existing_perm:
                    perm = Permission(
                        key=perm_def.key,
                        label_ar=perm_def.label_ar,
                        label_en=perm_def.label_en,
                        group=perm_def.group
                    )
                    db.add(perm)
            await db.flush()
            print("✅ تم إنشاء الصلاحيات")
            
            # 3. جلب جميع الصلاحيات
            stmt = select(Permission)
            result = await db.execute(stmt)
            all_perms = result.scalars().all()
            perm_dict = {p.key: p for p in all_perms}
            
            # 4. إنشاء الأدوار إذا لم توجد
            for role_key, perm_keys in ROLE_PERMISSIONS.items():
                stmt = select(Role).where(
                    Role.school_id == school.id,
                    Role.key == role_key
                )
                result = await db.execute(stmt)
                existing_role = result.scalar_one_or_none()
                
                if not existing_role:
                    role = Role(
                        school_id=school.id,
                        key=role_key,
                        name_ar=ROLE_LABELS.get(role_key, {}).get("ar", role_key),
                        name_en=ROLE_LABELS.get(role_key, {}).get("en", role_key),
                        description=f"دور {ROLE_LABELS.get(role_key, {}).get('ar', role_key)} في المدرسة",
                        is_system=True
                    )
                    db.add(role)
                    await db.flush()
                    
                    # إضافة الصلاحيات للدور
                    for perm_key in perm_keys:
                        if perm_key in perm_dict:
                            role_permission = RolePermission(
                                role_id=role.id,
                                permission_id=perm_dict[perm_key].id
                            )
                            db.add(role_permission)
            await db.flush()
            print("✅ تم إنشاء الأدوار والصلاحيات")
            
            # 5. جلب جميع الأدوار
            stmt = select(Role).where(Role.school_id == school.id)
            result = await db.execute(stmt)
            roles = result.scalars().all()
            role_dict = {r.key: r for r in roles}
            
            # 6. إنشاء المستخدمين التجريبيين (مع حذف القديمين)
            users_data = [
                {
                    "email": "admin@school.edu",
                    "password": "admin123",
                    "full_name": "أحمد المدير",
                    "role": "director"
                },
                {
                    "email": "deputy@school.edu",
                    "password": "deputy123",
                    "full_name": "خالد الوكيل",
                    "role": "deputy"
                },
                {
                    "email": "activities@school.edu",
                    "password": "activities123",
                    "full_name": "سارة الأنشطة",
                    "role": "activities_manager"
                },
                {
                    "email": "teacher@school.edu",
                    "password": "teacher123",
                    "full_name": "محمد المعلم",
                    "role": "teacher"
                }
            ]
            
            for user_data in users_data:
                # حذف المستخدم القديم إن وجد
                stmt = select(User).where(User.email == user_data["email"])
                result = await db.execute(stmt)
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    # حذف العلاقات أولاً
                    stmt = select(UserRole).where(UserRole.user_id == existing_user.id)
                    result = await db.execute(stmt)
                    user_roles = result.scalars().all()
                    for ur in user_roles:
                        await db.delete(ur)
                    await db.delete(existing_user)
                    await db.flush()
                
                # إنشاء المستخدم الجديد
                user = User(
                    email=user_data["email"],
                    password_hash=hash_password(user_data["password"]),
                    full_name=user_data["full_name"],
                    school_id=school.id,
                    is_active=True
                )
                db.add(user)
                await db.flush()
                
                # تعيين الدور للمستخدم
                if user_data["role"] in role_dict:
                    user_role = UserRole(
                        user_id=user.id,
                        role_id=role_dict[user_data["role"]].id
                    )
                    db.add(user_role)
                
                print(f"✅ تم إنشاء المستخدم: {user_data['email']}")
            
            await db.commit()
            
            # عرض الملخص
            stmt = select(User)
            result = await db.execute(stmt)
            users_count = len(result.scalars().all())
            
            stmt = select(Role)
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
    
    # تعيين القوالب
    set_templates(templates)
    
    # تهيئة قاعدة البيانات
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

app.mount("/static", StaticFiles(directory="app/static"), name="static")

register_exception_handlers(app)

# ---- Web routes ----
app.include_router(web_auth)
app.include_router(web_dashboard)
app.include_router(web_students)
app.include_router(web_teachers)
app.include_router(web_academics)
app.include_router(web_attendance)
app.include_router(web_grades)
app.include_router(web_schedules)
app.include_router(web_homework)
app.include_router(web_activities)
app.include_router(web_behavior)
app.include_router(web_notifications)
app.include_router(web_reports)

# ---- API v1 routes ----
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


@app.get("/")
async def root(request: Request):
    return RedirectResponse("/login", status_code=302)


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
