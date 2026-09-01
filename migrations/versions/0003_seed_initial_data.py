"""Seed initial data (roles and permissions)

Revision ID: 0003
Revises: 0002
Create Date: 2024-01-01 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """إضافة البيانات الأولية (الأدوار والصلاحيات)"""
    
    # الحصول على اتصال
    connection = op.get_bind()
    
    # ============================================================
    # 1. إضافة الصلاحيات
    # ============================================================
    permissions = [
        # Schools
        ('schools.view', 'عرض المدرسة', 'View school', 'schools'),
        ('schools.update', 'تعديل بيانات المدرسة', 'Update school', 'schools'),
        # Academic structure
        ('academics.view', 'عرض الهيكل الأكاديمي', 'View academic structure', 'academics'),
        ('academics.create', 'إنشاء عناصر أكاديمية', 'Create academic items', 'academics'),
        ('academics.update', 'تعديل عناصر أكاديمية', 'Update academic items', 'academics'),
        ('academics.delete', 'حذف عناصر أكاديمية', 'Delete academic items', 'academics'),
        # Users
        ('users.view', 'عرض المستخدمين', 'View users', 'users'),
        ('users.create', 'إنشاء مستخدم', 'Create user', 'users'),
        ('users.update', 'تعديل مستخدم', 'Update user', 'users'),
        ('users.delete', 'حذف مستخدم', 'Delete user', 'users'),
        ('users.assign_role', 'تعيين دور لمستخدم', 'Assign role to user', 'users'),
        # Students
        ('students.view', 'عرض الطلاب', 'View students', 'students'),
        ('students.create', 'إضافة طالب', 'Create student', 'students'),
        ('students.update', 'تعديل طالب', 'Update student', 'students'),
        ('students.delete', 'حذف طالب', 'Delete student', 'students'),
        # Teachers
        ('teachers.view', 'عرض المعلمين', 'View teachers', 'teachers'),
        ('teachers.create', 'إضافة معلم', 'Create teacher', 'teachers'),
        ('teachers.update', 'تعديل معلم', 'Update teacher', 'teachers'),
        ('teachers.assign', 'تكليف معلم', 'Assign teacher', 'teachers'),
        # Activities
        ('activities.view', 'عرض الأنشطة', 'View activities', 'activities'),
        ('activities.create', 'إنشاء نشاط', 'Create activity', 'activities'),
        ('activities.update', 'تعديل نشاط', 'Update activity', 'activities'),
        ('activities.delete', 'حذف نشاط', 'Delete activity', 'activities'),
        # Reports
        ('reports.view', 'عرض التقارير', 'View reports', 'reports'),
        ('reports.generate', 'إنشاء تقرير', 'Generate report', 'reports'),
        # Settings
        ('settings.view', 'عرض الإعدادات', 'View settings', 'settings'),
        ('settings.update', 'تعديل الإعدادات', 'Update settings', 'settings'),
    ]
    
    for key, label_ar, label_en, group in permissions:
        # ✅ استخدام gen_random_uuid() بدلاً من UUID()
        # ✅ استخدام "group" بين علامتي اقتباس (كلمة محجوزة)
        # ✅ استخدام ON CONFLICT (خاص بـ PostgreSQL)
        connection.execute(
            text("""
                INSERT INTO permissions (id, key, label_ar, label_en, "group", created_at)
                VALUES (
                    gen_random_uuid(),
                    :key,
                    :label_ar,
                    :label_en,
                    :group,
                    NOW()
                )
                ON CONFLICT (key) DO UPDATE SET 
                    label_ar = EXCLUDED.label_ar,
                    label_en = EXCLUDED.label_en,
                    "group" = EXCLUDED."group"
            """),
            {
                "key": key,
                "label_ar": label_ar,
                "label_en": label_en,
                "group": group
            }
        )
    
    print(f"✅ تم إضافة {len(permissions)} صلاحية")
    
    # ============================================================
    # 2. إضافة الأدوار الأساسية
    # ============================================================
    roles = [
        {"key": "director", "name_ar": "مدير", "name_en": "Director", "description": "مدير المدرسة", "is_system": True},
        {"key": "deputy", "name_ar": "وكيل", "name_en": "Deputy", "description": "وكيل المدرسة", "is_system": True},
        {"key": "activities_manager", "name_ar": "مسؤول الأنشطة", "name_en": "Activities Manager", "description": "مسؤول الأنشطة المدرسية", "is_system": True},
        {"key": "teacher", "name_ar": "معلم", "name_en": "Teacher", "description": "معلم", "is_system": True},
    ]
    
    for role in roles:
        connection.execute(
            text("""
                INSERT INTO roles (id, key, name_ar, name_en, description, is_system, school_id, created_at)
                VALUES (
                    gen_random_uuid(),
                    :key,
                    :name_ar,
                    :name_en,
                    :description,
                    :is_system,
                    NULL,
                    NOW()
                )
                ON CONFLICT (key, school_id) WHERE school_id IS NULL DO UPDATE SET
                    name_ar = EXCLUDED.name_ar,
                    name_en = EXCLUDED.name_en,
                    description = EXCLUDED.description,
                    is_system = EXCLUDED.is_system
            """),
            role
        )
    
    print(f"✅ تم إضافة {len(roles)} دور")
    
    # ============================================================
    # 3. تعريف صلاحيات كل دور
    # ============================================================
    role_permissions = {
        "director": [
            "schools.view", "schools.update",
            "academics.view", "academics.create", "academics.update", "academics.delete",
            "users.view", "users.create", "users.update", "users.delete", "users.assign_role",
            "students.view", "students.create", "students.update", "students.delete",
            "teachers.view", "teachers.create", "teachers.update", "teachers.assign",
            "activities.view", "activities.create", "activities.update", "activities.delete",
            "reports.view", "reports.generate",
            "settings.view", "settings.update"
        ],
        "deputy": [
            "schools.view",
            "academics.view", "academics.create", "academics.update",
            "users.view", "users.create", "users.update",
            "students.view", "students.create", "students.update",
            "teachers.view", "teachers.create", "teachers.update",
            "activities.view", "activities.create", "activities.update",
            "reports.view",
            "settings.view"
        ],
        "activities_manager": [
            "schools.view",
            "academics.view",
            "students.view",
            "teachers.view",
            "activities.view", "activities.create", "activities.update", "activities.delete",
            "reports.view",
            "settings.view"
        ],
        "teacher": [
            "schools.view",
            "academics.view",
            "students.view",
            "teachers.view",
            "activities.view",
            "reports.view"
        ]
    }
    
    # ============================================================
    # 4. ربط الصلاحيات بالأدوار
    # ============================================================
    for role_key, perm_keys in role_permissions.items():
        # الحصول على معرف الدور
        result = connection.execute(
            text("SELECT id FROM roles WHERE key = :key AND school_id IS NULL"),
            {"key": role_key}
        )
        role_row = result.fetchone()
        if not role_row:
            print(f"⚠️ الدور {role_key} غير موجود، تخطي")
            continue
        
        role_id = role_row[0]
        added_count = 0
        
        # الحصول على معرفات الصلاحيات وإضافتها
        for perm_key in perm_keys:
            result = connection.execute(
                text("SELECT id FROM permissions WHERE key = :key"),
                {"key": perm_key}
            )
            perm_row = result.fetchone()
            if not perm_row:
                print(f"⚠️ الصلاحية {perm_key} غير موجودة، تخطي")
                continue
            
            perm_id = perm_row[0]
            
            # إضافة العلاقة إذا لم تكن موجودة
            result = connection.execute(
                text("""
                    INSERT INTO role_permissions (id, role_id, permission_id, created_at)
                    VALUES (gen_random_uuid(), :role_id, :perm_id, NOW())
                    ON CONFLICT (role_id, permission_id) DO NOTHING
                """),
                {"role_id": role_id, "perm_id": perm_id}
            )
            
            if result.rowcount > 0:
                added_count += 1
        
        print(f"✅ تم ربط {added_count} صلاحية بالدور: {role_key}")


def downgrade() -> None:
    """حذف البيانات الأولية"""
    connection = op.get_bind()
    
    # حذف ربط الصلاحيات بالأدوار
    connection.execute(text("DELETE FROM role_permissions"))
    print("🗑️ تم حذف ربط الصلاحيات بالأدوار")
    
    # حذف الأدوار (بدون مدرسة)
    connection.execute(text("DELETE FROM roles WHERE school_id IS NULL"))
    print("🗑️ تم حذف الأدوار الأساسية")
    
    # حذف الصلاحيات
    connection.execute(text("DELETE FROM permissions"))
    print("🗑️ تم حذف الصلاحيات")
    
    print("✅ تم حذف جميع البيانات الأولية")
