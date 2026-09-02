# alembic/versions/0020_fix_student_enrollments_academic_year_id.py

"""Fix student_enrollments academic_year_id column

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-02 16:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
import logging

logger = logging.getLogger(__name__)

revision = '0020'
down_revision = '0019'
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


def table_exists(table_name):
    """التحقق من وجود جدول"""
    try:
        inspector = inspect(op.get_bind())
        return table_name in inspector.get_table_names()
    except Exception:
        return False


def upgrade():
    """إصلاح جدول student_enrollments"""
    
    if not table_exists('student_enrollments'):
        logger.warning("Table 'student_enrollments' does not exist, skipping")
        return
    
    # 1. التحقق من وجود academic_year_id
    if not column_exists('student_enrollments', 'academic_year_id'):
        logger.info("➕ Adding column 'academic_year_id' to student_enrollments")
        op.add_column(
            'student_enrollments',
            sa.Column('academic_year_id', sa.String(36), nullable=True, comment='معرف السنة الدراسية')
        )
        op.create_index('ix_student_enrollments_academic_year_id', 'student_enrollments', ['academic_year_id'])
        logger.info("✅ Column 'academic_year_id' added")
    else:
        logger.info("⏭️ Column 'academic_year_id' already exists")
    
    # 2. إذا كان هناك year_id، قم بنقل البيانات
    if column_exists('student_enrollments', 'year_id'):
        logger.info("🔄 Copying data from year_id to academic_year_id")
        op.execute("""
            UPDATE student_enrollments 
            SET academic_year_id = year_id 
            WHERE academic_year_id IS NULL AND year_id IS NOT NULL
        """)
        logger.info("✅ Data copied")


def downgrade():
    """التراجع عن التغييرات"""
    
    if not table_exists('student_enrollments'):
        return
    
    if column_exists('student_enrollments', 'academic_year_id'):
        logger.info("🗑️ Dropping column 'academic_year_id'")
        try:
            op.drop_index('ix_student_enrollments_academic_year_id', table_name='student_enrollments')
        except Exception:
            pass
        op.drop_column('student_enrollments', 'academic_year_id')
        logger.info("✅ Column dropped")
