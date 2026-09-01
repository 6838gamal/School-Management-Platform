# app/migrations/versions/0009_add_year_id_to_grades.py

"""Add year_id to grades

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-01 15:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = '0009'
down_revision: str | None = '0008'
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """إضافة عمود year_id إلى جدول grades"""
    
    conn = op.get_bind()
    
    # ✅ إضافة العمود (مع السماح بقيم NULL)
    op.add_column('grades', sa.Column('year_id', sa.String(36), nullable=True))
    
    # ✅ تحديث البيانات - ربط الصفوف بالسنة المناسبة
    try:
        conn.execute(
            text("""
                UPDATE grades g
                SET year_id = (
                    SELECT id FROM academic_years ay 
                    WHERE ay.school_id = g.school_id 
                    ORDER BY ay.created_at ASC 
                    LIMIT 1
                )
                WHERE year_id IS NULL
            """)
        )
    except Exception:
        pass
    
    # ✅ جعل العمود NOT NULL (إذا كانت جميع البيانات محدثة)
    try:
        op.alter_column('grades', 'year_id', nullable=False)
    except Exception:
        pass
    
    # ✅ إضافة فهرس
    op.create_index('ix_grades_year_id', 'grades', ['year_id'])


def downgrade() -> None:
    """حذف عمود year_id من جدول grades"""
    
    op.drop_index('ix_grades_year_id', table_name='grades')
    op.drop_column('grades', 'year_id')
