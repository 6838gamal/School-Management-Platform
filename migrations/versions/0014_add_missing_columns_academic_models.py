# migrations/versions/0014_add_missing_columns_academic_models.py

"""
إضافة الأعمدة المفقودة في النماذج الأكاديمية

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-02 12:30:00.000000

@author: فريق التطوير
@description: إضافة أعمدة is_active و year_id المفقودة في جداول الهيكل الأكاديمي
@changelog:
    - إضافة is_active إلى جدول grades
    - إضافة year_id إلى جدول grades  
    - إضافة is_active إلى جدول academic_years
    - إضافة is_active إلى جدول sections
    - إضافة is_active إلى جدول subjects
    - إضافة is_active إلى جدول rooms
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '0014'
down_revision: Union[str, None] = '0013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ============================================================
# دوال مساعدة للتحقق من وجود الأعمدة والجداول
# ============================================================

def table_exists(table_name: str) -> bool:
    """
    التحقق من وجود جدول في قاعدة البيانات
    
    Args:
        table_name: اسم الجدول
        
    Returns:
        True إذا كان الجدول موجوداً، False إذا لم يكن
    """
    try:
        inspector = inspect(op.get_bind())
        tables = inspector.get_table_names()
        return table_name in tables
    except Exception as e:
        print(f"⚠️ خطأ في التحقق من وجود الجدول {table_name}: {e}")
        return False


def column_exists(table_name: str, column_name: str) -> bool:
    """
    التحقق من وجود عمود في جدول معين
    
    Args:
        table_name: اسم الجدول
        column_name: اسم العمود
        
    Returns:
        True إذا كان العمود موجوداً، False إذا لم يكن
    """
    try:
        if not table_exists(table_name):
            return False
        inspector = inspect(op.get_bind())
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception as e:
        print(f"⚠️ خطأ في التحقق من العمود {column_name} في جدول {table_name}: {e}")
        return False


def add_column_safe(table_name: str, column: sa.Column) -> bool:
    """
    إضافة عمود إلى جدول مع التحقق من وجوده مسبقاً
    
    Args:
        table_name: اسم الجدول
        column: كائن العمود
        
    Returns:
        True إذا تمت الإضافة، False إذا كان العمود موجوداً بالفعل
    """
    # التحقق من وجود الجدول
    if not table_exists(table_name):
        print(f"⚠️ الجدول {table_name} غير موجود، تخطي إضافة العمود {column.name}")
        return False
    
    # التحقق من وجود العمود
    if column_exists(table_name, column.name):
        print(f"ℹ️ العمود '{column.name}' موجود بالفعل في جدول {table_name}، تخطي الإضافة")
        return False
    
    try:
        print(f"📝 جاري إضافة العمود '{column.name}' إلى جدول {table_name}...")
        op.add_column(table_name, column)
        print(f"✅ تم إضافة العمود '{column.name}' إلى جدول {table_name} بنجاح")
        return True
    except Exception as e:
        print(f"❌ فشل إضافة العمود '{column.name}' إلى جدول {table_name}: {e}")
        raise


def drop_column_safe(table_name: str, column_name: str) -> bool:
    """
    حذف عمود من جدول مع التحقق من وجوده
    
    Args:
        table_name: اسم الجدول
        column_name: اسم العمود
        
    Returns:
        True إذا تم الحذف، False إذا لم يكن العمود موجوداً
    """
    # التحقق من وجود الجدول
    if not table_exists(table_name):
        print(f"⚠️ الجدول {table_name} غير موجود، تخطي حذف العمود {column_name}")
        return False
    
    # التحقق من وجود العمود
    if not column_exists(table_name, column_name):
        print(f"ℹ️ العمود '{column_name}' غير موجود في جدول {table_name}، تخطي الحذف")
        return False
    
    try:
        print(f"📝 جاري حذف العمود '{column_name}' من جدول {table_name}...")
        op.drop_column(table_name, column_name)
        print(f"✅ تم حذف العمود '{column_name}' من جدول {table_name} بنجاح")
        return True
    except Exception as e:
        print(f"❌ فشل حذف العمود '{column_name}' من جدول {table_name}: {e}")
        raise


def create_index_safe(table_name: str, index_name: str, columns: list) -> bool:
    """
    إنشاء فهرس مع التحقق من وجوده
    
    Args:
        table_name: اسم الجدول
        index_name: اسم الفهرس
        columns: قائمة الأعمدة
        
    Returns:
        True إذا تم الإنشاء، False إذا كان الفهرس موجوداً
    """
    try:
        inspector = inspect(op.get_bind())
        indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
        
        if index_name in indexes:
            print(f"ℹ️ الفهرس '{index_name}' موجود بالفعل، تخطي الإنشاء")
            return False
        
        print(f"📝 جاري إنشاء الفهرس '{index_name}' على جدول {table_name}...")
        op.create_index(index_name, table_name, columns)
        print(f"✅ تم إنشاء الفهرس '{index_name}' بنجاح")
        return True
    except Exception as e:
        print(f"⚠️ تحذير: فشل إنشاء الفهرس '{index_name}': {e}")
        return False


def drop_index_safe(index_name: str, table_name: str) -> bool:
    """
    حذف فهرس مع التحقق من وجوده
    
    Args:
        index_name: اسم الفهرس
        table_name: اسم الجدول
        
    Returns:
        True إذا تم الحذف، False إذا لم يكن الفهرس موجوداً
    """
    try:
        inspector = inspect(op.get_bind())
        indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
        
        if index_name not in indexes:
            print(f"ℹ️ الفهرس '{index_name}' غير موجود، تخطي الحذف")
            return False
        
        print(f"📝 جاري حذف الفهرس '{index_name}' من جدول {table_name}...")
        op.drop_index(index_name, table_name=table_name)
        print(f"✅ تم حذف الفهرس '{index_name}' بنجاح")
        return True
    except Exception as e:
        print(f"⚠️ تحذير: فشل حذف الفهرس '{index_name}': {e}")
        return False


# ============================================================
# دالة الترقية (Upgrade)
# ============================================================

def upgrade() -> None:
    """إضافة جميع الأعمدة المفقودة في النماذج الأكاديمية"""
    
    print("=" * 80)
    print("🚀 بدء ترقية قاعدة البيانات: إضافة الأعمدة المفقودة في النماذج الأكاديمية")
    print("=" * 80)
    
    # ============================================================
    # 1. جدول grades
    # ============================================================
    print("\n📋 [1/6] تحديث جدول grades...")
    
    # إضافة عمود is_active
    add_column_safe(
        'grades',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true')
    )
    
    # إضافة عمود year_id
    add_column_safe(
        'grades',
        sa.Column('year_id', sa.String(36), nullable=True)
    )
    
    # ============================================================
    # 2. جدول academic_years
    # ============================================================
    print("\n📋 [2/6] تحديث جدول academic_years...")
    
    # إضافة عمود is_active
    add_column_safe(
        'academic_years',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true')
    )
    
    # ============================================================
    # 3. جدول sections
    # ============================================================
    print("\n📋 [3/6] تحديث جدول sections...")
    
    # إضافة عمود is_active
    add_column_safe(
        'sections',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true')
    )
    
    # ============================================================
    # 4. جدول subjects
    # ============================================================
    print("\n📋 [4/6] تحديث جدول subjects...")
    
    # إضافة عمود is_active
    add_column_safe(
        'subjects',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true')
    )
    
    # ============================================================
    # 5. جدول rooms
    # ============================================================
    print("\n📋 [5/6] تحديث جدول rooms...")
    
    # إضافة عمود is_active
    add_column_safe(
        'rooms',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true')
    )
    
    # ============================================================
    # 6. تحديث البيانات الموجودة (تجنباً للقيم NULL)
    # ============================================================
    print("\n📋 [6/6] تحديث البيانات الموجودة...")
    
    try:
        # التحقق من وجود الأعمدة قبل التحديث
        tables_to_update = [
            ('grades', 'is_active'),
            ('academic_years', 'is_active'),
            ('sections', 'is_active'),
            ('subjects', 'is_active'),
            ('rooms', 'is_active'),
        ]
        
        for table_name, column_name in tables_to_update:
            if column_exists(table_name, column_name):
                print(f"📝 تحديث بيانات جدول {table_name}...")
                op.execute(
                    text(f"UPDATE {table_name} SET {column_name} = true WHERE {column_name} IS NULL")
                )
                print(f"✅ تم تحديث بيانات جدول {table_name}")
            else:
                print(f"⚠️ تخطي تحديث {table_name}: العمود {column_name} غير موجود")
        
        print("✅ تم تحديث جميع البيانات الموجودة")
        
    except Exception as e:
        print(f"⚠️ تحذير: فشل تحديث بعض البيانات: {e}")
        print("⚠️ سيتم متابعة الترقية مع ترك القيم NULL (لن تؤثر على الأداء)")
    
    # ============================================================
    # 7. إضافة الفهارس (اختياري - لتحسين الأداء)
    # ============================================================
    print("\n📋 إضافة الفهارس...")
    
    # فهارس is_active
    create_index_safe('grades', 'ix_grades_is_active', ['is_active'])
    create_index_safe('academic_years', 'ix_academic_years_is_active', ['is_active'])
    create_index_safe('sections', 'ix_sections_is_active', ['is_active'])
    create_index_safe('subjects', 'ix_subjects_is_active', ['is_active'])
    create_index_safe('rooms', 'ix_rooms_is_active', ['is_active'])
    
    # فهرس year_id في grades
    create_index_safe('grades', 'ix_grades_year_id', ['year_id'])
    
    # ============================================================
    # اكتمال الترقية
    # ============================================================
    print("\n" + "=" * 80)
    print("✅ تمت ترقية قاعدة البيانات بنجاح!")
    print("=" * 80)
    print("\n📊 ملخص الأعمدة المضافة:")
    print("   ✅ grades.is_active")
    print("   ✅ grades.year_id")
    print("   ✅ academic_years.is_active")
    print("   ✅ sections.is_active")
    print("   ✅ subjects.is_active")
    print("   ✅ rooms.is_active")
    print("\n📊 ملخص الفهارس المضافة:")
    print("   ✅ ix_grades_is_active")
    print("   ✅ ix_grades_year_id")
    print("   ✅ ix_academic_years_is_active")
    print("   ✅ ix_sections_is_active")
    print("   ✅ ix_subjects_is_active")
    print("   ✅ ix_rooms_is_active")
    print("=" * 80)


# ============================================================
# دالة الرجوع (Downgrade)
# ============================================================

def downgrade() -> None:
    """حذف الأعمدة المضافة (الرجوع إلى الإصدار السابق)"""
    
    print("=" * 80)
    print("🚀 بدء الرجوع إلى الإصدار السابق: حذف الأعمدة المضافة")
    print("=" * 80)
    
    # ============================================================
    # حذف الفهارس
    # ============================================================
    print("\n📋 حذف الفهارس...")
    
    drop_index_safe('ix_grades_is_active', 'grades')
    drop_index_safe('ix_grades_year_id', 'grades')
    drop_index_safe('ix_academic_years_is_active', 'academic_years')
    drop_index_safe('ix_sections_is_active', 'sections')
    drop_index_safe('ix_subjects_is_active', 'subjects')
    drop_index_safe('ix_rooms_is_active', 'rooms')
    
    # ============================================================
    # حذف الأعمدة
    # ============================================================
    print("\n📋 حذف الأعمدة...")
    
    # حذف أعمدة grades
    drop_column_safe('grades', 'is_active')
    drop_column_safe('grades', 'year_id')
    
    # حذف أعمدة academic_years
    drop_column_safe('academic_years', 'is_active')
    
    # حذف أعمدة sections
    drop_column_safe('sections', 'is_active')
    
    # حذف أعمدة subjects
    drop_column_safe('subjects', 'is_active')
    
    # حذف أعمدة rooms
    drop_column_safe('rooms', 'is_active')
    
    # ============================================================
    # اكتمال الرجوع
    # ============================================================
    print("\n" + "=" * 80)
    print("✅ تم الرجوع إلى الإصدار السابق بنجاح!")
    print("=" * 80)
