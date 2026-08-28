"""
Permission catalog and helper functions.

Permissions are string keys grouped by resource. They are stored in the
``permissions`` table and linked to roles through ``role_permissions``.

The catalog below is the single source of truth — it is used to seed the
database on first run and to drive template-level permission checks.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionDef:
    key: str
    label_ar: str
    label_en: str
    group: str


# ------------------------------------------------------------------
# Catalog — extend this list to add new permissions.
# ------------------------------------------------------------------
PERMISSIONS: list[PermissionDef] = [
    # Schools
    PermissionDef("schools.view", "عرض المدرسة", "View school", "schools"),
    PermissionDef("schools.update", "تعديل بيانات المدرسة", "Update school", "schools"),
    
    # Academic structure
    PermissionDef("academics.view", "عرض الهيكل الأكاديمي", "View academic structure", "academics"),
    PermissionDef("academics.create", "إنشاء عناصر أكاديمية", "Create academic items", "academics"),
    PermissionDef("academics.update", "تعديل عناصر أكاديمية", "Update academic items", "academics"),
    PermissionDef("academics.delete", "حذف عناصر أكاديمية", "Delete academic items", "academics"),
    
    # Users
    PermissionDef("users.view", "عرض المستخدمين", "View users", "users"),
    PermissionDef("users.create", "إنشاء مستخدم", "Create user", "users"),
    PermissionDef("users.update", "تعديل مستخدم", "Update user", "users"),
    PermissionDef("users.delete", "حذف مستخدم", "Delete user", "users"),
    PermissionDef("users.assign_role", "تعيين دور لمستخدم", "Assign role to user", "users"),
    
    # Deputy (وكلاء المدرسة)
    PermissionDef("deputy.view", "عرض الوكلاء", "View deputies", "deputy"),
    PermissionDef("deputy.create", "إنشاء وكيل", "Create deputy", "deputy"),
    PermissionDef("deputy.update", "تعديل وكيل", "Update deputy", "deputy"),
    PermissionDef("deputy.delete", "حذف وكيل", "Delete deputy", "deputy"),
    
    # Activity Managers (مديرو الأنشطة)
    PermissionDef("activity_managers.view", "عرض مديري الأنشطة", "View activity managers", "activity_managers"),
    PermissionDef("activity_managers.create", "إنشاء مدير نشاط", "Create activity manager", "activity_managers"),
    PermissionDef("activity_managers.update", "تعديل مدير نشاط", "Update activity manager", "activity_managers"),
    PermissionDef("activity_managers.delete", "حذف مدير نشاط", "Delete activity manager", "activity_managers"),
    
    # Students
    PermissionDef("students.view", "عرض الطلاب", "View students", "students"),
    PermissionDef("students.create", "إضافة طالب", "Create student", "students"),
    PermissionDef("students.update", "تعديل طالب", "Update student", "students"),
    PermissionDef("students.delete", "حذف طالب", "Delete student", "students"),
    PermissionDef("students.transfer", "نقل طالب", "Transfer student", "students"),
    
    # Teachers
    PermissionDef("teachers.view", "عرض المعلمين", "View teachers", "teachers"),
    PermissionDef("teachers.create", "إضافة معلم", "Create teacher", "teachers"),
    PermissionDef("teachers.update", "تعديل معلم", "Update teacher", "teachers"),
    PermissionDef("teachers.assign", "تكليف معلم", "Assign teacher", "teachers"),
    
    # Schedules
    PermissionDef("schedules.view", "عرض الجداول", "View schedules", "schedules"),
    PermissionDef("schedules.create", "إنشاء جدول", "Create schedule", "schedules"),
    PermissionDef("schedules.update", "تعديل جدول", "Update schedule", "schedules"),
    PermissionDef("schedules.delete", "حذف جدول", "Delete schedule", "schedules"),
    
    # Attendance
    PermissionDef("attendance.view", "عرض الحضور", "View attendance", "attendance"),
    PermissionDef("attendance.create", "تسجيل الحضور", "Create attendance", "attendance"),
    PermissionDef("attendance.update", "تعديل الحضور", "Update attendance", "attendance"),
    
    # Grades
    PermissionDef("grades.view", "عرض الدرجات", "View grades", "grades"),
    PermissionDef("grades.create", "إدخال الدرجات", "Create grades", "grades"),
    PermissionDef("grades.update", "تعديل الدرجات", "Update grades", "grades"),
    PermissionDef("grades.delete", "حذف الدرجات", "Delete grades", "grades"),
    
    # Homework
    PermissionDef("homework.view", "عرض الواجبات", "View homework", "homework"),
    PermissionDef("homework.create", "إنشاء واجب", "Create homework", "homework"),
    PermissionDef("homework.update", "تعديل واجب", "Update homework", "homework"),
    PermissionDef("homework.delete", "حذف واجب", "Delete homework", "homework"),
    
    # Activities
    PermissionDef("activities.view", "عرض الأنشطة", "View activities", "activities"),
    PermissionDef("activities.create", "إنشاء نشاط", "Create activity", "activities"),
    PermissionDef("activities.update", "تعديل نشاط", "Update activity", "activities"),
    PermissionDef("activities.delete", "حذف نشاط", "Delete activity", "activities"),
    
    # Behavior
    PermissionDef("behavior.view", "عرض السلوك", "View behavior", "behavior"),
    PermissionDef("behavior.create", "تسجيل سلوك", "Create behavior record", "behavior"),
    PermissionDef("behavior.update", "تعديل سلوك", "Update behavior record", "behavior"),
    PermissionDef("behavior.delete", "حذف سلوك", "Delete behavior record", "behavior"),
    
    # Notifications
    PermissionDef("notifications.view", "عرض الإشعارات", "View notifications", "notifications"),
    PermissionDef("notifications.create", "إرسال إشعار", "Send notification", "notifications"),
    PermissionDef("notifications.manage", "إدارة الإشعارات", "Manage notifications", "notifications"),
    
    # Reports
    PermissionDef("reports.view", "عرض التقارير", "View reports", "reports"),
    PermissionDef("reports.generate", "إنشاء تقرير", "Generate report", "reports"),
    PermissionDef("reports.share", "مشاركة تقرير", "Share report", "reports"),
    
    # Settings
    PermissionDef("settings.view", "عرض الإعدادات", "View settings", "settings"),
    PermissionDef("settings.update", "تعديل الإعدادات", "Update settings", "settings"),
]

PERMISSION_KEYS: list[str] = [p.key for p in PERMISSIONS]
_PERMISSIONS_BY_KEY: dict[str, PermissionDef] = {p.key: p for p in PERMISSIONS}


def permission_label(key: str, lang: str = "ar") -> str:
    p = _PERMISSIONS_BY_KEY.get(key)
    if not p:
        return key
    return p.label_ar if lang == "ar" else p.label_en


# ------------------------------------------------------------------
# Role → default permission mapping (used during seeding).
# ------------------------------------------------------------------
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "director": [
        # جميع صلاحيات المدير (كاملة)
        "schools.view", "schools.update",
        "academics.view", "academics.create", "academics.update", "academics.delete",
        "users.view", "users.create", "users.update", "users.delete", "users.assign_role",
        "deputy.view", "deputy.create", "deputy.update", "deputy.delete",
        "activity_managers.view", "activity_managers.create", "activity_managers.update", "activity_managers.delete",
        "students.view", "students.create", "students.update", "students.delete", "students.transfer",
        "teachers.view", "teachers.create", "teachers.update", "teachers.assign",
        "schedules.view", "schedules.create", "schedules.update", "schedules.delete",
        "attendance.view", "attendance.create", "attendance.update",
        "grades.view", "grades.create", "grades.update", "grades.delete",
        "homework.view", "homework.create", "homework.update", "homework.delete",
        "activities.view", "activities.create", "activities.update", "activities.delete",
        "behavior.view", "behavior.create", "behavior.update", "behavior.delete",
        "notifications.view", "notifications.create", "notifications.manage",
        "reports.view", "reports.generate", "reports.share",
        "settings.view", "settings.update",
    ],
    "deputy": [
        # صلاحيات الوكيل (نفس صلاحيات المدير)
        "schools.view", "schools.update",
        "academics.view", "academics.create", "academics.update", "academics.delete",
        "users.view", "users.create", "users.update", "users.delete", "users.assign_role",
        "deputy.view", "deputy.create", "deputy.update", "deputy.delete",
        "activity_managers.view", "activity_managers.create", "activity_managers.update", "activity_managers.delete",
        "students.view", "students.create", "students.update", "students.delete", "students.transfer",
        "teachers.view", "teachers.create", "teachers.update", "teachers.assign",
        "schedules.view", "schedules.create", "schedules.update", "schedules.delete",
        "attendance.view", "attendance.create", "attendance.update",
        "grades.view", "grades.create", "grades.update", "grades.delete",
        "homework.view", "homework.create", "homework.update", "homework.delete",
        "activities.view", "activities.create", "activities.update", "activities.delete",
        "behavior.view", "behavior.create", "behavior.update", "behavior.delete",
        "notifications.view", "notifications.create", "notifications.manage",
        "reports.view", "reports.generate", "reports.share",
        "settings.view", "settings.update",
    ],
    "activities_manager": [
        "schools.view",
        "academics.view",
        "users.view",
        "activity_managers.view",
        "students.view", "students.update",
        "activities.view", "activities.create", "activities.update", "activities.delete",
        "behavior.view", "behavior.create", "behavior.update", "behavior.delete",
        "notifications.view", "notifications.create",
        "reports.view", "reports.generate",
    ],
    "teacher": [
        "schools.view",
        "academics.view",
        "students.view",
        "schedules.view",
        "attendance.view", "attendance.create", "attendance.update",
        "grades.view", "grades.create", "grades.update",
        "homework.view", "homework.create", "homework.update", "homework.delete",
        "activities.view",
        "behavior.view",
        "notifications.view",
        "reports.view",
    ],
}


ROLE_LABELS: dict[str, dict[str, str]] = {
    "director": {"ar": "مدير", "en": "Director"},
    "deputy": {"ar": "وكيل", "en": "Deputy Director"},
    "activities_manager": {"ar": "مسؤول الأنشطة", "en": "Activities Manager"},
    "teacher": {"ar": "معلم", "en": "Teacher"},
}
