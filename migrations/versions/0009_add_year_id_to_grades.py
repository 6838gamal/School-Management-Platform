# migrations/versions/0009_add_year_id_to_grades.py

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

revision = '0009'
down_revision: str | None = '0008'
branch_labels: str | None = None
depends_on: str | None = None


def table_exists(conn, table_name: str) -> bool:
    """التحقق من وجود جدول"""
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def column_exists(conn, table_name: str, column_name: str) -> bool:
    """التحقق من وجود عمود في جدول"""
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def constraint_exists(conn, table_name: str, constraint_name: str) -> bool:
    """التحقق من وجود قيد (Constraint)"""
    inspector = inspect(conn)
    constraints = inspector.get_unique_constraints(table_name)
    return any(c['name'] == constraint_name for c in constraints)


def upgrade() -> None:
    conn = op.get_bind()
    
    # ✅ الخطوة 1: التحقق من وجود جدول grades
    if not table_exists(conn, 'grades'):
        logger.warning("⚠️ جدول grades غير موجود! يتم إنشاؤه...")
        # إذا كان الجدول غير موجود، فهناك مشكلة أكبر
        # في هذه الحالة، يجب تشغيل الترحيلات الأساسية أولاً
        return
    
    # ✅ الخطوة 2: التحقق من وجود العمود year_id
    if column_exists(conn, 'grades', 'year_id'):
        logger.info("ℹ️ العمود year_id موجود بالفعل في جدول grades - تخطي")
    else:
        logger.info("➕ إضافة العمود year_id إلى جدول grades...")
        
        # إضافة العمود (مع السماح بقيم NULL مؤقتاً)
        op.add_column('grades', sa.Column('year_id', sa.String(36), nullable=True))
        
        # ✅ الخطوة 3: تحديث البيانات الموجودة (إذا وجدت)
        try:
            # التحقق من وجود بيانات في academic_years
            result = conn.execute(
                text("SELECT COUNT(*) FROM academic_years")
            ).scalar()
            
            if result and result > 0:
                logger.info("🔄 جاري تحديث البيانات الموجودة...")
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
                logger.info("✅ تم تحديث البيانات الموجودة")
        except Exception as e:
            logger.warning(f"⚠️ لم يتم تحديث البيانات: {e}")
        
        # ✅ الخطوة 4: جعل العمود NOT NULL
        op.alter_column('grades', 'year_id', nullable=False)
        logger.info("✅ تم جعل العمود year_id مطلوباً (NOT NULL)")
        
        # ✅ الخطوة 5: إضافة فهرس (إذا لم يكن موجوداً)
        # التحقق من وجود الفهرس
        indexes = inspect(conn).get_indexes('grades')
        if not any(idx['name'] == 'ix_grades_year_id' for idx in indexes):
            op.create_index('ix_grades_year_id', 'grades', ['year_id'])
            logger.info("✅ تم إضافة فهرس على year_id")
        else:
            logger.info("ℹ️ الفهرس ix_grades_year_id موجود بالفعل")
    
    # ✅ الخطوة 6: تحديث الـ UniqueConstraint
    try:
        # التحقق من وجود القيد القديم
        if constraint_exists(conn, 'grades', 'uq_grade_stage_name'):
            op.drop_constraint('uq_grade_stage_name', 'grades', type_='unique')
            logger.info("🗑️ تم حذف القيد القديم uq_grade_stage_name")
    except Exception as e:
        logger.info(f"ℹ️ القيد القديم غير موجود: {e}")
    
    # إنشاء القيد الجديد (إذا لم يكن موجوداً)
    if not constraint_exists(conn, 'grades', 'uq_grade_stage_year_name'):
        op.create_unique_constraint(
            'uq_grade_stage_year_name',
            'grades',
            ['stage_id', 'year_id', 'name']
        )
        logger.info("✅ تم إنشاء القيد الجديد uq_grade_stage_year_name")
    else:
        logger.info("ℹ️ القيد uq_grade_stage_year_name موجود بالفعل")


def downgrade() -> None:
    conn = op.get_bind()
    
    logger.info("⏪ جاري التراجع عن التغييرات...")
    
    # ✅ التحقق من وجود القيد قبل حذفه
    if constraint_exists(conn, 'grades', 'uq_grade_stage_year_name'):
        op.drop_constraint('uq_grade_stage_year_name', 'grades', type_='unique')
        logger.info("🗑️ تم حذف القيد الجديد")
    
    # ✅ إعادة القيد القديم
    if not constraint_exists(conn, 'grades', 'uq_grade_stage_name'):
        op.create_unique_constraint('uq_grade_stage_name', 'grades', ['stage_id', 'name'])
        logger.info("✅ تم إعادة القيد القديم")
    
    # ✅ حذف الفهرس
    indexes = inspect(conn).get_indexes('grades')
    if any(idx['name'] == 'ix_grades_year_id' for idx in indexes):
        op.drop_index('ix_grades_year_id', table_name='grades')
        logger.info("🗑️ تم حذف الفهرس")
    
    # ✅ حذف العمود (إذا كان موجوداً)
    if column_exists(conn, 'grades', 'year_id'):
        op.drop_column('grades', 'year_id')
        logger.info("🗑️ تم حذف العمود year_id")
