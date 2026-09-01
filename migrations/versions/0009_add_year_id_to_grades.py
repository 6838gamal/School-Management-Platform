# app/migrations/versions/0009_add_year_id_to_grades.py

"""Add year_id to grades

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-01 15:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
import logging

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision = '0009'
down_revision: str | None = '0008'  # تأكد من أن هذا المعرف صحيح
branch_labels: str | None = None
depends_on: str | None = None


def table_exists(conn, table_name: str) -> bool:
    """التحقق من وجود جدول"""
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def column_exists(conn, table_name: str, column_name: str) -> bool:
    """التحقق من وجود عمود في جدول"""
    inspector = inspect(conn)
    
    if table_name not in inspector.get_table_names():
        return False
    
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def constraint_exists(conn, table_name: str, constraint_name: str) -> bool:
    """التحقق من وجود قيد (Constraint)"""
    inspector = inspect(conn)
    
    if table_name not in inspector.get_table_names():
        return False
    
    constraints = inspector.get_unique_constraints(table_name)
    return any(c['name'] == constraint_name for c in constraints)


def index_exists(conn, table_name: str, index_name: str) -> bool:
    """التحقق من وجود فهرس"""
    inspector = inspect(conn)
    
    if table_name not in inspector.get_table_names():
        return False
    
    indexes = inspector.get_indexes(table_name)
    return any(idx['name'] == index_name for idx in indexes)


def upgrade() -> None:
    """تطبيق الترحيل - إضافة year_id إلى جدول grades"""
    conn = op.get_bind()
    
    logger.info("🚀 بدء ترحيل إضافة year_id إلى جدول grades...")
    
    # ============================================================
    # 1. التحقق من وجود جدول grades
    # ============================================================
    if not table_exists(conn, 'grades'):
        logger.warning("⚠️ جدول grades غير موجود! لا يمكن المتابعة.")
        logger.warning("💡 تأكد من تشغيل الترحيلات الأساسية أولاً.")
        return
    
    # ============================================================
    # 2. التحقق من وجود العمود year_id
    # ============================================================
    if column_exists(conn, 'grades', 'year_id'):
        logger.info("ℹ️ العمود year_id موجود بالفعل في جدول grades - تخطي الإضافة")
    else:
        logger.info("➕ إضافة العمود year_id إلى جدول grades...")
        
        # إضافة العمود (مع السماح بقيم NULL مؤقتاً)
        op.add_column('grades', sa.Column('year_id', sa.String(36), nullable=True))
        logger.info("✅ تم إضافة العمود year_id (NULL مؤقتاً)")
        
        # ============================================================
        # 3. تحديث البيانات الموجودة
        # ============================================================
        try:
            # التحقق من وجود جدول academic_years
            if table_exists(conn, 'academic_years'):
                # التحقق من وجود بيانات في academic_years
                result = conn.execute(
                    text("SELECT COUNT(*) FROM academic_years")
                ).scalar()
                
                if result and result > 0:
                    logger.info(f"🔄 جاري تحديث {result} صف...")
                    
                    # تحديث الصفوف التي ليس لها year_id
                    update_result = conn.execute(
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
                    
                    logger.info(f"✅ تم تحديث {update_result.rowcount} صف")
                else:
                    logger.warning("⚠️ لا توجد بيانات في جدول academic_years")
                    logger.warning("💡 سيتم تعيين year_id = NULL مؤقتاً")
            else:
                logger.warning("⚠️ جدول academic_years غير موجود")
                logger.warning("💡 سيتم تعيين year_id = NULL مؤقتاً")
                
        except Exception as e:
            logger.warning(f"⚠️ فشل تحديث البيانات: {e}")
            logger.warning("💡 سيتم تعيين year_id = NULL مؤقتاً")
        
        # ============================================================
        # 4. جعل العمود NOT NULL (فقط إذا كانت جميع البيانات محدثة)
        # ============================================================
        try:
            # التحقق من عدم وجود قيم NULL
            null_count = conn.execute(
                text("SELECT COUNT(*) FROM grades WHERE year_id IS NULL")
            ).scalar()
            
            if null_count and null_count > 0:
                logger.warning(f"⚠️ يوجد {null_count} صف بقيم NULL في year_id")
                logger.warning("💡 سيتم ترك العمود nullable مؤقتاً")
            else:
                op.alter_column('grades', 'year_id', nullable=False)
                logger.info("✅ تم جعل العمود year_id مطلوباً (NOT NULL)")
        except Exception as e:
            logger.warning(f"⚠️ فشل جعل العمود NOT NULL: {e}")
            logger.warning("💡 سيتم ترك العمود nullable مؤقتاً")
        
        # ============================================================
        # 5. إضافة فهرس
        # ============================================================
        if not index_exists(conn, 'grades', 'ix_grades_year_id'):
            op.create_index('ix_grades_year_id', 'grades', ['year_id'])
            logger.info("✅ تم إضافة فهرس ix_grades_year_id")
        else:
            logger.info("ℹ️ الفهرس ix_grades_year_id موجود بالفعل")
    
    # ============================================================
    # 6. تحديث الـ UniqueConstraint
    # ============================================================
    # حذف القيد القديم إذا كان موجوداً
    if constraint_exists(conn, 'grades', 'uq_grade_stage_name'):
        try:
            op.drop_constraint('uq_grade_stage_name', 'grades', type_='unique')
            logger.info("🗑️ تم حذف القيد القديم uq_grade_stage_name")
        except Exception as e:
            logger.warning(f"⚠️ فشل حذف القيد القديم: {e}")
    
    # إنشاء القيد الجديد (إذا لم يكن موجوداً)
    if not constraint_exists(conn, 'grades', 'uq_grade_stage_year_name'):
        try:
            op.create_unique_constraint(
                'uq_grade_stage_year_name',
                'grades',
                ['stage_id', 'year_id', 'name']
            )
            logger.info("✅ تم إنشاء القيد الجديد uq_grade_stage_year_name")
        except Exception as e:
            logger.warning(f"⚠️ فشل إنشاء القيد الجديد: {e}")
    else:
        logger.info("ℹ️ القيد uq_grade_stage_year_name موجود بالفعل")
    
    logger.info("✅ تم الانتهاء من ترحيل year_id بنجاح!")


def downgrade() -> None:
    """التراجع عن الترحيل - حذف year_id من جدول grades"""
    conn = op.get_bind()
    
    logger.info("⏪ بدء التراجع عن ترحيل year_id...")
    
    # ============================================================
    # 1. التحقق من وجود جدول grades
    # ============================================================
    if not table_exists(conn, 'grades'):
        logger.warning("⚠️ جدول grades غير موجود! لا يمكن المتابعة.")
        return
    
    # ============================================================
    # 2. حذف القيد الجديد
    # ============================================================
    if constraint_exists(conn, 'grades', 'uq_grade_stage_year_name'):
        try:
            op.drop_constraint('uq_grade_stage_year_name', 'grades', type_='unique')
            logger.info("🗑️ تم حذف القيد uq_grade_stage_year_name")
        except Exception as e:
            logger.warning(f"⚠️ فشل حذف القيد: {e}")
    
    # ============================================================
    # 3. إعادة القيد القديم (إذا لم يكن موجوداً)
    # ============================================================
    if not constraint_exists(conn, 'grades', 'uq_grade_stage_name'):
        try:
            op.create_unique_constraint('uq_grade_stage_name', 'grades', ['stage_id', 'name'])
            logger.info("✅ تم إعادة القيد uq_grade_stage_name")
        except Exception as e:
            logger.warning(f"⚠️ فشل إنشاء القيد القديم: {e}")
    
    # ============================================================
    # 4. حذف الفهرس
    # ============================================================
    if index_exists(conn, 'grades', 'ix_grades_year_id'):
        try:
            op.drop_index('ix_grades_year_id', table_name='grades')
            logger.info("🗑️ تم حذف الفهرس ix_grades_year_id")
        except Exception as e:
            logger.warning(f"⚠️ فشل حذف الفهرس: {e}")
    
    # ============================================================
    # 5. حذف العمود (إذا كان موجوداً)
    # ============================================================
    if column_exists(conn, 'grades', 'year_id'):
        try:
            op.drop_column('grades', 'year_id')
            logger.info("🗑️ تم حذف العمود year_id")
        except Exception as e:
            logger.warning(f"⚠️ فشل حذف العمود: {e}")
    
    logger.info("✅ تم الانتهاء من التراجع عن ترحيل year_id")
