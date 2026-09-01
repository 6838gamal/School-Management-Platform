"""Async database engine, session factory, and declarative Base."""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# إعدادات SSL - asyncpg يقبل ssl وليس sslmode
connect_args = {}
if settings.DATABASE_SSL:
    connect_args["ssl"] = True

def get_database_url():
    """
    الحصول على URL قاعدة البيانات المناسب للتطبيق.
    
    إذا كان URL يستخدم psycopg2 (postgresql://)، قم بتحويله إلى asyncpg.
    وإذا كان يستخدم asyncpg بالفعل، استخدمه كما هو.
    """
    url = settings.DATABASE_URL
    
    # التحقق من أن URL هو PostgreSQL
    if "postgresql" not in url:
        raise ValueError(
            f"❌ DATABASE_URL must be a PostgreSQL URL. Current: {url}"
        )
    
    # إذا كان URL يستخدم psycopg2 (بدون asyncpg)، قم بتحويله
    if "postgresql://" in url and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    
    return url

# الحصول على URL المناسب
DATABASE_URL = get_database_url()

# إنشاء محرك قاعدة البيانات غير المتزامن
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    connect_args=connect_args,  # ✅ إعدادات SSL
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async session and rolls back on error."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
