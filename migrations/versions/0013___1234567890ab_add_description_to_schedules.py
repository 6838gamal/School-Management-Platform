# migrations/versions/0013_add_description_to_schedules.py

"""
إضافة عمود description إلى جدول schedules

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-02 10:30:00.000000

@author: فريق التطوير
@description: إضافة وصف للجداول الدراسية لدعم عرض تفاصيل إضافية
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision: str = '0013'
down_revision: Union[str, None] = '0012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
        inspector = inspect(op.get_bind())
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception as e:
        print(f"⚠️ خطأ في التحقق من وجود العمود: {e}")
        return False


def upgrade() -> None:
    """إضافة عمود description إلى جدول schedules"""
    
    print("=" * 60)
    print("🚀 بدء ترقية قاعدة البيانات: إضافة وصف للجداول")
    print("=" * 60)
    
    # ============================================================
    # التحقق من وجود العمود قبل الإضافة
    # ============================================================
    if column_exists('schedules', 'description'):
        print("ℹ️ عمود 'description' موجود بالفعل في جدول schedules")
        print("✅ لا حاجة لإضافة العمود")
        print("=" * 60)
        return
    
    # ============================================================
    # إضافة العمود
    # ============================================================
    print("📝 جاري إضافة عمود 'description' إلى جدول schedules...")
    
    try:
        op.add_column(
            'schedules',
            sa.Column('description', sa.Text(), nullable=True)
        )
        print("✅ تم إضافة عمود 'description' بنجاح")
    except Exception as e:
        print(f"❌ فشل إضافة العمود: {e}")
        raise
    
    # ============================================================
    # (اختياري) تحديث البيانات الموجودة
    # ============================================================
    try:
        print("📝 جاري تحديث البيانات الموجودة...")
        op.execute(
            text("""
                UPDATE schedules 
                SET description = name 
                WHERE description IS NULL
            """)
        )
        print("✅ تم تحديث البيانات الموجودة")
    except Exception as e:
        print(f"⚠️ تحذير: فشل تحديث البيانات: {e}")
        print("⚠️ سيتم متابعة الترقية مع ترك البيانات فارغة")
    
    # ============================================================
    # (اختياري) إضافة فهرس للبحث
    # ============================================================
    # try:
    #     print("📝 جاري إضافة فهرس للبحث...")
    #     op.create_index(
    #         'ix_schedules_description',
    #         'schedules',
    #         ['description']
    #     )
    #     print("✅ تم إضافة الفهرس بنجاح")
    # except Exception as e:
    #     print(f"⚠️ تحذير: فشل إضافة الفهرس: {e}")
    
    print("=" * 60)
    print("✅ تمت ترقية قاعدة البيانات بنجاح")
    print("=" * 60)


def downgrade() -> None:
    """حذف عمود description من جدول schedules"""
    
    print("=" * 60)
    print("🚀 بدء الرجوع إلى الإصدار السابق: حذف وصف الجداول")
    print("=" * 60)
    
    # ============================================================
    # التحقق من وجود العمود قبل الحذف
    # ============================================================
    if not column_exists('schedules', 'description'):
        print("ℹ️ عمود 'description' غير موجود في جدول schedules")
        print("✅ لا حاجة لحذف العمود")
        print("=" * 60)
        return
    
    # ============================================================
    # حذف الفهرس (إذا تم إضافته)
    # ============================================================
    # try:
    #     print("📝 جاري حذف الفهرس...")
    #     op.drop_index('ix_schedules_description', table_name='schedules')
    #     print("✅ تم حذف الفهرس بنجاح")
    # except Exception as e:
    #     print(f"⚠️ تحذير: فشل حذف الفهرس: {e}")
    
    # ============================================================
    # حذف العمود
    # ============================================================
    print("📝 جاري حذف عمود 'description' من جدول schedules...")
    
    try:
        op.drop_column('schedules', 'description')
        print("✅ تم حذف عمود 'description' بنجاح")
    except Exception as e:
        print(f"❌ فشل حذف العمود: {e}")
        raise
    
    print("=" * 60)
    print("✅ تم الرجوع إلى الإصدار السابق بنجاح")
    print("=" * 60)
