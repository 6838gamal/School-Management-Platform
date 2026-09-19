import os
import sys
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from alembic import context

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.database import Base
from app.core.config import settings

# ============================================================
# استيراد جميع النماذج — تأكد أن كل جدول موجود هنا
# ============================================================
from app.models.users import User, Role, Permission, UserRole, RolePermission
from app.models.schools import School                          # ← أزل التعليق
from app.models.academics import AcademicYear, Subject, Grade
from app.models.activities import Activity, ActivityParticipant
from app.models.attendance import StudentAttendance, TeacherAttendance
from app.models.homework import Homework, HomeworkSubmission
from app.models.behavior import BehaviorRecord, BehaviorCategory
from app.models.notifications import Notification, NotificationRecipient
from app.models.reports import ReportLink, AuditLog
from app.models.teachers import Teacher
from app.models.students import Student

# ============================================================
# استيراد النماذج الناقصة — تحقق من المسارات الصحيحة عندك
# ============================================================
try:
    from app.models.sections import Section
except ImportError:
    print("⚠️ app.models.sections غير موجود — تحقق من المسار")
    Section = None

try:
    from app.models.schedules import Schedule
except ImportError:
    print("⚠️ app.models.schedules غير موجود — تحقق من المسار")
    Schedule = None

# أضف أي جداول أخرى (excused_leaves, substitutes, ...) هنا بنفس الطريقة

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_sync_url():
    url = os.environ.get("DATABASE_URL")
    if not url:
        url = settings.DATABASE_URL
    if "asyncpg" in url:
        url = url.replace("postgresql+asyncpg://", "postgresql://")
    return url


def run_migrations_offline() -> None:
    url = get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    sync_url = get_sync_url()
    connectable = create_engine(
        sync_url,
        poolclass=pool.NullPool,
        pool_pre_ping=True,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # ← عطّل هذه مؤقتاً حتى تعمل الترحيلات الأولى
            compare_type=False,
            compare_server_default=False,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
