"""Configuration management for Birthmark Aggregation Server."""

import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/birthmark_dev",
        description="Async database URL for runtime",
    )
    database_url_sync: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/birthmark_dev",
        description="Sync database URL for Alembic migrations",
    )

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=True, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # Batch Configuration
    batch_size: int = Field(default=1000, description="Number of images per batch")
    batch_worker_interval: int = Field(
        default=60, description="Batch worker check interval (seconds)"
    )

    # Validation Configuration
    validation_worker_interval: int = Field(
        default=10, description="Validation worker check interval (seconds)"
    )

    # SMA Configuration (Phase 1: Internal Mock)
    sma_endpoint: str = Field(
        default="http://localhost:8000/sma/validate", description="SMA validation endpoint"
    )
    sma_enabled: bool = Field(default=True, description="Enable SMA validation")

    # SSA Configuration (Phase 1: Internal Mock)
    ssa_endpoint: str = Field(
        default="http://localhost:8000/ssa/validate", description="SSA validation endpoint"
    )
    ssa_enabled: bool = Field(default=True, description="Enable SSA validation")

    # Blockchain Configuration (Phase 1: Mock)
    blockchain_enabled: bool = Field(default=False, description="Enable blockchain posting")
    zksync_rpc_url: str = Field(
        default="https://testnet.era.zksync.dev", description="zkSync RPC URL"
    )
    zksync_private_key: str = Field(default="", description="zkSync private key")

    # Rate Limiting
    rate_limit_per_minute: int = Field(
        default=100, description="Rate limit per IP per minute"
    )

    # CORS Configuration
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins",
    )


# Global settings instance
settings = Settings()
