"""SQLAlchemy ORM models for Birthmark Blockchain."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CHAR,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    ARRAY,
)
from sqlalchemy.orm import relationship

from src.shared.database.connection import Base


class Block(Base):
    """
    Blockchain block containing validated image hash transactions.

    Blocks are proposed by validator nodes and contain batches of transactions
    from submission servers.
    """

    __tablename__ = "blocks"

    block_height = Column(BigInteger, primary_key=True, autoincrement=False)
    block_hash = Column(CHAR(64), nullable=False, unique=True, index=True)
    previous_hash = Column(CHAR(64), nullable=False)
    timestamp = Column(BigInteger, nullable=False)  # Unix timestamp
    validator_id = Column(String(255), nullable=False)
    transaction_count = Column(Integer, nullable=False)
    signature = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    transactions = relationship("Transaction", back_populates="block", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_blocks_height", "block_height"),)


class Transaction(Base):
    """
    Transaction containing image hash submission from a submission server.

    Each transaction contains a batch of validated image hashes. The submission_server_id
    is stored here (not duplicated in image_hashes) for investigation queries.
    """

    __tablename__ = "transactions"

    tx_id = Column(Integer, primary_key=True, autoincrement=True)
    tx_hash = Column(CHAR(64), nullable=False, unique=True, index=True)
    block_height = Column(BigInteger, ForeignKey("blocks.block_height"), nullable=False, index=True)
    submission_server_id = Column(String(255), nullable=False)
    batch_size = Column(Integer, nullable=False)  # Number of hashes in this transaction
    signature = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    block = relationship("Block", back_populates="transactions")
    image_hashes = relationship("ImageHash", back_populates="transaction", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_tx_block", "block_height"),)


class ImageHash(Base):
    """
    Individual image hash with metadata for fast verification queries.

    This is the primary table for verification lookups. Optimized for:
    - Single hash verification (primary key on image_hash)
    - Provenance chain tracking (parent_image_hash, modification_level)

    Note: submission_server_id is NOT stored here (only in Transaction) to avoid
    duplication. Investigation queries can join to Transaction if needed.
    """

    __tablename__ = "image_hashes"

    image_hash = Column(CHAR(64), primary_key=True)
    tx_id = Column(Integer, ForeignKey("transactions.tx_id"), nullable=False, index=True)
    block_height = Column(BigInteger, ForeignKey("blocks.block_height"), nullable=False, index=True)
    timestamp = Column(BigInteger, nullable=False)  # Unix timestamp (server processing time)

    # Provenance chain
    parent_image_hash = Column(CHAR(64), nullable=True, index=True)  # For tracking raw->processed
    modification_level = Column(Integer, nullable=False, default=0)  # 0=raw, 1=processed, 2+=modified

    # Optional GPS location proof
    gps_hash = Column(CHAR(64), nullable=True)  # SHA-256 of GPS coordinates (if provided)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    transaction = relationship("Transaction", back_populates="image_hashes")

    __table_args__ = (
        Index("idx_hashes_block", "block_height"),
        Index("idx_hashes_timestamp", "timestamp"),
        Index("idx_hashes_parent", "parent_image_hash"),
        Index("idx_hashes_modification_level", "modification_level"),
    )


class PendingSubmission(Base):
    """
    Camera submissions awaiting SMA validation and blockchain submission.

    Phase 1: Camera submissions only (no software modifications)
    Submissions are grouped by transaction_id (raw + processed from same capture).
    """

    __tablename__ = "pending_submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_hash = Column(CHAR(64), nullable=False, index=True)

    # Camera submission data
    modification_level = Column(Integer, nullable=False, default=0, index=True)  # 0=raw, 1=processed
    parent_image_hash = Column(CHAR(64), nullable=True, index=True)  # For provenance chain (processed→raw)
    transaction_id = Column(String(36), nullable=False, index=True)  # Groups raw+processed from same capture
    manufacturer_authority_id = Column(String(100), nullable=False)  # e.g., "SIMULATED_CAMERA_001"
    camera_token_json = Column(Text, nullable=False)  # JSON-encoded CameraToken object

    # Timestamps and location
    timestamp = Column(BigInteger, nullable=False)  # Unix timestamp (camera capture time)
    gps_hash = Column(CHAR(64), nullable=True)  # SHA-256 of GPS coordinates (optional)

    # Validation tracking
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sma_validated = Column(Boolean, default=False, nullable=False, index=True)
    validation_attempted_at = Column(DateTime, nullable=True)
    validation_result = Column(String(50), nullable=True)  # PASS, FAIL, ERROR

    # Blockchain submission tracking (for crash recovery)
    tx_id = Column(Integer, ForeignKey("transactions.tx_id"), nullable=True)

    __table_args__ = (
        Index("idx_pending_validated", "sma_validated"),
        Index("idx_pending_transaction_id", "transaction_id"),
        Index("idx_pending_modification_level", "modification_level"),
        Index("idx_pending_parent_hash", "parent_image_hash"),
    )


class NodeState(Base):
    """Singleton table tracking node state and configuration."""

    __tablename__ = "node_state"

    id = Column(Integer, primary_key=True, default=1)  # Always ID=1
    node_id = Column(String(255), nullable=False)
    current_block_height = Column(BigInteger, default=0, nullable=False)
    total_hashes = Column(BigInteger, default=0, nullable=False)
    genesis_hash = Column(CHAR(64), nullable=True)
    last_block_time = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @classmethod
    def get_or_create(cls, session, node_id: str) -> "NodeState":
        """Get existing state or create new one."""
        state = session.query(cls).filter_by(id=1).first()
        if not state:
            state = cls(id=1, node_id=node_id)
            session.add(state)
            session.commit()
        return state


class ModificationRecordDB(Base):
    """
    Modification records from editing software (Phase 3+).

    NOT USED IN PHASE 1 - Created for future use.

    Tracks the editing provenance chain from authenticated captures
    through software modifications (Photoshop, Lightroom, etc.).
    """

    __tablename__ = "modification_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    original_image_hash = Column(CHAR(64), nullable=False, index=True)
    final_image_hash = Column(CHAR(64), nullable=False, unique=True, index=True)
    modification_level = Column(Integer, nullable=False)  # 0=unmodified, 1=minor, 2=heavy
    authenticated = Column(Boolean, nullable=False)  # Was original authenticated?

    # Dimensions
    original_width = Column(Integer, nullable=True)
    original_height = Column(Integer, nullable=True)
    final_width = Column(Integer, nullable=True)
    final_height = Column(Integer, nullable=True)

    # Software info
    software_id = Column(String(255), nullable=False, index=True)
    plugin_version = Column(String(50), nullable=False)
    authority_type = Column(String(50), default="software", nullable=False)

    # Timestamps
    initialized_at = Column(DateTime, nullable=False)  # When tracking started
    exported_at = Column(DateTime, nullable=False)  # When record exported
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # When stored in DB

    # Phase 3+: Link to blockchain transaction when final hash is submitted
    tx_id = Column(Integer, ForeignKey("transactions.tx_id"), nullable=True)

    __table_args__ = (
        Index("idx_mod_original", "original_image_hash"),
        Index("idx_mod_final", "final_image_hash"),
        Index("idx_mod_software", "software_id"),
        Index("idx_mod_level", "modification_level"),
    )
