# alembic/versions/0017_drop_period_id_from_students.py

"""Drop period_id column from students table

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-02 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
import logging

logger = logging.getLogger(__name__)

revision = '0017'
down_revision = '0016'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    """التحقق من وجود عمود"""
    try:
        inspector = inspect(op.get_bind())
        columns = [c['name'] for c in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception as e:
        logger.warning(f"Error checking column: {e}")
        return False


def upgrade():
    """حذف عمود period_id من جدول students"""
    
    if column_exists('students', 'period_id'):
        logger.info("🗑️ Dropping column 'period_id' from students")
        
        # حذف الفهرس إذا كان موجوداً
        try:
            op.drop_index('ix_students_period_id', table_name='students')
            logger.info("✅ Dropped index ix_students_period_id")
        except Exception as e:
            logger.warning(f"Index ix_students_period_id not found: {e}")
        
        # حذف العمود
        op.drop_column('students', 'period_id')
        logger.info("✅ Column 'period_id' dropped successfully")
    else:
        logger.info("⏭️ Column 'period_id' does not exist, skipping")


def downgrade():
    """إعادة إضافة عمود period_id (في حالة التراجع)"""
    
    if not column_exists('students', 'period_id'):
        logger.info("➕ Adding column 'period_id' back to students")
        op.add_column(
            'students',
            sa.Column('period_id', sa.String(36), nullable=True, comment='معرف الفصل/الحصة')
        )
        op.create_index('ix_students_period_id', 'students', ['period_id'])
        logger.info("✅ Column 'period_id' added back")
