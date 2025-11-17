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
    """Blockchain block containing validated image hash transactions."""

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
    """Transaction containing batch of image hashes from an aggregator."""

    __tablename__ = "transactions"

    tx_id = Column(Integer, primary_key=True, autoincrement=True)
    tx_hash = Column(CHAR(64), nullable=False, unique=True, index=True)
    block_height = Column(BigInteger, ForeignKey("blocks.block_height"), nullable=False, index=True)
    aggregator_id = Column(String(255), nullable=False)
    batch_size = Column(Integer, nullable=False)
    signature = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    block = relationship("Block", back_populates="transactions")
    image_hashes = relationship("ImageHash", back_populates="transaction", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_tx_block", "block_height"),)


class ImageHash(Base):
    """Individual image hash with metadata for fast verification queries."""

    __tablename__ = "image_hashes"

    image_hash = Column(CHAR(64), primary_key=True)
    tx_id = Column(Integer, ForeignKey("transactions.tx_id"), nullable=False, index=True)
    block_height = Column(BigInteger, ForeignKey("blocks.block_height"), nullable=False, index=True)
    timestamp = Column(BigInteger, nullable=False)  # Unix timestamp
    aggregator_id = Column(String(255), nullable=False)
    gps_hash = Column(CHAR(64), nullable=True)  # Optional GPS location hash
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    transaction = relationship("Transaction", back_populates="image_hashes")

    __table_args__ = (
        Index("idx_hashes_block", "block_height"),
        Index("idx_hashes_timestamp", "timestamp"),
        Index("idx_hashes_aggregator", "aggregator_id"),
    )


class PendingSubmission(Base):
    """Camera submissions awaiting SMA validation and batching."""

    __tablename__ = "pending_submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_hash = Column(CHAR(64), nullable=False, index=True)
    encrypted_token = Column(LargeBinary, nullable=False)
    table_references = Column(ARRAY(Integer), nullable=False)
    key_indices = Column(ARRAY(Integer), nullable=False)
    timestamp = Column(BigInteger, nullable=False)  # Unix timestamp
    gps_hash = Column(CHAR(64), nullable=True)
    device_signature = Column(LargeBinary, nullable=False)

    # Validation tracking
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sma_validated = Column(Boolean, default=False, nullable=False, index=True)
    validation_attempted_at = Column(DateTime, nullable=True)
    validation_result = Column(String(50), nullable=True)  # PASS, FAIL, ERROR

    # Batching tracking
    batched = Column(Boolean, default=False, nullable=False, index=True)
    batched_at = Column(DateTime, nullable=True)
    tx_id = Column(Integer, ForeignKey("transactions.tx_id"), nullable=True)

    __table_args__ = (
        Index("idx_pending_validated", "sma_validated"),
        Index("idx_pending_batched", "batched"),
        Index("idx_pending_status", "sma_validated", "batched"),
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
