# alembic/versions/0019_add_enrollment_status_column.py

"""Add enrollment_status column to students table

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-02 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
import logging

logger = logging.getLogger(__name__)

revision = '0019'
down_revision = '0018'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    inspector = inspect(op.get_bind())
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade():
    if not column_exists('students', 'enrollment_status'):
        logger.info("➕ Adding column 'enrollment_status' to students")
        op.add_column(
            'students',
            sa.Column('enrollment_status', sa.String(20), nullable=False, server_default='active', comment='حالة التسجيل')
        )
        logger.info("✅ Column 'enrollment_status' added")
    else:
        logger.info("⏭️ Column 'enrollment_status' already exists")


def downgrade():
    if column_exists('students', 'enrollment_status'):
        logger.info("🗑️ Dropping column 'enrollment_status'")
        op.drop_column('students', 'enrollment_status')
        logger.info("✅ Column 'enrollment_status' dropped")
