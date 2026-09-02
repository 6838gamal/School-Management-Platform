# alembic/versions/0024_add_session_lifecycle_permissions.py

"""Add session_lifecycle permissions

Revision ID: XXXX
Revises: previous_revision_id
Create Date: 2026-09-02 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
import logging

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision = '0024'
down_revision = '0023'  # ضع الـ revision السابق هنا
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """التحقق من وجود جدول"""
    try:
        inspector = inspect(op.get_bind())
        return table_name in inspector.get_table_names()
    except Exception:
        return False


def column_exists(table_name: str, column_name: str) -> bool:
    """التحقق من وجود عمود"""
    try:
        inspector = inspect(op.get_bind())
        columns = [c['name'] for c in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


def upgrade():
    """إضافة صلاحيات session_lifecycle إلى قاعدة البيانات"""
    
    # التحقق من وجود الجدول
    if not table_exists('permissions'):
        logger.warning("Table 'permissions' does not exist, skipping")
        return
    
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    # ============================================================
    # 1. إضافة صلاحيات session_lifecycle
    # ============================================================
    
    permissions = [
        ("session_lifecycle.view", "عرض حالة الحصص", "View session lifecycle", "session_lifecycle"),
        ("session_lifecycle.transition", "تغيير حالة الحصة", "Transition session", "session_lifecycle"),
    ]
    
    for key, label_ar, label_en, group in permissions:
        # التحقق من عدم وجود الصلاحية مسبقاً
        check_sql = f"SELECT id FROM permissions WHERE key = '{key}'"
        result = conn.execute(text(check_sql))
        existing = result.fetchone()
        
        if not existing:
            # إضافة الصلاحية
            insert_sql = """
                INSERT INTO permissions (id, key, label_ar, label_en, group, created_at, updated_at)
                VALUES (gen_random_uuid(), :key, :label_ar, :label_en, :group, NOW(), NOW())
            """
            conn.execute(
                text(insert_sql),
                {"key": key, "label_ar": label_ar, "label_en": label_en, "group": group}
            )
            logger.info(f"✅ Added permission: {key}")
        else:
            logger.info(f"⏭️ Permission already exists: {key}")
    
    # ============================================================
    # 2. إضافة الصلاحيات لدور deputy
    # ============================================================
    
    if table_exists('roles') and table_exists('role_permissions'):
        # جلب دور deputy
        role_result = conn.execute(text("SELECT id FROM roles WHERE key = 'deputy'"))
        role = role_result.fetchone()
        
        if role:
            role_id = role[0]
            
            # جلب معرفات الصلاحيات المضافة
            for key, _, _, _ in permissions:
                perm_result = conn.execute(text(f"SELECT id FROM permissions WHERE key = '{key}'"))
                perm = perm_result.fetchone()
                
                if perm:
                    perm_id = perm[0]
                    
                    # التحقق من عدم وجود العلاقة مسبقاً
                    check_sql = f"""
                        SELECT id FROM role_permissions 
                        WHERE role_id = '{role_id}' AND permission_id = '{perm_id}'
                    """
                    existing = conn.execute(text(check_sql)).fetchone()
                    
                    if not existing:
                        # إضافة العلاقة
                        insert_sql = """
                            INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
                            VALUES (gen_random_uuid(), :role_id, :perm_id, NOW(), NOW())
                        """
                        conn.execute(
                            text(insert_sql),
                            {"role_id": role_id, "perm_id": perm_id}
                        )
                        logger.info(f"✅ Added permission {key} to role deputy")
                    else:
                        logger.info(f"⏭️ Permission {key} already assigned to deputy")
        else:
            logger.warning("Role 'deputy' not found")
    
    # ============================================================
    # 3. (اختياري) إضافة الصلاحيات لدور teacher (للقراءة فقط)
    # ============================================================
    
    if table_exists('roles') and table_exists('role_permissions'):
        # جلب دور teacher
        role_result = conn.execute(text("SELECT id FROM roles WHERE key = 'teacher'"))
        role = role_result.fetchone()
        
        if role:
            role_id = role[0]
            
            # إضافة صلاحية view فقط للمعلم
            key = "session_lifecycle.view"
            perm_result = conn.execute(text(f"SELECT id FROM permissions WHERE key = '{key}'"))
            perm = perm_result.fetchone()
            
            if perm:
                perm_id = perm[0]
                check_sql = f"""
                    SELECT id FROM role_permissions 
                    WHERE role_id = '{role_id}' AND permission_id = '{perm_id}'
                """
                existing = conn.execute(text(check_sql)).fetchone()
                
                if not existing:
                    insert_sql = """
                        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
                        VALUES (gen_random_uuid(), :role_id, :perm_id, NOW(), NOW())
                    """
                    conn.execute(
                        text(insert_sql),
                        {"role_id": role_id, "perm_id": perm_id}
                    )
                    logger.info(f"✅ Added permission {key} to role teacher")
    
    logger.info("✅ Migration completed successfully")


def downgrade():
    """حذف صلاحيات session_lifecycle (التراجع)"""
    
    if not table_exists('permissions'):
        return
    
    conn = op.get_bind()
    
    # حذف الصلاحيات
    keys = ["session_lifecycle.view", "session_lifecycle.transition"]
    
    for key in keys:
        # حذف العلاقات أولاً
        delete_rp = f"""
            DELETE FROM role_permissions 
            WHERE permission_id IN (SELECT id FROM permissions WHERE key = '{key}')
        """
        conn.execute(text(delete_rp))
        
        # حذف الصلاحية
        delete_perm = f"DELETE FROM permissions WHERE key = '{key}'"
        conn.execute(text(delete_perm))
        
        logger.info(f"🗑️ Removed permission: {key}")
    
    logger.info("✅ Downgrade completed")
