# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Minimal Phase 1 Blockchain Node

Single-node blockchain for Phase 1 testing.
Stores hashes directly, no consensus needed, no syncing.

This is a simplified implementation for Phase 1 and will not carry over to Phase 2.
"""

import hashlib
import logging
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.shared.database.models import Block, Transaction, ImageHash, NodeState
from src.shared.database.connection import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/blockchain", tags=["blockchain"])


class HashSubmission(BaseModel):
    """Single hash submission from submission server."""
    image_hash: str = Field(..., min_length=64, max_length=64)
    timestamp: int
    submission_server_id: str  # Renamed from aggregator_id
    modification_level: int = 0  # 0=raw, 1=processed
    parent_image_hash: Optional[str] = None  # For provenance chain
    manufacturer_authority_id: Optional[str] = None
    gps_hash: Optional[str] = None  # Optional GPS location proof


class HashSubmissionResponse(BaseModel):
    """Response from hash submission."""
    tx_id: int
    block_height: int
    message: str


class HashVerification(BaseModel):
    """Hash verification response."""
    verified: bool
    timestamp: Optional[int] = None
    block_height: Optional[int] = None
    tx_id: Optional[int] = None
    submission_server_id: Optional[str] = None  # Renamed from aggregator_id
    modification_level: Optional[int] = None
    parent_image_hash: Optional[str] = None


@router.post("/submit", response_model=HashSubmissionResponse)
async def submit_hash(
    submission: HashSubmission,
    db: AsyncSession = Depends(get_db)
) -> HashSubmissionResponse:
    """
    Submit validated hash to blockchain.

    Phase 1: Direct storage, no batching, single node.
    Each hash gets its own transaction in the current block.
    """
    logger.info(f"📥 Blockchain: Receiving hash {submission.image_hash[:16]}...")
    logger.info(f"   Timestamp: {submission.timestamp}, Level: {submission.modification_level}, "
                f"Parent: {submission.parent_image_hash[:16] + '...' if submission.parent_image_hash else 'None'}")

    # Get or create current block
    current_block = await get_or_create_current_block(db)

    # Create transaction for this hash
    transaction = Transaction(
        tx_hash=hashlib.sha256(
            f"{submission.image_hash}{submission.timestamp}".encode()
        ).hexdigest(),
        block_height=current_block.block_height,
        submission_server_id=submission.submission_server_id,  # Normalized: only in Transaction
        batch_size=1,  # Always 1 for Phase 1 (no batching)
        signature="phase1_mock_signature",  # Phase 1 simplified
        created_at=datetime.utcnow()
    )
    db.add(transaction)
    await db.flush()  # Get tx_id

    # Store hash with provenance chain
    image_hash_record = ImageHash(
        image_hash=submission.image_hash,
        tx_id=transaction.tx_id,
        block_height=current_block.block_height,
        timestamp=submission.timestamp,
        parent_image_hash=submission.parent_image_hash,  # Provenance tracking
        modification_level=submission.modification_level,  # 0=raw, 1=processed
        gps_hash=submission.gps_hash,  # Optional GPS location proof
        created_at=datetime.utcnow()
    )
    db.add(image_hash_record)

    # Update block transaction count
    current_block.transaction_count += 1

    await db.commit()

    logger.info(
        f"✅ Hash stored: tx_id={transaction.tx_id}, block={current_block.block_height}, "
        f"hash={submission.image_hash[:16]}..."
    )

    return HashSubmissionResponse(
        tx_id=transaction.tx_id,
        block_height=current_block.block_height,
        message="Hash submitted to blockchain"
    )


@router.get("/verify/{image_hash}", response_model=HashVerification)
async def verify_hash(
    image_hash: str,
    db: AsyncSession = Depends(get_db)
) -> HashVerification:
    """
    Verify if hash exists on blockchain.

    Returns verification status with block height, timestamp, and provenance chain.
    """
    # Query for hash with joined transaction to get submission_server_id
    stmt = select(ImageHash, Transaction.submission_server_id).join(
        Transaction, ImageHash.tx_id == Transaction.tx_id
    ).where(ImageHash.image_hash == image_hash)
    result = await db.execute(stmt)
    row = result.one_or_none()

    if row:
        hash_record, submission_server_id = row
        logger.info(f"🔍 Verification: Hash {image_hash[:16]}... found (verified)")
        return HashVerification(
            verified=True,
            timestamp=hash_record.timestamp,
            block_height=hash_record.block_height,
            tx_id=hash_record.tx_id,
            submission_server_id=submission_server_id,
            modification_level=hash_record.modification_level,
            parent_image_hash=hash_record.parent_image_hash
        )
    else:
        logger.info(f"🔍 Verification: Hash {image_hash[:16]}... not found")
        return HashVerification(verified=False)


@router.get("/status")
async def blockchain_status(db: AsyncSession = Depends(get_db)) -> dict:
    """Get blockchain node status."""
    # Get node state
    node_state = await get_node_state(db)

    # Get total hashes
    stmt = select(func.count(ImageHash.image_hash))
    result = await db.execute(stmt)
    total_hashes = result.scalar_one()

    return {
        "node_id": node_state.node_id,
        "block_height": node_state.current_block_height,
        "total_hashes": total_hashes,
        "last_block_time": node_state.last_block_time.isoformat() if node_state.last_block_time else None,
        "status": "operational"
    }


async def get_or_create_current_block(db: AsyncSession) -> Block:
    """
    Get current block or create new one.

    Phase 1: Simple strategy - new block every 100 transactions or 5 minutes.
    """
    node_state = await get_node_state(db)

    # Check if current block exists
    if node_state.current_block_height > 0:
        stmt = select(Block).where(Block.block_height == node_state.current_block_height)
        result = await db.execute(stmt)
        current_block = result.scalar_one_or_none()

        if current_block:
            # Check if we need a new block (100 transactions or 5 min old)
            age_seconds = (datetime.utcnow() - current_block.created_at).total_seconds()
            if current_block.transaction_count >= 100 or age_seconds >= 300:
                return await create_new_block(db, node_state)
            return current_block

    # No current block, create genesis or next
    return await create_new_block(db, node_state)


async def create_new_block(db: AsyncSession, node_state: NodeState) -> Block:
    """Create new block."""
    new_height = node_state.current_block_height + 1

    # Get previous block hash
    if new_height == 1:
        # Genesis block
        previous_hash = "0" * 64
    else:
        stmt = select(Block.block_hash).where(
            Block.block_height == node_state.current_block_height
        )
        result = await db.execute(stmt)
        previous_hash = result.scalar_one()

    # Create block hash
    block_hash = hashlib.sha256(
        f"{new_height}{previous_hash}{int(time.time())}".encode()
    ).hexdigest()

    # Create block
    block = Block(
        block_height=new_height,
        block_hash=block_hash,
        previous_hash=previous_hash,
        timestamp=int(time.time()),
        validator_id="phase1_single_node",
        transaction_count=0,
        signature="phase1_mock_signature",
        created_at=datetime.utcnow()
    )
    db.add(block)

    # Update node state
    node_state.current_block_height = new_height
    node_state.last_block_time = datetime.utcnow()

    await db.commit()

    logger.info(f"✓ Created block {new_height}: {block_hash[:16]}...")

    return block


async def get_node_state(db: AsyncSession) -> NodeState:
    """Get or create node state."""
    stmt = select(NodeState).where(NodeState.id == 1)
    result = await db.execute(stmt)
    state = result.scalar_one_or_none()

    if not state:
        # Initialize node state
        state = NodeState(
            id=1,
            node_id="phase1_blockchain_node",
            current_block_height=0,
            total_hashes=0,
            genesis_hash=None,
            last_block_time=None,
            updated_at=datetime.utcnow()
        )
        db.add(state)
        await db.commit()

    return state
