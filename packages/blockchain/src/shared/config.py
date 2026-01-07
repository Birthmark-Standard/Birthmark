# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""Configuration management for Birthmark Blockchain Node."""

from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Node Identity
    node_id: str = "validator_001"
    validator_key_path: str = "/data/keys/validator.key"

    # Database
    database_url: str = "postgresql://birthmark:birthmark@localhost:5432/birthmark_chain"
    database_pool_size: int = 20
    database_max_overflow: int = 40

    # Aggregator Settings
    sma_validation_endpoint: str = "http://localhost:8001/validate"
    sma_request_timeout: int = 5
    batch_size_min: int = 100
    batch_size_max: int = 1000
    batch_timeout_seconds: int = 300

    # Consensus
    consensus_mode: Literal["single", "poa"] = "single"
    validator_nodes: str = ""  # Comma-separated list for Phase 2+

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8545
    api_workers: int = 4
    enable_public_verification: bool = True
    cors_origins: str = "*"

    # P2P Networking (Phase 2+)
    p2p_enabled: bool = False
    p2p_port: int = 26656
    p2p_peers: str = ""  # Comma-separated peer addresses

    # Logging
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"

    # Genesis
    genesis_timestamp: Optional[int] = None
    genesis_validator: Optional[str] = None

    @property
    def validator_nodes_list(self) -> list[str]:
        """Parse validator nodes from comma-separated string."""
        if not self.validator_nodes:
            return []
        return [node.strip() for node in self.validator_nodes.split(",") if node.strip()]

    @property
    def p2p_peers_list(self) -> list[str]:
        """Parse P2P peers from comma-separated string."""
        if not self.p2p_peers:
            return []
        return [peer.strip() for peer in self.p2p_peers.split(",") if peer.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


# Global settings instance
settings = Settings()
