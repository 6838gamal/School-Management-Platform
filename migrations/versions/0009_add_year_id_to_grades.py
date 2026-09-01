# app/migrations/versions/xxxx_add_year_id_to_grades.py

"""Add year_id to grades

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-01 15:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0009'
down_revision: str | None = '0008'  # تأكد من أن هذا المعرف صحيح
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # 1. إضافة عمود year_id مع السماح بقيم NULL مؤقتاً
    # ملاحظة: لا يوجد Foreign Key، فقط عمود عادي
    op.add_column('grades', sa.Column('year_id', sa.String(36), nullable=True))
    
    # 2. تحديث البيانات الموجودة - ربط الصفوف بالسنة المناسبة
    conn = op.get_bind()
    
    # التحقق من وجود بيانات في academic_years
    result = conn.execute(
        sa.text("SELECT COUNT(*) FROM academic_years")
    ).scalar()
    
    if result and result > 0:
        # تحديث الصفوف التي ليس لها year_id
        conn.execute(
            sa.text("""
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
    else:
        # إذا لم توجد سنوات، قم بإنشاء سنة افتراضية لكل مدرسة
        conn.execute(
            sa.text("""
                INSERT INTO academic_years (id, school_id, name, start_date, end_date, is_current, is_active)
                SELECT 
                    gen_random_uuid()::text, 
                    id, 
                    'السنة الدراسية الافتراضية', 
                    '2024-09-01', 
                    '2025-06-30', 
                    true, 
                    true
                FROM schools
                WHERE NOT EXISTS (
                    SELECT 1 FROM academic_years WHERE academic_years.school_id = schools.id
                )
            """)
        )
        
        # إعادة محاولة التحديث
        conn.execute(
            sa.text("""
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
    
    # 3. جعل العمود NOT NULL بعد تعبئة البيانات
    op.alter_column('grades', 'year_id', nullable=False)
    
    # 4. ❌ تم إزالة المفتاح الأجنبي
    # op.create_foreign_key(...)
    
    # 5. تحديث الـ UniqueConstraint
    try:
        op.drop_constraint('uq_grade_stage_name', 'grades', type_='unique')
    except Exception:
        # القيد قد لا يكون موجوداً بنفس الاسم
        pass
    
    op.create_unique_constraint(
        'uq_grade_stage_year_name',
        'grades',
        ['stage_id', 'year_id', 'name']
    )
    
    # 6. إضافة فهرس (اختياري لكن مفيد للأداء)
    op.create_index('ix_grades_year_id', 'grades', ['year_id'])


def downgrade() -> None:
    # 1. حذف الفهرس
    op.drop_index('ix_grades_year_id', table_name='grades')
    
    # 2. حذف الـ UniqueConstraint الجديد
    op.drop_constraint('uq_grade_stage_year_name', 'grades', type_='unique')
    
    # 3. إعادة الـ UniqueConstraint القديم (إذا كان موجوداً سابقاً)
    op.create_unique_constraint('uq_grade_stage_name', 'grades', ['stage_id', 'name'])
    
    # 4. حذف العمود year_id
    op.drop_column('grades', 'year_id')
