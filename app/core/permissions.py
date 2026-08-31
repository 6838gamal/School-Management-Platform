"""Permission catalog (extended with 008 features).

This file is the single source of truth for the catalog used at runtime
and at seed time. Migration 008 mirrors the keys into PostgreSQL.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionDef:
    key: str
    label_ar: str
    label_en: str
    group: str


PERMISSIONS: list[PermissionDef] = [
    PermissionDef("schools.view",        "عرض المدرسة",          "View school",                  "schools"),
    PermissionDef("schools.update",      "تعديل بيانات المدرسة",  "Update school",                "schools"),

    PermissionDef("academics.view",      "عرض الهيكل الأكاديمي",  "View academic structure",      "academics"),
    PermissionDef("academics.create",    "إنشاء عناصر أكاديمية", "Create academic items",        "academics"),
    PermissionDef("academics.update",    "تعديل عناصر أكاديمية",  "Update academic items",        "academics"),
    PermissionDef("academics.delete",    "حذف عناصر أكاديمية",   "Delete academic items",         "academics"),

    PermissionDef("users.view",          "عرض المستخدمين",       "View users",                   "users"),
    PermissionDef("users.create",        "إنشاء مستخدم",         "Create user",                  "users"),
    PermissionDef("users.update",        "تعديل مستخدم",         "Update user",                  "users"),
    PermissionDef("users.delete",        "حذف مستخدم",           "Delete user",                  "users"),
    PermissionDef("users.assign_role",  "تعيين دور لمستخدم",   "Assign role to user",          "users"),

    PermissionDef("deputy.view",         "عرض الوكلاء",         "View deputies",                "deputy"),
    PermissionDef("deputy.create",       "إنشاء وكيل",           "Create deputy",                "deputy"),
    PermissionDef("deputy.update",       "تعديل وكيل",           "Update deputy",                "deputy"),
    PermissionDef("deputy.delete",       "حذف وكيل",             "Delete deputy",                "deputy"),

    PermissionDef("activity_managers.view",   "عرض مديري الأنشطة",     "View activity managers", "activity_managers"),
    PermissionDef("activity_managers.create", "إنشاء مدير نشاط",       "Create activity manager","activity_managers"),
    PermissionDef("activity_managers.update", "تعديل مدير نشاط",       "Update activity manager","activity_managers"),
    PermissionDef("activity_managers.delete", "حذف مدير نشاط",        "Delete activity manager","activity_managers"),

    PermissionDef("students.view",       "عرض الطلاب",          "View students",                "students"),
    PermissionDef("students.create",     "إضافة طالب",          "Create student",               "students"),
    PermissionDef("students.update",     "تعديل طالب",          "Update student",               "students"),
    PermissionDef("students.delete",     "حذف طالب",            "Delete student",               "students"),
    PermissionDef("students.transfer",   "نقل طالب",            "Transfer student",             "students"),

    PermissionDef("teachers.view",       "عرض المعلمين",        "View teachers",                "teachers"),
    PermissionDef("teachers.create",     "إضافة معلم",          "Create teacher",               "teachers"),
    PermissionDef("teachers.update",     "تعديل معلم",          "Update teacher",               "teachers"),
    PermissionDef("teachers.assign",     "تكليف معلم",          "Assign teacher",               "teachers"),

    PermissionDef("schedules.view",      "عرض الجداول",         "View schedules",               "schedules"),
    PermissionDef("schedules.create",    "إنشاء جدول",          "Create schedule",              "schedules"),
    PermissionDef("schedules.update",    "تعديل جدول",          "Update schedule",              "schedules"),
    PermissionDef("schedules.delete",    "حذف جدول",            "Delete schedule",              "schedules"),

    PermissionDef("attendance.view",     "عرض الحضور",          "View attendance",              "attendance"),
    PermissionDef("attendance.create",   "تسجيل حضور",          "Create attendance",            "attendance"),
    PermissionDef("attendance.update",   "تعديل حضور",          "Update attendance",            "attendance"),
    PermissionDef("attendance.delete",   "حذف حضور",            "Delete attendance",            "attendance"),
    PermissionDef("attendance.early_dismiss", "تسجيل انصراف مبكر", "Student early dismiss",     "attendance"),

    PermissionDef("grades.view",         "عرض الدرجات",         "View grades",                  "grades"),
    PermissionDef("grades.create",       "إضافة درجة",          "Create grade",                 "grades"),
    PermissionDef("grades.update",       "تعديل درجة",          "Update grade",                 "grades"),

    PermissionDef("homework.view",       "عرض الواجبات",        "View homework",                "homework"),
    PermissionDef("homework.create",     "إضافة واجب",          "Create homework",              "homework"),
    PermissionDef("homework.update",     "تعديل واجب",          "Update homework",              "homework"),
    PermissionDef("homework.delete",     "حذف واجب",            "Delete homework",              "homework"),

    PermissionDef("activities.view",     "عرض الأنشطة",         "View activities",              "activities"),
    PermissionDef("activities.create",   "إنشاء نشاط",          "Create activity",              "activities"),
    PermissionDef("activities.update",   "تعديل نشاط",          "Update activity",              "activities"),
    PermissionDef("activities.delete",   "حذف نشاط",            "Delete activity",              "activities"),

    PermissionDef("behavior.view",       "عرض السلوك",          "View behavior",                "behavior"),
    PermissionDef("behavior.create",     "تسجيل سلوك",          "Create behavior",              "behavior"),
    PermissionDef("behavior.update",     "تعديل سلوك",          "Update behavior",              "behavior"),
    PermissionDef("behavior.delete",     "حذف سلوك",            "Delete behavior",              "behavior"),

    PermissionDef("notifications.view",  "عرض الإشعارات",       "View notifications",           "notifications"),
    PermissionDef("notifications.create","إنشاء إشعار",         "Create notification",          "notifications"),

    PermissionDef("reports.view",        "عرض التقارير",        "View reports",                 "reports"),
    PermissionDef("reports.generate",    "إنشاء تقرير",         "Generate report",              "reports"),
    PermissionDef("reports.share",       "مشاركة تقرير",        "Share report",                 "reports"),

    PermissionDef("settings.view",       "عرض الإعدادات",        "View settings",                "settings"),
    PermissionDef("settings.update",     "تعديل الإعدادات",      "Update settings",              "settings"),

    # ───── 008 additions ─────
    PermissionDef("excused_leaves.view",       "عرض الاستئذانات",     "View excused leaves",      "excused_leaves"),
    PermissionDef("excused_leaves.create",     "تسجيل استئذان",      "Record excused leave",     "excused_leaves"),
    PermissionDef("excused_leaves.update",     "تعديل استئذان",       "Update excused leave",     "excused_leaves"),
    PermissionDef("excused_leaves.delete",     "حذف استئذان",         "Delete excused leave",     "excused_leaves"),

    PermissionDef("substitutes.view",          "عرض تكليفات البدلاء","View substitutes",          "substitutes"),
    PermissionDef("substitutes.create",        "تكليف معلم بديل",    "Assign substitute",        "substitutes"),
    PermissionDef("substitutes.respond",       "الرد على تكليف بديل","Respond to substitute",    "substitutes"),

    PermissionDef("session_lifecycle.view",        "عرض حالة الحصص",  "View session lifecycle",  "session_lifecycle"),
    PermissionDef("session_lifecycle.transition",  "تغيير حالة الحصة","Transition session",      "session_lifecycle"),

    PermissionDef("timetable_alerts.view",   "عرض إعدادات التنبيهات",  "View timetable alerts",   "timetable_alerts"),
    PermissionDef("timetable_alerts.update", "تعديل إعدادات التنبيهات","Update timetable alerts","timetable_alerts"),

    PermissionDef("student_attachments.view",   "عرض مرفقات الطالب", "View student attachments",   "student_attachments"),
    PermissionDef("student_attachments.upload", "رفع مرفقات الطالب", "Upload student attachments","student_attachments"),
    PermissionDef("student_attachments.delete", "حذف مرفقات الطالب", "Delete student attachments","student_attachments"),

    PermissionDef("audit_log.view", "عرض سجل التدقيق", "View audit log", "audit"),
]


ROLE_PERMISSIONS: dict[str, list[str]] = {
    "director": [p.key for p in PERMISSIONS],  # everything
    "deputy": [
        "schools.view",
        "academics.view", "academics.create", "academics.update",
        "users.view", "users.create", "users.update",
        "deputy.view",
        "activity_managers.view",
        "students.view", "students.create", "students.update", "students.transfer",
        "teachers.view", "teachers.create", "teachers.update", "teachers.assign",
        "schedules.view", "schedules.create", "schedules.update", "schedules.delete",
        "attendance.view", "attendance.create", "attendance.update", "attendance.delete", "attendance.early_dismiss",
        "grades.view", "grades.create", "grades.update",
        "homework.view", "homework.create", "homework.update", "homework.delete",
        "activities.view",
        "behavior.view", "behavior.create", "behavior.update", "behavior.delete",
        "notifications.view", "notifications.create",
        "reports.view", "reports.generate", "reports.share",
        "settings.view", "settings.update",
        # 008 additions (deputy-only)
        "excused_leaves.view", "excused_leaves.create", "excused_leaves.update", "excused_leaves.delete",
        "substitutes.view", "substitutes.create",
        "session_lifecycle.view", "session_lifecycle.transition",
        "timetable_alerts.view", "timetable_alerts.update",
        "student_attachments.view", "student_attachments.upload", "student_attachments.delete",
        "audit_log.view",
    ],
    "activities_manager": [
        "schools.view", "academics.view", "users.view", "activity_managers.view",
        "students.view", "students.update",
        "activities.view", "activities.create", "activities.update", "activities.delete",
        "behavior.view", "behavior.create", "behavior.update", "behavior.delete",
        "notifications.view", "notifications.create",
        "reports.view", "reports.generate",
        # 008 (read-only)
        "excused_leaves.view", "student_attachments.view", "student_attachments.upload",
        "session_lifecycle.view", "timetable_alerts.view", "audit_log.view",
    ],
    "teacher": [
        # Teachers MUST NOT hold excused_leaves.*.create/.update/.delete
        "schools.view",
        "academics.view",
        "students.view",
        "schedules.view", "schedules.update",  # can update attendance markers in own class
        "attendance.view", "attendance.create", "attendance.update",
        # attendance.delete + early_dismiss intentionally OMITTED
        "grades.view", "grades.create", "grades.update",
        "homework.view", "homework.create", "homework.update", "homework.delete",
        "activities.view",
        "behavior.view", "behavior.create", "behavior.update",
        "notifications.view",
        "reports.view",
        # 008 — teacher can VIEW lifecycle, RESPOND to substitute requests,
        # and mark their OWN session as prepared (transition).
        "excused_leaves.view",
        "substitutes.view", "substitutes.respond",
        "session_lifecycle.view", "session_lifecycle.transition",
        "student_attachments.view",
        "timetable_alerts.view",
    ],
}


ROLE_LABELS: dict[str, dict[str, str]] = {
    "director":           {"ar": "مدير",          "en": "Director"},
    "deputy":             {"ar": "وكيل",          "en": "Deputy Director"},
    "activities_manager": {"ar": "مسؤول الأنشطة", "en": "Activities Manager"},
    "teacher":            {"ar": "معلم",          "en": "Teacher"},
}
