# alembic/versions/0021_add_class_id_to_student_enrollments.py

"""Add class_id column to student_enrollments

Revision ID: 0020
Revises: 0019
Create Date: 2026-09-02 16:25:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
import logging

logger = logging.getLogger(__name__)

revision = '0021'
down_revision = '0020'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    try:
        inspector = inspect(op.get_bind())
        columns = [c['name'] for c in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


def table_exists(table_name):
    try:
        inspector = inspect(op.get_bind())
        return table_name in inspector.get_table_names()
    except Exception:
        return False


def upgrade():
    if not table_exists('student_enrollments'):
        logger.warning("Table 'student_enrollments' does not exist")
        return
    
    if not column_exists('student_enrollments', 'class_id'):
        logger.info("➕ Adding column 'class_id' to student_enrollments")
        op.add_column(
            'student_enrollments',
            sa.Column('class_id', sa.String(36), nullable=True, comment='معرف الفصل')
        )
        op.create_index('ix_student_enrollments_class_id', 'student_enrollments', ['class_id'])
        logger.info("✅ Column 'class_id' added")
    else:
        logger.info("⏭️ Column 'class_id' already exists")


def downgrade():
    if not table_exists('student_enrollments'):
        return
    
    if column_exists('student_enrollments', 'class_id'):
        logger.info("🗑️ Dropping column 'class_id'")
        try:
            op.drop_index('ix_student_enrollments_class_id', table_name='student_enrollments')
        except Exception:
            pass
        op.drop_column('student_enrollments', 'class_id')
        logger.info("✅ Column dropped")
