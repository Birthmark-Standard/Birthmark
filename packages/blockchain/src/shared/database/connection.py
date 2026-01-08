# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""Database connection and session management."""

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base

from src.shared.config import settings

# Base class for all ORM models
Base = declarative_base()

# Synchronous engine (for migrations and scripts)
sync_engine = create_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.log_level == "DEBUG",
)

# Async engine (for FastAPI endpoints)
async_database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
async_engine = create_async_engine(
    async_database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.log_level == "DEBUG",
)

# Session factories
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


@contextmanager
def get_sync_db() -> Generator[Session, None, None]:
    """Get synchronous database session (for scripts and migrations)."""
    db = SyncSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@asynccontextmanager
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Get asynchronous database session (for FastAPI)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session."""
    async with get_async_db() as session:
        yield session


def create_tables() -> None:
    """Create all database tables (for initial setup)."""
    Base.metadata.create_all(bind=sync_engine)


def drop_tables() -> None:
    """Drop all database tables (for testing)."""
    Base.metadata.drop_all(bind=sync_engine)
