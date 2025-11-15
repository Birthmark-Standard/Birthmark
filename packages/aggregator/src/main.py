"""Main FastAPI application for Birthmark Aggregation Server."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import init_db, close_db, get_db
from src.models import Submission, Batch
from src.api import submissions, verification, sma, ssa
from src.schemas import HealthCheckResponse

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app."""
    # Startup
    logger.info("Starting Birthmark Aggregation Server...")
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Birthmark Aggregation Server...")
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI app
app = FastAPI(
    title="Birthmark Protocol Aggregation Server",
    version="1.0.0",
    description="Phase 1 aggregation server supporting camera and software submissions",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(submissions.router)
app.include_router(verification.router)
app.include_router(sma.router)
app.include_router(ssa.router)


# Exception handlers


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "error_code": "SERVER_ERROR",
            "message": "Internal server error",
        },
    )


# Root endpoint


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint."""
    return {
        "service": "Birthmark Protocol Aggregation Server",
        "version": "1.0.0",
        "phase": "Phase 1 (Mock Backend)",
        "status": "operational",
        "endpoints": {
            "docs": "/docs",
            "submit": "POST /api/v1/submit",
            "verify": "GET /api/v1/verify?image_hash=...",
            "health": "GET /health",
        },
    }


# Health check endpoint


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint.

    Returns service status and basic statistics.
    """
    try:
        # Check database connectivity
        async for db in get_db():
            # Count pending submissions
            stmt = select(func.count()).select_from(Submission).where(Submission.batch_id.is_(None))
            result = await db.execute(stmt)
            pending_count = result.scalar_one()

            # Get last batch time
            stmt = select(Batch.created_at).order_by(Batch.created_at.desc()).limit(1)
            result = await db.execute(stmt)
            last_batch = result.scalar_one_or_none()

            return HealthCheckResponse(
                status="healthy",
                database="connected",
                pending_submissions=pending_count,
                last_batch=last_batch.isoformat() + "Z" if last_batch else None,
                timestamp=datetime.now(timezone.utc).isoformat() + "Z",
            )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            database="disconnected",
            timestamp=datetime.now(timezone.utc).isoformat() + "Z",
        )


# Metrics endpoint (simple for Phase 1)


@app.get("/metrics")
async def metrics():
    """Simple metrics endpoint for monitoring."""
    try:
        async for db in get_db():
            # Total submissions
            stmt = select(func.count()).select_from(Submission)
            result = await db.execute(stmt)
            total_submissions = result.scalar_one()

            # Validated submissions
            stmt = (
                select(func.count())
                .select_from(Submission)
                .where(Submission.validation_status == "validated")
            )
            result = await db.execute(stmt)
            validated_count = result.scalar_one()

            # Failed validations
            stmt = (
                select(func.count())
                .select_from(Submission)
                .where(Submission.validation_status == "validation_failed")
            )
            result = await db.execute(stmt)
            failed_count = result.scalar_one()

            # Total batches
            stmt = select(func.count()).select_from(Batch)
            result = await db.execute(stmt)
            total_batches = result.scalar_one()

            # Camera vs software breakdown
            stmt = (
                select(func.count())
                .select_from(Submission)
                .where(Submission.submission_type == "camera")
            )
            result = await db.execute(stmt)
            camera_count = result.scalar_one()

            stmt = (
                select(func.count())
                .select_from(Submission)
                .where(Submission.submission_type == "software")
            )
            result = await db.execute(stmt)
            software_count = result.scalar_one()

            return {
                "submissions": {
                    "total": total_submissions,
                    "camera": camera_count,
                    "software": software_count,
                    "validated": validated_count,
                    "failed": failed_count,
                },
                "batches": {
                    "total": total_batches,
                },
            }
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        return {"error": "Failed to collect metrics"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
