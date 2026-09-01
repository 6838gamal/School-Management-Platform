"""008 — RBAC keys for spec (3) excused-leaves (deputy-only),
substitute assignments, session lifecycle, web alerts & attachments.

The teacher role MUST NOT receive excused_leaves.create (so deleting
the button alone is not enough — backend refuses).
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text
from sqlalchemy.engine.reflection import Inspector


revision: str = "0008"
down_revision: str | None = '0007'
branch_labels: str | None = None
depends_on: str | None = None


def table_exists(table_name: str) -> bool:
    """التحقق من وجود جدول في قاعدة البيانات."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    return table_name in inspector.get_table_names()


def permission_exists(conn, key: str) -> bool:
    """التحقق من وجود صلاحية معينة في قاعدة البيانات."""
    result = conn.execute(
        text("SELECT id FROM permissions WHERE key = :key"),
        {"key": key}
    )
    return result.fetchone() is not None


def role_exists(conn, key: str) -> bool:
    """التحقق من وجود دور معين في قاعدة البيانات."""
    result = conn.execute(
        text("SELECT id FROM roles WHERE key = :key"),
        {"key": key}
    )
    return result.fetchone() is not None


# (key, label_ar, label_en, group)
NEW_PERMISSIONS = [
    # Excused leaves (استئذان) - deputy-only
    ("excused_leaves.view",   "عرض الاستئذانات",        "View excused leaves",     "excused_leaves"),
    ("excused_leaves.create", "تسجيل استئذان",         "Record excused leave",    "excused_leaves"),
    ("excused_leaves.update", "تعديل استئذان",         "Update excused leave",    "excused_leaves"),
    ("excused_leaves.delete", "حذف استئذان",           "Delete excused leave",    "excused_leaves"),
    # Substitute workflow
    ("substitutes.view",        "عرض تكليفات البدلاء", "View substitutes",         "substitutes"),
    ("substitutes.create",      "تكليف معلم بديل",     "Assign substitute",       "substitutes"),
    ("substitutes.respond",     "الرد على تكليف بديل", "Respond to substitute",   "substitutes"),
    # Session lifecycle
    ("session_lifecycle.view",      "عرض حالة الحصص",  "View session lifecycle",   "session_lifecycle"),
    ("session_lifecycle.transition","تغيير حالة الحصة","Transition session",       "session_lifecycle"),
    # Timetable-linked alerts
    ("timetable_alerts.view",   "عرض إعدادات التنبيهات", "View timetable alerts", "timetable_alerts"),
    ("timetable_alerts.update", "تعديل إعدادات التنبيهات", "Update timetable alerts", "timetable_alerts"),
    # Health attachments
    ("student_attachments.view",   "عرض مرفقات الطالب", "View student attachments", "student_attachments"),
    ("student_attachments.upload", "رفع مرفقات الطالب", "Upload student attachments", "student_attachments"),
    ("student_attachments.delete",  "حذف مرفقات الطالب", "Delete student attachments", "student_attachments"),
    # Attendance extra statuses (late_arrival_minutes, excused, holiday)
    ("attendance.early_dismiss", "تسجيل انصراف مبكر للطالب", "Student early dismiss", "attendance"),
    # Audit log
    ("audit_log.view", "عرض سجل التدقيق", "View audit log", "audit"),
]


def upgrade() -> None:
    conn = op.get_bind()
    
    # التحقق من وجود الجداول
    if not table_exists('permissions'):
        print("⚠️ جدول permissions غير موجود، تخطي")
        return
    
    if not table_exists('roles'):
        print("⚠️ جدول roles غير موجود، تخطي")
        return

    # 1) Insert the new permissions
    for key, ar, en, group in NEW_PERMISSIONS:
        # التحقق من عدم وجود الصلاحية
        if permission_exists(conn, key):
            print(f"⏭️ الصلاحية موجودة بالفعل: {key}")
            continue
        
        conn.execute(
            text("""
                INSERT INTO permissions (id, key, label_ar, label_en, "group", created_at, updated_at)
                VALUES (gen_random_uuid(), :key, :ar, :en, :group, NOW(), NOW())
            """),
            {"key": key, "ar": ar, "en": en, "group": group},
        )
        print(f"✅ تم إضافة الصلاحية: {key}")

    # 2) Tie them to the right system roles via role.keys
    # Deputy → all excused_leaves + alerts + lifecycle + early_dismiss
    if role_exists(conn, 'deputy'):
        for key in (
            "excused_leaves.view", "excused_leaves.create",
            "excused_leaves.update", "excused_leaves.delete",
            "substitutes.view", "substitutes.create",
            "session_lifecycle.view", "session_lifecycle.transition",
            "timetable_alerts.view", "timetable_alerts.update",
            "student_attachments.view", "student_attachments.upload", "student_attachments.delete",
            "attendance.early_dismiss",
            "audit_log.view",
        ):
            # التحقق من وجود الصلاحية
            if not permission_exists(conn, key):
                print(f"⚠️ الصلاحية غير موجودة: {key}")
                continue
            
            conn.execute(
                text("""
                    INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
                    SELECT gen_random_uuid(), r.id, p.id, NOW(), NOW()
                    FROM roles r JOIN permissions p ON p.key = :key
                    WHERE r.key = 'deputy'
                    ON CONFLICT (role_id, permission_id) DO NOTHING
                """),
                {"key": key},
            )
            print(f"✅ تم ربط الصلاحية {key} بدور deputy")
    else:
        print("⚠️ دور deputy غير موجود")

    # Director → all of the above + view audit, attachments.view
    if role_exists(conn, 'director'):
        for key in [p[0] for p in NEW_PERMISSIONS]:
            if not permission_exists(conn, key):
                print(f"⚠️ الصلاحية غير موجودة: {key}")
                continue
            
            conn.execute(
                text("""
                    INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
                    SELECT gen_random_uuid(), r.id, p.id, NOW(), NOW()
                    FROM roles r JOIN permissions p ON p.key = :key
                    WHERE r.key = 'director'
                    ON CONFLICT (role_id, permission_id) DO NOTHING
                """),
                {"key": key},
            )
            print(f"✅ تم ربط الصلاحية {key} بدور director")
    else:
        print("⚠️ دور director غير موجود")

    # Activities manager → attachments + excuses view + audit view only
    if role_exists(conn, 'activities_manager'):
        for key in (
            "excused_leaves.view",
            "student_attachments.view", "student_attachments.upload",
            "session_lifecycle.view",
            "timetable_alerts.view",
            "audit_log.view",
        ):
            if not permission_exists(conn, key):
                print(f"⚠️ الصلاحية غير موجودة: {key}")
                continue
            
            conn.execute(
                text("""
                    INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
                    SELECT gen_random_uuid(), r.id, p.id, NOW(), NOW()
                    FROM roles r JOIN permissions p ON p.key = :key
                    WHERE r.key = 'activities_manager'
                    ON CONFLICT (role_id, permission_id) DO NOTHING
                """),
                {"key": key},
            )
            print(f"✅ تم ربط الصلاحية {key} بدور activities_manager")
    else:
        print("⚠️ دور activities_manager غير موجود")

    # Teacher → ONLY view lifecycle + respond-to-substitute (NOT excused_leaves.create)
    if role_exists(conn, 'teacher'):
        for key in (
            "excused_leaves.view",                     # can view but not create
            "substitutes.view", "substitutes.respond", # can accept/reject when assigned
            "session_lifecycle.view",
            "session_lifecycle.transition",           # to mark lesson_prepared on his own
            "student_attachments.view",
            "timetable_alerts.view",
        ):
            if not permission_exists(conn, key):
                print(f"⚠️ الصلاحية غير موجودة: {key}")
                continue
            
            conn.execute(
                text("""
                    INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
                    SELECT gen_random_uuid(), r.id, p.id, NOW(), NOW()
                    FROM roles r JOIN permissions p ON p.key = :key
                    WHERE r.key = 'teacher'
                    ON CONFLICT (role_id, permission_id) DO NOTHING
                """),
                {"key": key},
            )
            print(f"✅ تم ربط الصلاحية {key} بدور teacher")
    else:
        print("⚠️ دور teacher غير موجود")

    # CRITICAL GUARANTEE: Teacher MUST NOT have excused_leaves.create/update/delete
    # (explicit removal to assert backend enforcement regardless of seed data state)
    conn.execute(
        text("""
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions
                WHERE key IN ('excused_leaves.create','excused_leaves.update','excused_leaves.delete',
                              'attendance.early_dismiss')
            )
            AND role_id IN (SELECT id FROM roles WHERE key = 'teacher')
        """),
    )
    print("🔒 تم تأكيد حذف صلاحيات الاستئذان من دور المعلم")


def downgrade() -> None:
    conn = op.get_bind()
    
    if not table_exists('permissions'):
        print("⚠️ جدول permissions غير موجود، تخطي")
        return
    
    keys = tuple(p[0] for p in NEW_PERMISSIONS)
    
    # حذف الصلاحيات من role_permissions أولاً
    conn.execute(
        text("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE key = ANY(:keys))"),
        {"keys": list(keys)},
    )
    print("🗑️ تم حذف الصلاحيات من role_permissions")
    
    # ثم حذف الصلاحيات
    conn.execute(
        text("DELETE FROM permissions WHERE key = ANY(:keys)"),
        {"keys": list(keys)},
    )
    print("🗑️ تم حذف الصلاحيات من permissions")
    
    print("✅ تم حذف جميع الصلاحيات المضافة")
