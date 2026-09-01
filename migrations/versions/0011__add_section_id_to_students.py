"""add_section_id_to_students

Revision ID: 006
Revises: yyyyyyy
Create Date: 2026-08-29 04:37:35.284564

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # إضافة العمود
    op.add_column('students', sa.Column('section_id', sa.String(36), nullable=True))
    # إضافة المفتاح الخارجي
    op.create_foreign_key(
        'fk_students_section_id_sections',
        'students',
        'sections',
        ['section_id'],
        ['id'],
        ondelete='SET NULL'
    )
    # إضافة فهرس
    op.create_index('ix_students_section_id', 'students', ['section_id'])

def downgrade() -> None:
    # حذف الفهر س
    op.drop_index('ix_students_section_id', table_name='students')
    # حذف المفتاح الخارجي
    op.drop_constraint('fk_students_section_id_sections', 'students', type_='foreignkey')
    # حذف العمود
    op.drop_column('students', 'section_id')
