# alembic/versions/0022_add_missing_columns_to_student_enrollments.py

"""Add missing columns to student_enrollments (academic_year_id, class_id, notes)

Revision ID: 0021
Revises: 0020
Create Date: 2026-09-02 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
import logging

logger = logging.getLogger(__name__)

revision = '0022'
down_revision = '0021'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    """التحقق من وجود عمود في الجدول"""
    try:
        inspector = inspect(op.get_bind())
        columns = [c['name'] for c in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception as e:
        logger.warning(f"Error checking column {column_name}: {e}")
        return False


def table_exists(table_name):
    """التحقق من وجود جدول"""
    try:
        inspector = inspect(op.get_bind())
        return table_name in inspector.get_table_names()
    except Exception:
        return False


def index_exists(table_name, index_name):
    """التحقق من وجود فهرس"""
    try:
        inspector = inspect(op.get_bind())
        indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
        return index_name in indexes
    except Exception:
        return False


def upgrade():
    """إضافة الأعمدة المفقودة إلى جدول student_enrollments"""
    
    if not table_exists('student_enrollments'):
        logger.warning("Table 'student_enrollments' does not exist, skipping")
        return
    
    # ============================================================
    # 1. إضافة academic_year_id
    # ============================================================
    if not column_exists('student_enrollments', 'academic_year_id'):
        logger.info("➕ Adding column 'academic_year_id' to student_enrollments")
        op.add_column(
            'student_enrollments',
            sa.Column('academic_year_id', sa.String(36), nullable=True, comment='معرف السنة الدراسية')
        )
        if not index_exists('student_enrollments', 'ix_student_enrollments_academic_year_id'):
            op.create_index('ix_student_enrollments_academic_year_id', 'student_enrollments', ['academic_year_id'])
            logger.info("✅ Index created on academic_year_id")
    else:
        logger.info("⏭️ Column 'academic_year_id' already exists")
    
    # ============================================================
    # 2. إضافة class_id
    # ============================================================
    if not column_exists('student_enrollments', 'class_id'):
        logger.info("➕ Adding column 'class_id' to student_enrollments")
        op.add_column(
            'student_enrollments',
            sa.Column('class_id', sa.String(36), nullable=True, comment='معرف الفصل')
        )
        if not index_exists('student_enrollments', 'ix_student_enrollments_class_id'):
            op.create_index('ix_student_enrollments_class_id', 'student_enrollments', ['class_id'])
            logger.info("✅ Index created on class_id")
    else:
        logger.info("⏭️ Column 'class_id' already exists")
    
    # ============================================================
    # 3. إضافة notes
    # ============================================================
    if not column_exists('student_enrollments', 'notes'):
        logger.info("➕ Adding column 'notes' to student_enrollments")
        op.add_column(
            'student_enrollments',
            sa.Column('notes', sa.String(500), nullable=True, comment='ملاحظات')
        )
    else:
        logger.info("⏭️ Column 'notes' already exists")
    
    # ============================================================
    # 4. نقل البيانات من year_id إلى academic_year_id إذا كان موجوداً
    # ============================================================
    if column_exists('student_enrollments', 'year_id'):
        logger.info("🔄 Copying data from year_id to academic_year_id")
        try:
            op.execute("""
                UPDATE student_enrollments 
                SET academic_year_id = year_id 
                WHERE academic_year_id IS NULL AND year_id IS NOT NULL
            """)
            logger.info("✅ Data copied successfully")
        except Exception as e:
            logger.warning(f"Could not copy data: {e}")
    
    logger.info("✅ Migration 0021 completed successfully")


def downgrade():
    """التراجع عن التغييرات - حذف الأعمدة المضافة"""
    
    if not table_exists('student_enrollments'):
        return
    
    # ============================================================
    # 1. حذف notes
    # ============================================================
    if column_exists('student_enrollments', 'notes'):
        logger.info("🗑️ Dropping column 'notes'")
        op.drop_column('student_enrollments', 'notes')
    
    # ============================================================
    # 2. حذف class_id والفهرس
    # ============================================================
    if column_exists('student_enrollments', 'class_id'):
        logger.info("🗑️ Dropping column 'class_id'")
        try:
            if index_exists('student_enrollments', 'ix_student_enrollments_class_id'):
                op.drop_index('ix_student_enrollments_class_id', table_name='student_enrollments')
        except Exception:
            pass
        op.drop_column('student_enrollments', 'class_id')
    
    # ============================================================
    # 3. حذف academic_year_id والفهرس
    # ============================================================
    if column_exists('student_enrollments', 'academic_year_id'):
        logger.info("🗑️ Dropping column 'academic_year_id'")
        try:
            if index_exists('student_enrollments', 'ix_student_enrollments_academic_year_id'):
                op.drop_index('ix_student_enrollments_academic_year_id', table_name='student_enrollments')
        except Exception:
            pass
        op.drop_column('student_enrollments', 'academic_year_id')
    
    logger.info("✅ Downgrade completed")


# ============================================================
# نسخة بديلة: تشغيل SQL مباشرة
# ============================================================

def upgrade_sql():
    """نسخة بديلة: تشغيل SQL مباشرة"""
    
    # إضافة الأعمدة
    op.execute("""
        ALTER TABLE student_enrollments 
        ADD COLUMN IF NOT EXISTS academic_year_id VARCHAR(36),
        ADD COLUMN IF NOT EXISTS class_id VARCHAR(36),
        ADD COLUMN IF NOT EXISTS notes VARCHAR(500)
    """)
    
    # إنشاء الفهارس
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_student_enrollments_academic_year_id 
        ON student_enrollments (academic_year_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_student_enrollments_class_id 
        ON student_enrollments (class_id)
    """)
    
    # نقل البيانات
    op.execute("""
        UPDATE student_enrollments 
        SET academic_year_id = year_id 
        WHERE academic_year_id IS NULL AND year_id IS NOT NULL
    """)
