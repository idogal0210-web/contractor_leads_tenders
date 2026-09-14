"""
api/main.py — אפליקציית FastAPI ראשית.

מרכז את כל הנתיבים, middleware וניהול מחזור חיי האפליקציה.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings

log = structlog.get_logger(__name__)


# =============================================================================
# Lifespan — startup / shutdown
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """ניהול מחזור חיי האפליקציה — startup ו-shutdown."""
    # Startup
    log.info(
        "startup",
        environment=settings.environment,
        debug=settings.debug,
        version="1.0.0",
    )

    # בדיקת חיבור ל-DB בזמן אתחול
    try:
        from core.db.session import async_engine
        from sqlalchemy import text
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        log.info("db_connection_ok")
    except Exception as exc:
        # לא עוצרים את ה-startup — מאפשרים degraded mode
        log.warning("db_connection_failed", error=str(exc))

    yield

    # Shutdown
    log.info("shutdown")
    try:
        from core.db.session import async_engine
        await async_engine.dispose()
        log.info("db_engine_disposed")
    except Exception as exc:
        log.warning("db_dispose_error", error=str(exc))


# =============================================================================
# יצירת האפליקציה
# =============================================================================

app = FastAPI(
    title="מערכת איתור לידים ומכרזים",
    description="Lead and Tender Management for Contractors — מערכת ניהול לידים ומכרזים לקבלנים",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================================================
# Middleware
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.is_production else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# נתיבים (Routers)
# =============================================================================

from api.routes import webhooks, dashboard, opportunities, reports  # noqa: E402

app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(dashboard.router, prefix="", tags=["dashboard"])
app.include_router(opportunities.router, prefix="/api/opportunities", tags=["opportunities"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])


# =============================================================================
# Health check
# =============================================================================

@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """בדיקת תקינות — מוחזר על ידי load balancer / k8s."""
    return {"status": "ok", "version": "1.0.0", "environment": settings.environment}


@app.get("/health/db", tags=["system"])
async def health_db() -> dict[str, str]:
    """בדיקת חיבור ל-DB."""
    try:
        from core.db.session import async_engine
        from sqlalchemy import text
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"DB unavailable: {exc}") from exc
