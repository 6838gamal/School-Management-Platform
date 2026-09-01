"""
Application entry point.

Assembles the FastAPI app, mounts static files, configures Jinja2,
registers all web and API routers, and wires exception handlers.
"""
import logging
import subprocess
import sys
import os

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
from app.routes.web.grades import router as grades_router

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


# ============================================================
# دوال تهيئة قاعدة البيانات
# ============================================================

async def run_migrations():
    """
    تشغيل ترحيلات Alembic تلقائياً عند بدء التطبيق
    
    هذه الدالة تقوم بتشغيل جميع الترحيلات المعلقة لتحديث هيكل قاعدة البيانات
    إلى أحدث إصدار. يتم تشغيلها مرة واحدة عند بدء التطبيق.
    """
    print("🔄 جاري تشغيل ترحيلات قاعدة البيانات...")
    
    # حفظ URL الأصلي
    original_db_url = os.environ.get("DATABASE_URL")
    
    try:
        # الحصول على DATABASE_URL من متغيرات البيئة أو الإعدادات
        db_url = original_db_url
        if not db_url:
            db_url = settings.DATABASE_URL
        
        # تحويل URL من asyncpg إلى psycopg2 لـ Alembic
        # Alembic لا يدعم asyncpg، لذلك نحتاج إلى استخدام psycopg2
        sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        
        # طباعة معلومات للتتبع (مع إخفاء كلمة المرور)
        if '@' in sync_url:
            parts = sync_url.split('@')
            if len(parts) > 1:
                print(f"📊 استخدام قاعدة البيانات (لـ Alembic): {parts[1]}")
        
        # تعيين DATABASE_URL في متغيرات البيئة ليستخدمها alembic.ini
        os.environ["DATABASE_URL"] = sync_url
        
        # الحصول على مسار المشروع
        project_dir = os.getcwd()
        alembic_ini_path = os.path.join(project_dir, "alembic.ini")
        
        # التحقق من وجود ملف alembic.ini
        if not os.path.exists(alembic_ini_path):
            print("⚠️ ملف alembic.ini غير موجود. تخطي تشغيل الترحيلات.")
            # استعادة URL الأصلي
            if original_db_url:
                os.environ["DATABASE_URL"] = original_db_url
            return False
        
        # تشغيل alembic upgrade head باستخدام subprocess
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=project_dir,
            env=os.environ.copy()
        )
        
        # استعادة URL الأصلي
        if original_db_url:
            os.environ["DATABASE_URL"] = original_db_url
        
        if result.returncode == 0:
            print("✅ تم تشغيل الترحيلات بنجاح")
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines[-5:]:  # عرض آخر 5 أسطر فقط
                    if line.strip():
                        print(f"   {line}")
            return True
        else:
            # قد يكون الخطأ بسبب عدم وجود ترحيلات جديدة
            error_msg = result.stderr.strip() if result.stderr else "خطأ غير معروف"
            
            # أخطاء شائعة غير حرجة
            if "No such revision" in error_msg:
                print("ℹ️ قاعدة البيانات محدثة بالفعل (لا توجد ترحيلات جديدة)")
                return True
            elif "target database is not up to date" in error_msg:
                print("ℹ️ قاعدة البيانات محدثة بالفعل")
                return True
            elif "No migration" in error_msg:
                print("ℹ️ لا توجد ترحيلات جديدة")
                return True
            else:
                print(f"⚠️ فشل تشغيل الترحيلات: {error_msg}")
                # لا نوقف التطبيق، نكمل بـ ensure_database_schema
                return False
            
    except subprocess.CalledProcessError as e:
        print(f"⚠️ خطأ في تشغيل الترحيلات (قد تكون الترحيلات مطبقة بالفعل): {e.stderr if e.stderr else str(e)}")
        # استعادة URL الأصلي
        if original_db_url:
            os.environ["DATABASE_URL"] = original_db_url
        return False
    except Exception as e:
        print(f"⚠️ خطأ غير متوقع في تشغيل الترحيلات: {str(e)}")
        # استعادة URL الأصلي
        if original_db_url:
            os.environ["DATABASE_URL"] = original_db_url
        # نكمل التطبيق ولا نوقفه
        return False


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
    """
    التأكد من وجود جميع الأعمدة المطلوبة في قاعدة البيانات
    
    هذه الدالة تضيف الأعمدة المفقودة في الجداول الموجودة
    لتجنب أخطاء SQLAlchemy عند تشغيل التطبيق.
    """
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
            
            # 2. التحقق من وجود عمود section_id في جدول students
            await db.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'students' AND column_name = 'section_id'
                    ) THEN
                        ALTER TABLE students ADD COLUMN section_id VARCHAR(36) NULL;
                        CREATE INDEX IF NOT EXISTS ix_students_section_id ON students (section_id);
                        RAISE NOTICE '✅ تم إضافة العمود section_id إلى جدول students';
                    ELSE
                        RAISE NOTICE 'ℹ️ العمود section_id موجود بالفعل في جدول students';
                    END IF;
                END $$;
            """))
            
            # 3. إضافة المفتاح الخارجي للـ section_id
            await db.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints 
                        WHERE table_name = 'students' 
                        AND constraint_name = 'fk_students_section_id_sections'
                    ) THEN
                        ALTER TABLE students 
                        ADD CONSTRAINT fk_students_section_id_sections 
                        FOREIGN KEY (section_id) 
                        REFERENCES sections(id) 
                        ON DELETE SET NULL;
                        RAISE NOTICE '✅ تم إضافة المفتاح الخارجي fk_students_section_id_sections';
                    ELSE
                        RAISE NOTICE 'ℹ️ المفتاح الخارجي fk_students_section_id_sections موجود بالفعل';
                    END IF;
                END $$;
            """))
            
            # 4. التحقق من وجود عمود school_id في جدول students
            await db.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'students' AND column_name = 'school_id'
                    ) THEN
                        ALTER TABLE students ADD COLUMN school_id VARCHAR(36) NULL;
                        CREATE INDEX IF NOT EXISTS ix_students_school_id ON students (school_id);
                        RAISE NOTICE '✅ تم إضافة العمود school_id إلى جدول students';
                    ELSE
                        RAISE NOTICE 'ℹ️ العمود school_id موجود بالفعل في جدول students';
                    END IF;
                END $$;
            """))
            
            # 5. التحقق من وجود عمود is_active في جدول students
            await db.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'students' AND column_name = 'is_active'
                    ) THEN
                        ALTER TABLE students ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
                        RAISE NOTICE '✅ تم إضافة العمود is_active إلى جدول students';
                    ELSE
                        RAISE NOTICE 'ℹ️ العمود is_active موجود بالفعل في جدول students';
                    END IF;
                END $$;
            """))
            
            # 6. التحقق من وجود عمود code في جدول students
            await db.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'students' AND column_name = 'code'
                    ) THEN
                        ALTER TABLE students ADD COLUMN code VARCHAR(50) NULL;
                        CREATE INDEX IF NOT EXISTS ix_students_code ON students (code);
                        RAISE NOTICE '✅ تم إضافة العمود code إلى جدول students';
                    ELSE
                        RAISE NOTICE 'ℹ️ العمود code موجود بالفعل في جدول students';
                    END IF;
                END $$;
            """))
            
            # 7. التحقق من وجود عمود parent_phone في جدول students
            await db.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'students' AND column_name = 'parent_phone'
                    ) THEN
                        ALTER TABLE students ADD COLUMN parent_phone VARCHAR(20) NULL;
                        RAISE NOTICE '✅ تم إضافة العمود parent_phone إلى جدول students';
                    ELSE
                        RAISE NOTICE 'ℹ️ العمود parent_phone موجود بالفعل في جدول students';
                    END IF;
                END $$;
            """))
            
            # 8. التحقق من وجود عمود address في جدول students
            await db.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'students' AND column_name = 'address'
                    ) THEN
                        ALTER TABLE students ADD COLUMN address TEXT NULL;
                        RAISE NOTICE '✅ تم إضافة العمود address إلى جدول students';
                    ELSE
                        RAISE NOTICE 'ℹ️ العمود address موجود بالفعل في جدول students';
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


# ============================================================
# Lifespan
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    
    يتم تشغيل هذا الكود عند بدء التطبيق وإيقافه.
    الترتيب:
    1. تشغيل ترحيلات Alembic (تحديث هيكل قاعدة البيانات)
    2. التحقق من هيكل قاعدة البيانات (إضافة الأعمدة المفقودة)
    3. تهيئة البيانات الأساسية (المستخدمين والصلاحيات)
    4. إغلاق اتصال قاعدة البيانات عند الإيقاف
    """
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
    
    # ============================================================
    # الخطوة 1: تشغيل ترحيلات Alembic
    # ============================================================
    await run_migrations()
    
    # ============================================================
    # الخطوة 2: التحقق من هيكل قاعدة البيانات (إضافة الأعمدة المفقودة)
    # ============================================================
    await ensure_database_schema()
    
    # ============================================================
    # الخطوة 3: تهيئة قاعدة البيانات (المستخدمين والصلاحيات)
    # ============================================================
    await init_database()
    
    print("✅ التطبيق جاهز للاستخدام!")
    yield
    
    # ============================================================
    # إيقاف التطبيق
    # ============================================================
    print("🛑 Shutting down application...")
    
    # إغلاق اتصال قاعدة البيانات عند الإيقاف
    await engine.dispose()
    print("✅ Database connection closed.")


# ============================================================
# إنشاء التطبيق
# ============================================================

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
app.include_router(grades_router)

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
    """إعادة توجيه الصفحة الرئيسية إلى صفحة تسجيل الدخول"""
    return RedirectResponse("/login", status_code=302)


@app.get("/health")
async def health():
    """فحص صحة التطبيق"""
    return {"status": "ok", "app": settings.APP_NAME}


# ============================================================
# Spec features (Sessions 1-12): dashboard, excused-leaves,
# substitutes, student profile, attendance late/absent,
# timetable alerts, session lifecycle API.
# ============================================================
try:
    from app.routes.web.deputy_dashboard import router as web_deputy_dashboard
    from app.routes.web.excused_leaves import router as web_excused_leaves
    from app.routes.web.substitutes import router as web_substitutes
    from app.routes.web.student_profile import router as web_student_profile
    from app.routes.web.timetable_alerts import router as web_timetable_alerts
    from app.routes.api.v1.attendance import router as api_attendance_v2
    from app.routes.api.v1.session_lifecycle import router as api_lifecycle
    from app.routes.api.v1.substitutes import router as api_substitutes_v2

    app.include_router(web_deputy_dashboard)
    app.include_router(web_excused_leaves)
    app.include_router(web_substitutes)
    app.include_router(web_student_profile)
    app.include_router(web_timetable_alerts)
    app.include_router(api_attendance_v2, prefix="/api/v1")
    app.include_router(api_lifecycle, prefix="/api/v1")
    app.include_router(api_substitutes_v2, prefix="/api/v1")
except Exception as e:
    import logging
    logging.getLogger("app.main").warning(
        "spec routes not all loaded: %s", e
    )


# ============================================================
# تشغيل التطبيق (للتطوير المحلي)
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
