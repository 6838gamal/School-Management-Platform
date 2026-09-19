"""
Application entry point.

Assembles the FastAPI app, mounts static files, configures Jinja2,
registers all web and API routers, and wires exception handlers.

الترتيب عند بدء التشغيل:
1. إنشاء الجداول مباشرةً من الـ models (create_all) — حل احتياطي مضمون.
2. تشغيل ترحيلات Alembic (للترقيات المستقبلية).
3. إضافة الأعمدة المفقودة (ensure_database_schema).
4. تهيئة البيانات الأساسية (المستخدمين والصلاحيات).
"""
import logging
import subprocess
import sys
import os

# ============================================================
# إعداد logging
# ============================================================
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
from sqlalchemy import select, text

from app.core.config import settings
from app.core.database import engine, get_db, Base
from app.core.exceptions import register_exception_handlers
from app.core.templating import set_templates, get_templates
from app.core.security import hash_password
from app.models.users import User, Role, Permission, UserRole, RolePermission
from app.models.schools import School
from app.core.permissions import PERMISSIONS, ROLE_PERMISSIONS, ROLE_LABELS

# ============================================================
# استيراد جميع النماذج لتسجيلها في Base.metadata
# (ضروري لعمل Base.metadata.create_all)
# ============================================================
try:
    import app.models  # noqa: F401 — يستورد كل النماذج من app/models/__init__.py
except Exception as _e:
    print(f"⚠️ تعذّر استيراد app.models كحزمة: {_e}")
    # استيراد احتياطي مباشر لأهم النماذج
    try:
        from app.models.students import Student  # noqa: F401
        from app.models.teachers import Teacher  # noqa: F401
        from app.models.sections import Section  # noqa: F401
        from app.models.schedules import Schedule  # noqa: F401
        from app.models.academics import AcademicYear, Subject, Grade  # noqa: F401
        from app.models.activities import Activity, ActivityParticipant  # noqa: F401
        from app.models.attendance import StudentAttendance, TeacherAttendance  # noqa: F401
        from app.models.homework import Homework, HomeworkSubmission  # noqa: F401
        from app.models.behavior import BehaviorRecord, BehaviorCategory  # noqa: F401
        from app.models.notifications import Notification, NotificationRecipient  # noqa: F401
        from app.models.reports import ReportLink, AuditLog  # noqa: F401
    except Exception as _e2:
        print(f"⚠️ تعذّر الاستيراد الاحتياطي للنماذج: {_e2}")

# ============================================================
# استيراد API routes
# ============================================================
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

# ============================================================
# استيراد Web routes
# ============================================================
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

# ============================================================
# إنشاء مثيل templates
# ============================================================
templates = Jinja2Templates(directory="app/templates")


# ============================================================
# دالة can للقوالب
# ============================================================
def can(permission: str, request: Request = None) -> bool:
    """التحقق من أن المستخدم لديه صلاحية معينة (للاستخدام في القوالب)"""
    if request is None:
        return False
    if not hasattr(request, 'state'):
        return False
    if not hasattr(request.state, 'user') or request.state.user is None:
        return False
    if hasattr(request.state, 'permissions'):
        return permission in request.state.permissions
    return False


templates.env.globals['can'] = lambda permission: can(permission)


# ============================================================
# دوال تهيئة قاعدة البيانات
# ============================================================

async def create_tables_if_not_exist():
    """
    ✅ الحل الاحتياطي المضمون: إنشاء كل الجداول مباشرةً من الـ models.
    
    هذا يضمن وجود جميع الجداول (users, schools, students, sections,
    schedules, ...) حتى لو فشل Alembic لأي سبب.
    """
    print("🔨 جاري إنشاء الجداول إن لم تكن موجودة (create_all)...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print(f"✅ تم التأكد من وجود {len(Base.metadata.tables)} جدول")
        # عرض أسماء الجداول للتشخيص
        table_names = sorted(Base.metadata.tables.keys())
        print(f"   📋 الجداول المسجلة: {', '.join(table_names)}")
        return True
    except Exception as e:
        print(f"❌ فشل إنشاء الجداول: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_migrations():
    """
    تشغيل ترحيلات Alembic تلقائياً عند بدء التطبيق.
    ملاحظة: هذه خطوة إضافية للترقيات المستقبلية.
    """
    print("🔄 جاري تشغيل ترحيلات قاعدة البيانات...")

    original_db_url = os.environ.get("DATABASE_URL")

    try:
        db_url = original_db_url
        if not db_url:
            db_url = settings.DATABASE_URL

        # تحويل URL من asyncpg إلى psycopg2 لـ Alembic
        sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

        if '@' in sync_url:
            parts = sync_url.split('@')
            if len(parts) > 1:
                print(f"📊 استخدام قاعدة البيانات (لـ Alembic): {parts[1]}")

        os.environ["DATABASE_URL"] = sync_url

        project_dir = os.getcwd()
        alembic_ini_path = os.path.join(project_dir, "alembic.ini")

        if not os.path.exists(alembic_ini_path):
            print("⚠️ ملف alembic.ini غير موجود. تخطي تشغيل الترحيلات.")
            if original_db_url:
                os.environ["DATABASE_URL"] = original_db_url
            return False

        # التحقق من وجود مجلد versions
        versions_dir = os.path.join(project_dir, "alembic", "versions")
        if os.path.isdir(versions_dir):
            files = [f for f in os.listdir(versions_dir) if f.endswith(".py")]
            print(f"📂 عدد ملفات الترحيل: {len(files)}")
            if not files:
                print("ℹ️ لا توجد ملفات ترحيل — تخطي Alembic والاعتماد على create_all")
                if original_db_url:
                    os.environ["DATABASE_URL"] = original_db_url
                return False

        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=project_dir,
            env=os.environ.copy()
        )

        if original_db_url:
            os.environ["DATABASE_URL"] = original_db_url

        # ✅ اطبع المخرجات دائماً للتشخيص
        print(f"🔍 Alembic returncode: {result.returncode}")
        if result.stdout:
            print(f"🔍 Alembic stdout:\n{result.stdout}")
        if result.stderr:
            print(f"🔍 Alembic stderr:\n{result.stderr}")

        if result.returncode == 0:
            print("✅ تم تشغيل الترحيلات بنجاح")
            return True
        else:
            error_msg = result.stderr.strip() if result.stderr else "خطأ غير معروف"

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
                return False

    except subprocess.CalledProcessError as e:
        print(f"⚠️ خطأ في تشغيل الترحيلات: {e.stderr if e.stderr else str(e)}")
        if original_db_url:
            os.environ["DATABASE_URL"] = original_db_url
        return False
    except Exception as e:
        print(f"⚠️ خطأ غير متوقع في تشغيل الترحيلات: {str(e)}")
        import traceback
        traceback.print_exc()
        if original_db_url:
            os.environ["DATABASE_URL"] = original_db_url
        return False


async def ensure_user_exists(db, email: str, password: str, full_name: str, school_id: int, role_name: str):
    """التأكد من وجود المستخدم، وإنشائه إذا لم يكن موجوداً"""
    from app.services.auth_service import AuthService

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


async def ensure_database_schema():
    """
    التأكد من وجود جميع الأعمدة المطلوبة في قاعدة البيانات.
    هذه الدالة تضيف الأعمدة المفقودة في الجداول الموجودة.
    """
    print("🔧 جاري التحقق من هيكل قاعدة البيانات...")

    async for db in get_db():
        try:
            # 1. عمود academic_year_id في schedules
            await db.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'schedules' AND column_name = 'academic_year_id'
                    ) THEN
                        ALTER TABLE schedules ADD COLUMN academic_year_id VARCHAR(36);
                        CREATE INDEX IF NOT EXISTS ix_schedules_academic_year_id ON schedules (academic_year_id);
                        RAISE NOTICE '✅ تم إضافة academic_year_id إلى schedules';
                    END IF;
                END $$;
            """))

            # 2. عمود section_id في students
            await db.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'students' AND column_name = 'section_id'
                    ) THEN
                        ALTER TABLE students ADD COLUMN section_id VARCHAR(36) NULL;
                        CREATE INDEX IF NOT EXISTS ix_students_section_id ON students (section_id);
                        RAISE NOTICE '✅ تم إضافة section_id إلى students';
                    END IF;
                END $$;
            """))

            # 3. المفتاح الخارجي لـ section_id
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
                        RAISE NOTICE '✅ تم إضافة fk_students_section_id_sections';
                    END IF;
                END $$;
            """))

            # 4. عمود school_id في students
            await db.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'students' AND column_name = 'school_id'
                    ) THEN
                        ALTER TABLE students ADD COLUMN school_id VARCHAR(36) NULL;
                        CREATE INDEX IF NOT EXISTS ix_students_school_id ON students (school_id);
                        RAISE NOTICE '✅ تم إضافة school_id إلى students';
                    END IF;
                END $$;
            """))

            # 5. عمود is_active في students
            await db.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'students' AND column_name = 'is_active'
                    ) THEN
                        ALTER TABLE students ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
                        RAISE NOTICE '✅ تم إضافة is_active إلى students';
                    END IF;
                END $$;
            """))

            # 6. عمود code في students
            await db.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'students' AND column_name = 'code'
                    ) THEN
                        ALTER TABLE students ADD COLUMN code VARCHAR(50) NULL;
                        CREATE INDEX IF NOT EXISTS ix_students_code ON students (code);
                        RAISE NOTICE '✅ تم إضافة code إلى students';
                    END IF;
                END $$;
            """))

            # 7. عمود parent_phone في students
            await db.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'students' AND column_name = 'parent_phone'
                    ) THEN
                        ALTER TABLE students ADD COLUMN parent_phone VARCHAR(20) NULL;
                        RAISE NOTICE '✅ تم إضافة parent_phone إلى students';
                    END IF;
                END $$;
            """))

            # 8. عمود address في students
            await db.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'students' AND column_name = 'address'
                    ) THEN
                        ALTER TABLE students ADD COLUMN address TEXT NULL;
                        RAISE NOTICE '✅ تم إضافة address إلى students';
                    END IF;
                END $$;
            """))

            await db.commit()
            print("✅ تم التحقق من هيكل قاعدة البيانات بنجاح")
            break
        except Exception as e:
            print(f"⚠️ خطأ في التحقق من هيكل قاعدة البيانات: {str(e)}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            break


async def ensure_role_permissions_updated(school_id: str):
    """التأكد من أن جميع الأدوار لديها الصلاحيات المطلوبة"""
    print("🔄 جاري تحديث صلاحيات الأدوار...")

    async for db in get_db():
        try:
            stmt = select(Permission)
            result = await db.execute(stmt)
            all_perms = {p.key: p for p in result.scalars().all()}
            print(f"📊 عدد الصلاحيات الكلي: {len(all_perms)}")

            stmt = select(Role).where(Role.school_id == school_id)
            result = await db.execute(stmt)
            roles = result.scalars().all()
            print(f"📊 عدد الأدوار: {len(roles)}")

            updated_count = 0

            for role in roles:
                stmt = select(RolePermission).where(RolePermission.role_id == role.id)
                result = await db.execute(stmt)
                existing_perms = {rp.permission_id for rp in result.scalars().all()}

                required_perm_keys = ROLE_PERMISSIONS.get(role.key, [])

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
                    else:
                        print(f"   ⚠️ صلاحية '{perm_key}' غير موجودة")

                await db.flush()

            await db.commit()
            print(f"✅ تم تحديث صلاحيات الأدوار: تم إضافة {updated_count} صلاحية")
        except Exception as e:
            print(f"❌ خطأ في تحديث صلاحيات الأدوار: {str(e)}")
            import traceback
            traceback.print_exc()
            await db.rollback()
        break


async def display_database_schema():
    """استعراض كافة الجداول والأعمدة والبيانات في قاعدة البيانات"""
    print("\n" + "=" * 80)
    print("📊 استعراض هيكل قاعدة البيانات والبيانات")
    print("=" * 80)

    async for db in get_db():
        try:
            stmt = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            result = await db.execute(stmt)
            tables = [row[0] for row in result.fetchall()]

            print(f"\n📋 عدد الجداول: {len(tables)}")
            print("-" * 80)

            for table_name in tables:
                print(f"\n📌 جدول: {table_name}")
                print("-" * 40)

                stmt = text(f"""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = '{table_name}'
                    ORDER BY ordinal_position
                """)
                result = await db.execute(stmt)
                columns = result.fetchall()

                print(f"   🏷️ الأعمدة ({len(columns)}):")
                for col in columns:
                    col_name, data_type, is_nullable, default = col
                    nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
                    default_info = f" DEFAULT {default}" if default else ""
                    print(f"      • {col_name}: {data_type} [{nullable}]{default_info}")

                try:
                    stmt = text(f"SELECT COUNT(*) FROM {table_name}")
                    result = await db.execute(stmt)
                    count = result.scalar()
                    print(f"   📊 عدد السجلات: {count}")

                    if count > 0 and count <= 20:
                        print(f"   📝 البيانات:")
                        stmt = text(f"SELECT * FROM {table_name} LIMIT 5")
                        result = await db.execute(stmt)
                        rows = result.fetchall()

                        if rows:
                            col_names = [col[0] for col in columns[:5]]
                            print("      " + " | ".join(col_names))
                            print("      " + "-" * (len(" | ".join(col_names))))

                            for row in rows[:5]:
                                values = []
                                for i, val in enumerate(row[:5]):
                                    if val is None:
                                        values.append("NULL")
                                    elif isinstance(val, str) and len(str(val)) > 30:
                                        values.append(str(val)[:27] + "...")
                                    else:
                                        values.append(str(val))
                                print("      " + " | ".join(values))

                            if count > 5:
                                print(f"      ... وعرض {count - 5} سجلات أخرى")
                    elif count > 20:
                        print(f"   ℹ️ عرض البيانات مخفي (يوجد {count} سجل)")
                except Exception as e:
                    print(f"   ⚠️ لا يمكن قراءة البيانات: {str(e)}")

            print("\n" + "=" * 80)
            print("✅ اكتمل استعراض قاعدة البيانات")
            print("=" * 80 + "\n")

        except Exception as e:
            print(f"❌ خطأ في استعراض قاعدة البيانات: {str(e)}")
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

            # 2. التأكد من وجود جميع الصلاحيات
            await service.ensure_permissions_exist(school.id)

            # 3. تهيئة الصلاحيات والأدوار الأساسية
            await service.ensure_system_roles_and_permissions(school.id)
            await db.commit()
            print("✅ تم تهيئة الصلاحيات والأدوار الأساسية")

            # 4. تحديث صلاحيات الأدوار
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

            stmt = select(User)
            result = await db.execute(stmt)
            users_count = len(result.scalars().all())

            stmt = select(Role).where(Role.school_id == school.id)
            result = await db.execute(stmt)
            roles_count = len(result.scalars().all())

            stmt = select(Permission)
            result = await db.execute(stmt)
            perms_count = len(result.scalars().all())

            print("\n" + "=" * 50)
            print("🎉 تم تهيئة قاعدة البيانات بنجاح!")
            print("=" * 50)
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
            print("=" * 50 + "\n")

            await display_database_schema()

        except Exception as e:
            print(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
        break


# ============================================================
# Lifespan
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    الترتيب الصحيح:
    1. ✅ إنشاء الجداول مباشرةً من الـ models (create_all) — الحل المضمون.
    2. تشغيل ترحيلات Alembic (اختياري، للترقيات المستقبلية).
    3. إضافة الأعمدة المفقودة (ensure_database_schema).
    4. تهيئة البيانات الأساسية (المستخدمين والصلاحيات).
    """
    print("🚀 Starting application...")
    print(f"📊 Database: {settings.DATABASE_URL}")

    set_templates(templates)
    print("✅ تم تعيين القوالب للتطبيق")

    if get_templates() is None:
        print("❌ فشل تعيين templates!")
    else:
        print(f"✅ تم تأكيد تعيين templates: {get_templates() is not None}")

    # ============================================================
    # الخطوة 1: ✅ إنشاء الجداول مباشرةً من الـ models (الحل المضمون)
    # ============================================================
    await create_tables_if_not_exist()

    # ============================================================
    # الخطوة 2: ترحيلات Alembic (اختياري)
    # ============================================================
    await run_migrations()

    # ============================================================
    # الخطوة 3: إضافة الأعمدة المفقودة
    # ============================================================
    await ensure_database_schema()

    # ============================================================
    # الخطوة 4: تهيئة البيانات
    # ============================================================
    await init_database()

    print("✅ التطبيق جاهز للاستخدام!")
    yield

    # ============================================================
    # إيقاف التطبيق
    # ============================================================
    print("🛑 Shutting down application...")
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
# Spec features (Sessions 1-12)
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
