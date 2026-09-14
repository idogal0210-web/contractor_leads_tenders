"""
core/db/session.py — ניהול חיבורי מסד נתונים עם SQLAlchemy 2.x.

מספק:
- מנוע אסינכרוני (asyncpg) לשימוש ב-FastAPI
- מנוע סינכרוני (psycopg2) לשימוש ב-Celery tasks
- AsyncSessionLocal ו-SessionLocal לפתיחת sessions
- get_db() — dependency injection אסינכרוני ל-FastAPI
- Base — declarative base לכל המודלים
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

import structlog
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config.settings import settings

logger = structlog.get_logger(__name__)


# =============================================================================
# Base — בסיס לכל מודלי SQLAlchemy
# =============================================================================

class Base(DeclarativeBase):
    """Declarative base class לכל מודלי ה-ORM במערכת."""
    pass


# =============================================================================
# כתובות חיבור — המרה בין דרייברים
# =============================================================================

def _async_db_url(sync_url: str) -> str:
    """
    ממיר כתובת sync ל-async לצורך AsyncEngine.
    """
    if sync_url.startswith("postgresql+psycopg2://"):
        return sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if sync_url.startswith("postgresql://"):
        return sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if sync_url.startswith("sqlite:///"):
        return sync_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return sync_url


_SYNC_DB_URL: str = settings.supabase_db_url
_ASYNC_DB_URL: str = _async_db_url(_SYNC_DB_URL)


# =============================================================================
# מנועים (Engines) — תמיכה ב-PostgreSQL וב-SQLite
# =============================================================================

if _SYNC_DB_URL.startswith("sqlite"):
    sync_engine = create_engine(
        _SYNC_DB_URL,
        connect_args={"check_same_thread": False},
        echo=settings.debug,
    )
    async_engine = create_async_engine(
        _ASYNC_DB_URL,
        echo=settings.debug,
    )
else:
    sync_engine = create_engine(
        _SYNC_DB_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=settings.debug,
    )
    async_engine = create_async_engine(
        _ASYNC_DB_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=settings.debug,
    )

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


def init_db() -> None:
    """יצירת כל הטבלאות ישירות במסד הנתונים."""
    from core.db.models import Base
    Base.metadata.create_all(bind=sync_engine)
    logger.info("database_tables_initialized")


# =============================================================================
# FastAPI Dependency — get_db
# =============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency שמחזיר AsyncSession ומבטיח סגירתה.

    שימוש:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("db_session_error", action="rollback")
            raise
        finally:
            await session.close()


# =============================================================================
# Celery Utility — get_sync_db (context manager)
# =============================================================================

def get_sync_db() -> Session:
    """
    מחזיר Session סינכרוני לשימוש ב-Celery tasks.

    שימוש:
        with get_sync_db() as db:
            db.query(MyModel).all()
    """
    return SessionLocal()
