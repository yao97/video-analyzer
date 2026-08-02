"""
FastAPI application entry point.
Configures middleware, routes, exception handlers, and startup/shutdown events.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.core.limiter import limiter
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.db.session import close_db, init_db
from app.api.v1.routes import upload, transcribe, analyze, jobs, health, websocket

settings = get_settings()
configure_logging(debug=settings.debug)
log = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # Startup
    log.info("app_starting", version=settings.app_version, debug=settings.debug)

    # Initialize MinIO bucket
    try:
        from app.services.storage import StorageService
        storage = StorageService()
        storage.ensure_bucket()
        log.info("minio_bucket_ready", bucket=settings.minio_bucket)
    except Exception as e:
        log.warning("minio_init_failed", error=str(e))

    # Run database migrations (in production, use alembic upgrade head)
    if settings.debug:
        try:
            await init_db()
            log.info("db_initialized")
        except Exception as e:
            log.warning("db_init_failed", error=str(e))

    log.info("app_started", api_port=8766)

    yield

    # Shutdown
    log.info("app_stopping")
    await close_db()
    log.info("app_stopped")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Video Content Analyzer Backend API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# === Middleware ===

# Request ID middleware
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Add a unique request ID to every request for tracing."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# CORS (Bug #4 fix: whitelist, not wildcard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# Rate limiter (single shared instance — see app.core.limiter)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Exception handlers
register_exception_handlers(app)

# === Routes ===
app.include_router(health.router)
app.include_router(upload.router)
app.include_router(transcribe.router)
app.include_router(analyze.router)
app.include_router(jobs.router)
app.include_router(websocket.router)

# === Prometheus Metrics ===
Instrumentator(
    excluded_handlers=["/health", "/ready", "/metrics"],
    should_round_latency_decimals=True,
).instrument(app).expose(app, endpoint="/metrics")

# === Root endpoint ===
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8766,
        reload=settings.debug,
        workers=1 if settings.debug else 2,
    )
