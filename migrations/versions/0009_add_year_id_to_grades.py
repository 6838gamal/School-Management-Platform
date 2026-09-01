# app/migrations/versions/xxxx_add_year_id_to_grades.py

"""Add year_id to grades

Revision ID: xxxx
Revises: yyyy
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. إضافة عمود year_id مع السماح بقيم NULL مؤقتاً
    op.add_column('grades', sa.Column('year_id', sa.String(36), nullable=True))
    
    # 2. إضافة عمود is_active
    op.add_column('grades', sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False))
    
    # 3. تحديث البيانات الموجودة - ربط الصفوف بالسنة المناسبة
    # (هذا يعتمد على منطق عملك - مثال: ربط بأول سنة دراسية للمدرسة)
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            UPDATE grades g
            SET year_id = (
                SELECT id FROM academic_years ay 
                WHERE ay.school_id = g.school_id 
                ORDER BY ay.created_at LIMIT 1
            )
            WHERE year_id IS NULL
        """)
    )
    
    # 4. جعل العمود NOT NULL بعد تعبئة البيانات
    op.alter_column('grades', 'year_id', nullable=False)
    
    # 5. إضافة المفاتيح الأجنبية
    op.create_foreign_key(
        'fk_grades_year_id_academic_years',
        'grades', 'academic_years',
        ['year_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # 6. تحديث الـ UniqueConstraint
    op.drop_constraint('uq_grade_stage_name', 'grades', type_='unique')
    op.create_unique_constraint(
        'uq_grade_stage_year_name',
        'grades',
        ['stage_id', 'year_id', 'name']
    )
    
    # 7. إضافة فهرس
    op.create_index('ix_grades_year_id', 'grades', ['year_id'])


def downgrade() -> None:
    # 1. حذف الفهرس
    op.drop_index('ix_grades_year_id', table_name='grades')
    
    # 2. حذف الـ UniqueConstraint الجديد
    op.drop_constraint('uq_grade_stage_year_name', 'grades', type_='unique')
    op.create_unique_constraint('uq_grade_stage_name', 'grades', ['stage_id', 'name'])
    
    # 3. حذف المفتاح الأجنبي
    op.drop_constraint('fk_grades_year_id_academic_years', 'grades', type_='foreignkey')
    
    # 4. حذف العمود is_active
    op.drop_column('grades', 'is_active')
    
    # 5. حذف العمود year_id
    op.drop_column('grades', 'year_id')
