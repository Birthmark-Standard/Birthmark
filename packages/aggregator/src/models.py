"""SQLAlchemy database models for Birthmark Aggregation Server."""

import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String,
    Integer,
    BigInteger,
    DateTime,
    Text,
    CheckConstraint,
    Index,
    UniqueConstraint,
    ARRAY,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class Submission(Base):
    """Unified table for both camera and software submissions."""

    __tablename__ = "submissions"

    # Primary key
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Submission type and image data
    submission_type: Mapped[str] = mapped_column(
        String(10), nullable=False, index=True
    )  # 'camera' or 'software'
    image_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    modification_level: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    parent_image_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )

    # Camera-specific fields (NULL for software submissions)
    camera_token_ciphertext: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    camera_token_auth_tag: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    camera_token_nonce: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    table_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    key_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    manufacturer_authority_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    manufacturer_validation_endpoint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Software-specific fields (NULL for camera submissions)
    program_token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    developer_authority_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    developer_version_string: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    developer_validation_endpoint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Common fields
    timestamp: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    validation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    validation_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Transaction grouping (all hashes from same camera submission share this)
    transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    # Batch assignment
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    __table_args__ = (
        CheckConstraint(
            "submission_type IN ('camera', 'software')", name="check_submission_type"
        ),
        CheckConstraint(
            "modification_level >= 0 AND modification_level <= 2",
            name="check_modification_level",
        ),
        CheckConstraint(
            "table_id IS NULL OR (table_id >= 0 AND table_id < 250)", name="check_table_id"
        ),
        CheckConstraint(
            "key_index IS NULL OR (key_index >= 0 AND key_index < 1000)",
            name="check_key_index",
        ),
    )


class Batch(Base):
    """Batches of validated submissions posted to blockchain."""

    __tablename__ = "batches"

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    image_count: Mapped[int] = mapped_column(Integer, nullable=False)
    merkle_root: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    tree_depth: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    zksync_tx_hash: Mapped[Optional[str]] = mapped_column(String(66), nullable=True)
    zksync_block_number: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'merkle_complete', 'posted', 'finalized')",
            name="check_batch_status",
        ),
    )


class MerkleProof(Base):
    """Merkle proofs for image verification."""

    __tablename__ = "merkle_proofs"

    proof_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    image_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    leaf_index: Mapped[int] = mapped_column(Integer, nullable=False)
    proof_path: Mapped[dict] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        UniqueConstraint("batch_id", "image_hash", name="uq_batch_image"),
        Index("idx_merkle_proof_image_hash", "image_hash"),
        Index("idx_merkle_proof_batch_id", "batch_id"),
    )


# SMA (Simulated Manufacturer Authority) Tables


class SMACamera(Base):
    """Registered cameras in the SMA (Phase 1 mock)."""

    __tablename__ = "sma_cameras"

    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    camera_serial: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    manufacturer: Mapped[str] = mapped_column(String(50), nullable=False)
    nuc_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    table_ids: Mapped[List[int]] = mapped_column(ARRAY(Integer), nullable=False)
    provisioned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SMAKeyTable(Base):
    """Key tables for camera token encryption (Phase 1 mock)."""

    __tablename__ = "sma_key_tables"

    table_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    master_key: Mapped[bytes] = mapped_column(String(64), nullable=False)  # 256-bit hex key

    __table_args__ = (
        CheckConstraint("table_id >= 0 AND table_id < 250", name="check_sma_table_id"),
    )


# SSA (Simulated Software Authority) Tables


class SSASoftware(Base):
    """Registered software in the SSA (Phase 1 mock)."""

    __tablename__ = "ssa_software"

    software_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    authority_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    developer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    software_name: Mapped[str] = mapped_column(String(100), nullable=False)
    program_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SSASoftwareVersion(Base):
    """Software versions with expected tokens (Phase 1 mock)."""

    __tablename__ = "ssa_software_versions"

    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    software_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    version_string: Mapped[str] = mapped_column(String(200), nullable=False)
    expected_token: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # SHA256(program_hash || version_string)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("software_id", "version_string", name="uq_software_version"),
    )
