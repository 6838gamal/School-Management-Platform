"""add_deputy_and_activity_managers_permissions

Revision ID: 005
Revises: yyyy
Create Date: 2026-08-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '0006'  # هذا الرقم سيتغير
down_revision = '0005' # هذا الرقم سيتغير
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    إضافة صلاحيات الوكلاء ومديري الأنشطة
    """
    connection = op.get_bind()
    
    # 1. إضافة الصلاحيات الجديدة
    permissions = [
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
    
    # أدخل الصلاحيات الجديدة
    for perm in permissions:
        connection.execute(
            text("""
                INSERT INTO permissions (key, label_ar, label_en, "group")
                VALUES (:key, :label_ar, :label_en, :group)
                ON CONFLICT (key) DO NOTHING
            """),
            perm
        )
    
    # 2. أضف صلاحيات view للمدير
    connection.execute(
        text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT 
                r.id,
                p.id
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name = 'director'
            AND p.key IN ('deputy.view', 'activity_managers.view')
            ON CONFLICT DO NOTHING
        """)
    )
    
    # 3. أضف صلاحية view للوكيل
    connection.execute(
        text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT 
                r.id,
                p.id
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name = 'deputy'
            AND p.key = 'deputy.view'
            ON CONFLICT DO NOTHING
        """)
    )
    
    # 4. أضف صلاحية view لمدير الأنشطة
    connection.execute(
        text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT 
                r.id,
                p.id
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name = 'activities_manager'
            AND p.key = 'activity_managers.view'
            ON CONFLICT DO NOTHING
        """)
    )
    
    print("✅ تم إضافة صلاحيات الوكلاء ومديري الأنشطة بنجاح")


def downgrade() -> None:
    """
    حذف صلاحيات الوكلاء ومديري الأنشطة في حالة الرجوع
    """
    connection = op.get_bind()
    
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
    
    # ثم حذف الصلاحيات
    connection.execute(
        text("""
            DELETE FROM permissions
            WHERE key LIKE 'deputy.%' 
            OR key LIKE 'activity_managers.%'
        """)
    )
    
    print("✅ تم حذف صلاحيات الوكلاء ومديري الأنشطة بنجاح")
