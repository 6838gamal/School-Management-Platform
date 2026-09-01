# migrations/versions/0012_add_user_id_to_students.py
"""Add user_id to students table

Revision ID: xxxx
Revises: 0002
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision: str = '0012'
down_revision: str | None = '0011'  # <-- هذا السطر كان مفقوداً
branch_labels: str | None = None
depends_on: str | None = None

def upgrade() -> None:
    # إضافة عمود user_id
    op.add_column('students', sa.Column('user_id', sa.String(36), nullable=True))
    op.create_index('ix_students_user_id', 'students', ['user_id'])
    op.create_foreign_key(
        'fk_students_user_id_users',
        'students', 'users',
        ['user_id'], ['id'],
        ondelete='SET NULL'
    )

def downgrade() -> None:
    op.drop_constraint('fk_students_user_id_users', 'students', type_='foreignkey')
    op.drop_index('ix_students_user_id', table_name='students')
    op.drop_column('students', 'user_id')
