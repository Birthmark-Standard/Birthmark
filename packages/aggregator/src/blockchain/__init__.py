"""Blockchain posting module for Merkle roots."""

import logging
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models import Batch

logger = logging.getLogger(__name__)


async def mock_blockchain_post(
    batch_id: UUID, merkle_root: str, image_count: int, db: AsyncSession
) -> str:
    """
    Simulate posting Merkle root to blockchain (Phase 1).

    Generates fake transaction hash and updates batch record.

    Args:
        batch_id: UUID of the batch
        merkle_root: Merkle root hash to "post"
        image_count: Number of images in batch
        db: Database session

    Returns:
        Mock transaction hash
    """
    # Generate fake zkSync transaction hash
    # Format: 0xMOCK_ + first 60 chars of merkle_root
    mock_tx_hash = f"0xMOCK_{merkle_root[:60]}"

    # Generate fake block number (incrementing counter)
    stmt = select(Batch.zksync_block_number).where(Batch.zksync_block_number.isnot(None)).order_by(Batch.zksync_block_number.desc()).limit(1)
    result = await db.execute(stmt)
    last_block = result.scalar_one_or_none()
    mock_block_number = (last_block or 1000000) + 1

    # Update batch with mock blockchain info
    stmt = (
        update(Batch)
        .where(Batch.batch_id == batch_id)
        .values(
            status="posted",
            zksync_tx_hash=mock_tx_hash,
            zksync_block_number=mock_block_number,
            confirmed_at=datetime.now(timezone.utc),
        )
    )
    await db.execute(stmt)
    await db.commit()

    logger.info(
        f"Mock blockchain post: batch {batch_id} ({image_count} images) "
        f"-> tx {mock_tx_hash} at block {mock_block_number}"
    )

    return mock_tx_hash


async def post_batch_to_blockchain(
    batch_id: UUID, merkle_root: str, image_count: int, db: AsyncSession
) -> str:
    """
    Post Merkle root to real zkSync blockchain (Phase 2+).

    This is a placeholder for Phase 2 implementation.
    Currently just calls mock_blockchain_post.

    Args:
        batch_id: UUID of the batch
        merkle_root: Merkle root hash to post
        image_count: Number of images in batch
        db: Database session

    Returns:
        Transaction hash

    TODO Phase 2:
        - Import web3 library
        - Load zkSync RPC endpoint from settings
        - Build transaction to BirthmarkRegistry.postBatch()
        - Sign with private key
        - Send transaction
        - Wait for confirmation
        - Update batch record with real tx hash
    """
    logger.warning("Real blockchain posting not implemented yet. Using mock.")
    return await mock_blockchain_post(batch_id, merkle_root, image_count, db)
