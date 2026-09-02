# migrations/versions/0014_add_missing_columns_academic_models.py

"""
إضافة الأعمدة المفقودة في النماذج الأكاديمية

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-02 12:30:00.000000

@author: فريق التطوير
@description: إضافة أعمدة is_active و year_id المفقودة في جداول الهيكل الأكاديمي
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision: str = '0014'
down_revision: Union[str, None] = '0013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """التحقق من وجود عمود في جدول معين"""
    try:
        inspector = inspect(op.get_bind())
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception as e:
        print(f"⚠️ خطأ في التحقق من العمود {column_name} في جدول {table_name}: {e}")
        return False


def add_column_if_not_exists(table_name: str, column: sa.Column) -> None:
    """إضافة عمود إذا لم يكن موجوداً"""
    if column_exists(table_name, column.name):
        print(f"ℹ️ العمود '{column.name}' موجود بالفعل في جدول {table_name}")
        return
    
    print(f"📝 جاري إضافة العمود '{column.name}' إلى جدول {table_name}...")
    op.add_column(table_name, column)
    print(f"✅ تم إضافة العمود '{column.name}' بنجاح")


def upgrade() -> None:
    """إضافة جميع الأعمدة المفقودة"""
    
    print("=" * 70)
    print("🚀 بدء ترقية قاعدة البيانات: إضافة الأعمدة المفقودة في النماذج الأكاديمية")
    print("=" * 70)
    
    # ============================================================
    # 1. جدول grades
    # ============================================================
    print("\n📋 تحديث جدول grades...")
    
    # إضافة عمود is_active
    add_column_if_not_exists(
        'grades',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true')
    )
    
    # إضافة عمود year_id (إذا لم يكن موجوداً)
    add_column_if_not_exists(
        'grades',
        sa.Column('year_id', sa.String(36), nullable=True)
    )
    
    # ============================================================
    # 2. جدول academic_years
    # ============================================================
    print("\n📋 تحديث جدول academic_years...")
    
    # إضافة عمود is_active
    add_column_if_not_exists(
        'academic_years',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true')
    )
    
    # ============================================================
    # 3. جدول sections
    # ============================================================
    print("\n📋 تحديث جدول sections...")
    
    # إضافة عمود is_active
    add_column_if_not_exists(
        'sections',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true')
    )
    
    # ============================================================
    # 4. جدول subjects
    # ============================================================
    print("\n📋 تحديث جدول subjects...")
    
    # إضافة عمود is_active
    add_column_if_not_exists(
        'subjects',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true')
    )
    
    # ============================================================
    # 5. جدول rooms
    # ============================================================
    print("\n📋 تحديث جدول rooms...")
    
    # إضافة عمود is_active
    add_column_if_not_exists(
        'rooms',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true')
    )
    
    # ============================================================
    # 6. تحديث البيانات الموجودة
    # ============================================================
    print("\n📝 تحديث البيانات الموجودة...")
    
    try:
        # تحديث grades
        op.execute(
            text("UPDATE grades SET is_active = true WHERE is_active IS NULL")
        )
        
        # تحديث academic_years
        op.execute(
            text("UPDATE academic_years SET is_active = true WHERE is_active IS NULL")
        )
        
        # تحديث sections
        op.execute(
            text("UPDATE sections SET is_active = true WHERE is_active IS NULL")
        )
        
        # تحديث subjects
        op.execute(
            text("UPDATE subjects SET is_active = true WHERE is_active IS NULL")
        )
        
        # تحديث rooms
        op.execute(
            text("UPDATE rooms SET is_active = true WHERE is_active IS NULL")
        )
        
        print("✅ تم تحديث البيانات الموجودة")
    except Exception as e:
        print(f"⚠️ تحذير: فشل تحديث بعض البيانات: {e}")
    
    # ============================================================
    # 7. إضافة الفهارس (اختياري)
    # ============================================================
    print("\n📝 إضافة الفهارس...")
    
    try:
        op.create_index('ix_grades_is_active', 'grades', ['is_active'])
        op.create_index('ix_academic_years_is_active', 'academic_years', ['is_active'])
        op.create_index('ix_sections_is_active', 'sections', ['is_active'])
        op.create_index('ix_subjects_is_active', 'subjects', ['is_active'])
        op.create_index('ix_rooms_is_active', 'rooms', ['is_active'])
        print("✅ تم إضافة الفهارس بنجاح")
    except Exception as e:
        print(f"⚠️ تحذير: فشل إضافة بعض الفهارس: {e}")
    
    print("\n" + "=" * 70)
    print("✅ تمت ترقية قاعدة البيانات بنجاح")
    print("=" * 70)


def downgrade() -> None:
    """حذف الأعمدة المضافة (الرجوع إلى الإصدار السابق)"""
    
    print("=" * 70)
    print("🚀 بدء الرجوع إلى الإصدار السابق: حذف الأعمدة المضافة")
    print("=" * 70)
    
    # ============================================================
    # حذف الفهارس
    # ============================================================
    print("\n📝 حذف الفهارس...")
    
    try:
        op.drop_index('ix_grades_is_active', table_name='grades')
        op.drop_index('ix_academic_years_is_active', table_name='academic_years')
        op.drop_index('ix_sections_is_active', table_name='sections')
        op.drop_index('ix_subjects_is_active', table_name='subjects')
        op.drop_index('ix_rooms_is_active', table_name='rooms')
        print("✅ تم حذف الفهارس بنجاح")
    except Exception as e:
        print(f"⚠️ تحذير: فشل حذف بعض الفهارس: {e}")
    
    # ============================================================
    # حذف الأعمدة
    # ============================================================
    
    # جدول grades
    if column_exists('grades', 'is_active'):
        print("📝 حذف عمود is_active من جدول grades...")
        op.drop_column('grades', 'is_active')
    
    if column_exists('grades', 'year_id'):
        print("📝 حذف عمود year_id من جدول grades...")
        op.drop_column('grades', 'year_id')
    
    # جدول academic_years
    if column_exists('academic_years', 'is_active'):
        print("📝 حذف عمود is_active من جدول academic_years...")
        op.drop_column('academic_years', 'is_active')
    
    # جدول sections
    if column_exists('sections', 'is_active'):
        print("📝 حذف عمود is_active من جدول sections...")
        op.drop_column('sections', 'is_active')
    
    # جدول subjects
    if column_exists('subjects', 'is_active'):
        print("📝 حذف عمود is_active من جدول subjects...")
        op.drop_column('subjects', 'is_active')
    
    # جدول rooms
    if column_exists('rooms', 'is_active'):
        print("📝 حذف عمود is_active من جدول rooms...")
        op.drop_column('rooms', 'is_active')
    
    print("\n" + "=" * 70)
    print("✅ تم الرجوع إلى الإصدار السابق بنجاح")
    print("=" * 70)
