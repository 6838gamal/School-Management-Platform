"""Add default roles

Revision ID: 003
Revises: 002
Create Date: 2024-01-01 00:00:02.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """إضافة الأدوار الافتراضية"""
    connection = op.get_bind()
    
    # 1. الحصول على المدرسة الأولى (أو إنشاء واحدة)
    school_result = connection.execute(
        text("SELECT id FROM schools LIMIT 1")
    )
    school_row = school_result.fetchone()
    
    if not school_row:
        # إنشاء مدرسة افتراضية إذا لم توجد
        connection.execute(
            text("""
                INSERT INTO schools (id, name, code, onboarding_complete, is_active, created_at)
                VALUES (UUID(), 'المدرسة الرئيسية', 'SCHOOL001', 1, 1, NOW())
            """)
        )
        school_result = connection.execute(
            text("SELECT id FROM schools WHERE code = 'SCHOOL001' LIMIT 1")
        )
        school_row = school_result.fetchone()
    
    school_id = school_row[0]
    
    # 2. الأدوار الافتراضية
    roles = [
        {
            "key": "director",
            "name_ar": "مدير",
            "name_en": "Director",
            "description": "مدير المدرسة - صلاحيات كاملة",
            "is_system": 1
        },
        {
            "key": "deputy",
            "name_ar": "وكيل",
            "name_en": "Deputy",
            "description": "وكيل المدرسة - إدارة أكاديمية",
            "is_system": 1
        },
        {
            "key": "activities",
            "name_ar": "مسؤول أنشطة",
            "name_en": "Activities Officer",
            "description": "مسؤول الأنشطة والفعاليات",
            "is_system": 1
        },
        {
            "key": "teacher",
            "name_ar": "معلم",
            "name_en": "Teacher",
            "description": "معلم - تدريس وإدارة صف",
            "is_system": 1
        }
    ]
    
    for role in roles:
        # التحقق من عدم وجود الدور
        existing = connection.execute(
            text("SELECT id FROM roles WHERE key = :key AND school_id = :school_id"),
            {"key": role["key"], "school_id": school_id}
        ).fetchone()
        
        if not existing:
            connection.execute(
                text("""
                    INSERT INTO roles (id, school_id, key, name_ar, name_en, description, is_system, created_at)
                    VALUES (UUID(), :school_id, :key, :name_ar, :name_en, :description, :is_system, NOW())
                """),
                {
                    "school_id": school_id,
                    "key": role["key"],
                    "name_ar": role["name_ar"],
                    "name_en": role["name_en"],
                    "description": role["description"],
                    "is_system": role["is_system"]
                }
            )
            print(f"✅ تم إنشاء الدور: {role['key']}")
        else:
            print(f"⏭️ الدور موجود بالفعل: {role['key']}")
    
    # 3. ربط الأدوار بالصلاحيات الأساسية
    # جلب معرفات الأدوار
    roles_result = connection.execute(
        text("SELECT id, key FROM roles WHERE school_id = :school_id"),
        {"school_id": school_id}
    )
    roles_dict = {row[1]: row[0] for row in roles_result.fetchall()}
    
    # جلب معرفات الصلاحيات
    perms_result = connection.execute(
        text("SELECT id, key FROM permissions")
    )
    perms_dict = {row[1]: row[0] for row in perms_result.fetchall()}
    
    # تعريف الصلاحيات لكل دور
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
            "reports.view", "reports.generate"
        ],
        "activities": [
            "schools.view",
            "academics.view",
            "users.view",
            "students.view",
            "activities.view", "activities.create", "activities.update", "activities.delete",
            "reports.view"
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
    
    for role_key, perm_keys in role_permissions.items():
        if role_key in roles_dict:
            role_id = roles_dict[role_key]
            for perm_key in perm_keys:
                if perm_key in perms_dict:
                    # التحقق من عدم وجود العلاقة مسبقًا
                    existing = connection.execute(
                        text("""
                            SELECT id FROM role_permissions 
                            WHERE role_id = :role_id AND permission_id = :perm_id
                        """),
                        {"role_id": role_id, "perm_id": perms_dict[perm_key]}
                    ).fetchone()
                    
                    if not existing:
                        connection.execute(
                            text("""
                                INSERT INTO role_permissions (id, role_id, permission_id, created_at)
                                VALUES (UUID(), :role_id, :perm_id, NOW())
                            """),
                            {"role_id": role_id, "perm_id": perms_dict[perm_key]}
                        )
                        print(f"✅ تم ربط الصلاحية {perm_key} بالدور {role_key}")
                else:
                    print(f"⚠️ الصلاحية غير موجودة: {perm_key}")
    
    print("✅ ✅ ✅ تم إضافة الأدوار والصلاحيات بنجاح!")


def downgrade() -> None:
    """حذف الأدوار المضافة"""
    connection = op.get_bind()
    
    # حذف الأدوار (مع الصلاحيات المرتبطة بسبب CASCADE)
    connection.execute(
        text("DELETE FROM roles WHERE key IN ('director', 'deputy', 'activities', 'teacher')")
    )
    print("✅ تم حذف الأدوار")
