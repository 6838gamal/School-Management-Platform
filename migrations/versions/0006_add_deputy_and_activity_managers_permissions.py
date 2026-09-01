"""add_deputy_and_activity_managers_permissions

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: str | None = '0005'
branch_labels: str | None = None
depends_on: str | None = None


def table_exists(table_name: str) -> bool:
    """التحقق من وجود جدول في قاعدة البيانات."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    return table_name in inspector.get_table_names()


def permission_exists(connection, key: str) -> bool:
    """التحقق من وجود صلاحية معينة في قاعدة البيانات."""
    result = connection.execute(
        text("SELECT id FROM permissions WHERE key = :key"),
        {"key": key}
    )
    return result.fetchone() is not None


def role_exists(connection, key: str, school_id: str) -> bool:
    """التحقق من وجود دور معين في قاعدة البيانات."""
    result = connection.execute(
        text("SELECT id FROM roles WHERE key = :key AND school_id = :school_id"),
        {"key": key, "school_id": school_id}
    )
    return result.fetchone() is not None


def add_permission_if_not_exists(connection, key: str, label_ar: str, label_en: str, group: str) -> bool:
    """إضافة صلاحية إذا لم تكن موجودة."""
    if permission_exists(connection, key):
        print(f"⏭️ الصلاحية موجودة بالفعل: {key}")
        return False
    
    connection.execute(
        text("""
            INSERT INTO permissions (id, key, label_ar, label_en, "group", created_at, updated_at)
            VALUES (gen_random_uuid(), :key, :label_ar, :label_en, :group, NOW(), NOW())
        """),
        {
            "key": key,
            "label_ar": label_ar,
            "label_en": label_en,
            "group": group
        }
    )
    print(f"✅ تم إضافة الصلاحية: {key}")
    return True


def add_role_permission_if_not_exists(connection, role_id: str, permission_id: str) -> bool:
    """إضافة ربط بين دور وصلاحية إذا لم يكن موجوداً."""
    result = connection.execute(
        text("""
            SELECT id FROM role_permissions 
            WHERE role_id = :role_id AND permission_id = :permission_id
        """),
        {"role_id": role_id, "permission_id": permission_id}
    )
    if result.fetchone():
        return False
    
    connection.execute(
        text("""
            INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
            VALUES (gen_random_uuid(), :role_id, :permission_id, NOW(), NOW())
        """),
        {"role_id": role_id, "permission_id": permission_id}
    )
    return True


def upgrade() -> None:
    """
    إضافة صلاحيات الوكلاء ومديري الأنشطة
    """
    connection = op.get_bind()
    
    # التحقق من وجود الجداول
    if not table_exists('permissions'):
        print("⚠️ جدول permissions غير موجود، تخطي")
        return
    
    if not table_exists('roles'):
        print("⚠️ جدول roles غير موجود، تخطي")
        return
    
    # 1. إضافة الصلاحيات الجديدة
    new_permissions = [
        # Deputy permissions
        {
            'key': 'deputy.view',
            'label_ar': 'عرض الوكلاء',
            'label_en': 'View deputies',
            'group': 'deputy'
        },
        {
            'key': 'deputy.create',
            'label_ar': 'إنشاء وكيل',
            'label_en': 'Create deputy',
            'group': 'deputy'
        },
        {
            'key': 'deputy.update',
            'label_ar': 'تعديل وكيل',
            'label_en': 'Update deputy',
            'group': 'deputy'
        },
        {
            'key': 'deputy.delete',
            'label_ar': 'حذف وكيل',
            'label_en': 'Delete deputy',
            'group': 'deputy'
        },
        # Activity Managers permissions
        {
            'key': 'activity_managers.view',
            'label_ar': 'عرض مديري الأنشطة',
            'label_en': 'View activity managers',
            'group': 'activity_managers'
        },
        {
            'key': 'activity_managers.create',
            'label_ar': 'إنشاء مدير نشاط',
            'label_en': 'Create activity manager',
            'group': 'activity_managers'
        },
        {
            'key': 'activity_managers.update',
            'label_ar': 'تعديل مدير نشاط',
            'label_en': 'Update activity manager',
            'group': 'activity_managers'
        },
        {
            'key': 'activity_managers.delete',
            'label_ar': 'حذف مدير نشاط',
            'label_en': 'Delete activity manager',
            'group': 'activity_managers'
        }
    ]
    
    added_count = 0
    for perm in new_permissions:
        if add_permission_if_not_exists(
            connection,
            perm['key'],
            perm['label_ar'],
            perm['label_en'],
            perm['group']
        ):
            added_count += 1
    
    print(f"✅ تم إضافة {added_count} صلاحية جديدة")
    
    # 2. الحصول على المدرسة الأولى
    school_result = connection.execute(
        text("SELECT id FROM schools LIMIT 1")
    )
    school_row = school_result.fetchone()
    
    if not school_row:
        print("⚠️ لا توجد مدارس في النظام، تخطي ربط الصلاحيات")
        return
    
    school_id = school_row[0]
    
    # 3. ربط الصلاحيات الجديدة بالأدوار
    # جلب معرفات الصلاحيات الجديدة
    perm_ids = {}
    for perm in new_permissions:
        result = connection.execute(
            text("SELECT id FROM permissions WHERE key = :key"),
            {"key": perm['key']}
        )
        row = result.fetchone()
        if row:
            perm_ids[perm['key']] = row[0]
    
    # جلب معرفات الأدوار
    roles_result = connection.execute(
        text("SELECT id, key FROM roles WHERE school_id = :school_id"),
        {"school_id": school_id}
    )
    roles_dict = {row[1]: row[0] for row in roles_result.fetchall()}
    
    # 4. تعريف الصلاحيات لكل دور باستخدام المفتاح الصحيح (key)
    role_permissions = {
        "director": [
            "deputy.view", "deputy.create", "deputy.update", "deputy.delete",
            "activity_managers.view", "activity_managers.create", "activity_managers.update", "activity_managers.delete"
        ],
        "deputy": [
            "deputy.view",
            "activity_managers.view"
        ],
        "activities_manager": [
            "activity_managers.view", "activity_managers.create", "activity_managers.update"
        ],
        "teacher": [
            "deputy.view",
            "activity_managers.view"
        ]
    }
    
    linked_count = 0
    for role_key, perm_keys in role_permissions.items():
        if role_key in roles_dict:
            role_id = roles_dict[role_key]
            for perm_key in perm_keys:
                if perm_key in perm_ids:
                    if add_role_permission_if_not_exists(connection, role_id, perm_ids[perm_key]):
                        linked_count += 1
                        print(f"✅ تم ربط الصلاحية {perm_key} بالدور {role_key}")
                else:
                    print(f"⚠️ الصلاحية غير موجودة: {perm_key}")
        else:
            print(f"⚠️ الدور غير موجود: {role_key}")
    
    print(f"✅ تم ربط {linked_count} صلاحية بالأدوار")
    print("✅ تم إضافة صلاحيات الوكلاء ومديري الأنشطة بنجاح")


def downgrade() -> None:
    """
    حذف صلاحيات الوكلاء ومديري الأنشطة في حالة الرجوع
    """
    connection = op.get_bind()
    
    if not table_exists('permissions'):
        print("⚠️ جدول permissions غير موجود، تخطي")
        return
    
    # حذف الصلاحيات من role_permissions أولاً
    connection.execute(
        text("""
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions 
                WHERE key LIKE 'deputy.%' 
                OR key LIKE 'activity_managers.%'
            )
        """)
    )
    print("🗑️ تم حذف الصلاحيات من role_permissions")
    
    # ثم حذف الصلاحيات
    connection.execute(
        text("""
            DELETE FROM permissions
            WHERE key LIKE 'deputy.%' 
            OR key LIKE 'activity_managers.%'
        """)
    )
    print("🗑️ تم حذف الصلاحيات من permissions")
    
    print("✅ تم حذف صلاحيات الوكلاء ومديري الأنشطة بنجاح")
