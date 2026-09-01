"""008 — RBAC keys for spec (3) excused-leaves (deputy-only),
substitute assignments, session lifecycle, web alerts & attachments.

The teacher role MUST NOT receive excused_leaves.create (so deleting
the button alone is not enough — backend refuses).
"""
revision: str = '0008'
down_revision: Union[str, None] = None


from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "0008"
down_revision: str | None = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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

    # 1) Insert the new permissions
    for key, ar, en, group in NEW_PERMISSIONS:
        conn.execute(
            text("""
                INSERT INTO permissions (id, key, label_ar, label_en, "group", created_at, updated_at)
                VALUES (UUID(), :key, :ar, :en, :group, NOW(), NOW())
                ON CONFLICT (key) DO NOTHING
            """),
            {"key": key, "ar": ar, "en": en, "group": group},
        )

    # 2) Tie them to the right system roles via role.keys
    # Deputy → all excused_leaves + alerts + lifecycle + early_dismiss
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
        conn.execute(
            text("""
                INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
                SELECT UUID(), r.id, p.id, NOW(), NOW()
                FROM roles r JOIN permissions p ON p.key = :key
                WHERE r.key = 'deputy'
                ON CONFLICT DO NOTHING
            """),
            {"key": key},
        )

    # Director → all of the above + view audit, attachments.view
    for key in list(NEW_PERMISSIONS[0][0] for _ in [0]) + [p[0] for p in NEW_PERMISSIONS]:
        conn.execute(
            text("""
                INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
                SELECT UUID(), r.id, p.id, NOW(), NOW()
                FROM roles r JOIN permissions p ON p.key = :key
                WHERE r.key = 'director'
                ON CONFLICT DO NOTHING
            """),
            {"key": key},
        )

    # Activities manager → attachments + excuses view + audit view only
    for key in (
        "excused_leaves.view",
        "student_attachments.view", "student_attachments.upload",
        "session_lifecycle.view",
        "timetable_alerts.view",
        "audit_log.view",
    ):
        conn.execute(
            text("""
                INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
                SELECT UUID(), r.id, p.id, NOW(), NOW()
                FROM roles r JOIN permissions p ON p.key = :key
                WHERE r.key = 'activities_manager'
                ON CONFLICT DO NOTHING
            """),
            {"key": key},
        )

    # Teacher → ONLY view lifecycle + respond-to-substitute (NOT excused_leaves.create)
    for key in (
        "excused_leaves.view",                     # can view but not create
        "substitutes.view", "substitutes.respond", # can accept/reject when assigned
        "session_lifecycle.view",
        "session_lifecycle.transition",           # to mark lesson_prepared on his own
        "student_attachments.view",
        "timetable_alerts.view",
    ):
        conn.execute(
            text("""
                INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
                SELECT UUID(), r.id, p.id, NOW(), NOW()
                FROM roles r JOIN permissions p ON p.key = :key
                WHERE r.key = 'teacher'
                ON CONFLICT DO NOTHING
            """),
            {"key": key},
        )

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


def downgrade() -> None:
    conn = op.get_bind()
    keys = tuple(p[0] for p in NEW_PERMISSIONS)
    conn.execute(
        text("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE key = ANY(:keys))"),
        {"keys": list(keys)},
    )
    conn.execute(
        text("DELETE FROM permissions WHERE key = ANY(:keys)"),
        {"keys": list(keys)},
    )
