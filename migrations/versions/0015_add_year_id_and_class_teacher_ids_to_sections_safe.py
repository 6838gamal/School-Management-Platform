# alembic/versions/0015_add_year_id_and_class_teacher_ids_to_sections_safe.py

"""Add year_id and class_teacher_ids to sections table (Safe version)

Revision ID: xxxx
Revises: previous_revision_id
Create Date: 2026-09-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
import logging

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '0015'
down_revision: Union[str, None] = '0014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """التحقق من وجود عمود في الجدول"""
    try:
        inspector = inspect(op.get_bind())
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception as e:
        logger.warning(f"Error checking column {column_name}: {e}")
        return False


def table_exists(table_name: str) -> bool:
    """التحقق من وجود جدول"""
    try:
        inspector = inspect(op.get_bind())
        return table_name in inspector.get_table_names()
    except Exception as e:
        logger.warning(f"Error checking table {table_name}: {e}")
        return False


def index_exists(table_name: str, index_name: str) -> bool:
    """التحقق من وجود فهرس"""
    try:
        inspector = inspect(op.get_bind())
        indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
        return index_name in indexes
    except Exception as e:
        logger.warning(f"Error checking index {index_name}: {e}")
        return False


def upgrade() -> None:
    """إضافة الأعمدة الجديدة إلى جدول sections مع التحقق الكامل"""
    
    # التحقق من وجود الجدول
    if not table_exists('sections'):
        logger.warning("Table 'sections' does not exist, skipping migration")
        return
    
    conn = op.get_bind()
    
    # ========== 1. إضافة عمود year_id ==========
    if not column_exists('sections', 'year_id'):
        logger.info("Adding column 'year_id' to 'sections'")
        
        # إضافة العمود (nullable مؤقتاً)
        op.add_column(
            'sections',
            sa.Column(
                'year_id',
                sa.String(36),
                nullable=True,
                comment='معرف السنة الدراسية'
            )
        )
        
        # تحديث البيانات الموجودة
        try:
            # التحقق من وجود year_id في جدول grades
            if column_exists('grades', 'year_id'):
                # SQLite vs PostgreSQL/MySQL
                dialect = conn.dialect.name
                
                if dialect == 'sqlite':
                    # SQLite لا يدعم UPDATE مع FROM بنفس الطريقة
                    op.execute("""
                        UPDATE sections 
                        SET year_id = (
                            SELECT year_id FROM grades 
                            WHERE grades.id = sections.grade_id
                        )
                        WHERE year_id IS NULL
                    """)
                else:
                    # PostgreSQL, MySQL, etc.
                    op.execute("""
                        UPDATE sections s
                        SET year_id = g.year_id
                        FROM grades g
                        WHERE s.grade_id = g.id
                        AND s.year_id IS NULL
                    """)
                
                logger.info("Updated existing sections with year_id from grades")
            else:
                logger.warning("Column 'year_id' not found in 'grades', skipping data update")
                
        except Exception as e:
            logger.error(f"Error updating year_id: {e}")
            # الاستمرار في الترحيل حتى لو فشل التحديث
        
        # جعل العمود NOT NULL (إذا كانت جميع البيانات محدثة)
        try:
            # التحقق من وجود قيم NULL
            result = conn.execute(text("SELECT COUNT(*) FROM sections WHERE year_id IS NULL"))
            count = result.scalar()
            
            if count == 0:
                op.alter_column(
                    'sections',
                    'year_id',
                    nullable=False
                )
                logger.info("Set year_id as NOT NULL")
            else:
                logger.warning(f"{count} rows have NULL year_id, keeping as nullable")
                
        except Exception as e:
            logger.error(f"Error setting year_id NOT NULL: {e}")
        
        # إضافة فهرس
        if not index_exists('sections', 'ix_sections_year_id'):
            op.create_index(
                'ix_sections_year_id',
                'sections',
                ['year_id']
            )
            logger.info("Created index on year_id")
    
    else:
        logger.info("Column 'year_id' already exists, skipping")
    
    # ========== 2. إضافة عمود class_teacher_ids ==========
    if not column_exists('sections', 'class_teacher_ids'):
        logger.info("Adding column 'class_teacher_ids' to 'sections'")
        
        op.add_column(
            'sections',
            sa.Column(
                'class_teacher_ids',
                sa.String(500),
                nullable=True,
                comment='معرفات المعلمين رؤساء الفصل مفصولة بفواصل'
            )
        )
        logger.info("Column 'class_teacher_ids' added successfully")
    else:
        logger.info("Column 'class_teacher_ids' already exists, skipping")


def downgrade() -> None:
    """حذف الأعمدة المضافة (التراجع) مع التحقق الكامل"""
    
    if not table_exists('sections'):
        return
    
    # ========== 1. حذف عمود class_teacher_ids ==========
    if column_exists('sections', 'class_teacher_ids'):
        logger.info("Dropping column 'class_teacher_ids'")
        op.drop_column('sections', 'class_teacher_ids')
    
    # ========== 2. حذف عمود year_id ==========
    if column_exists('sections', 'year_id'):
        logger.info("Dropping column 'year_id'")
        
        # حذف الفهرس إذا كان موجوداً
        if index_exists('sections', 'ix_sections_year_id'):
            try:
                op.drop_index('ix_sections_year_id', table_name='sections')
                logger.info("Dropped index on year_id")
            except Exception as e:
                logger.warning(f"Could not drop index: {e}")
        
        # حذف العمود
        op.drop_column('sections', 'year_id')
        logger.info("Column 'year_id' dropped successfully")
