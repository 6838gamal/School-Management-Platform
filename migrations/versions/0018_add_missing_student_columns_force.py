# alembic/versions/0018_add_missing_student_columns_force.py

"""Add missing student columns forcefully

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-02 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '0018'
down_revision = '0017'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    inspector = inspect(op.get_bind())
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade():
    # الأعمدة المطلوبة
    columns = [
        ('first_name_ar', sa.String(100)),
        ('last_name_ar', sa.String(100)),
        ('nationality', sa.String(50)),
        ('guardian_relation', sa.String(50)),
        ('phone', sa.String(50)),
        ('photo_url', sa.String(500)),
        ('year_id', sa.String(36)),
        ('grade_id', sa.String(36)),
    ]
    
    for col_name, col_type in columns:
        if not column_exists('students', col_name):
            op.add_column('students', sa.Column(col_name, col_type, nullable=True))
            print(f"✅ Added column: {col_name}")


def downgrade():
    columns = ['photo_url', 'phone', 'guardian_relation', 'nationality', 'last_name_ar', 'first_name_ar', 'grade_id', 'year_id']
    for col in columns:
        if column_exists('students', col):
            op.drop_column('students', col)
            print(f"🗑️ Dropped column: {col}")
