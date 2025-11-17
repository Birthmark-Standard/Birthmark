"""Block and transaction storage engine."""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.database.models import Block, Transaction, ImageHash, NodeState
from src.shared.models.schemas import BatchTransaction, BlockInfo, TransactionInfo
from src.shared.crypto.hashing import compute_block_hash, compute_transaction_hash

logger = logging.getLogger(__name__)


class BlockStorage:
    """Manages blockchain storage in PostgreSQL."""

    async def store_block(
        self,
        block_height: int,
        previous_hash: str,
        timestamp: int,
        validator_id: str,
        transactions: list[BatchTransaction],
        signature: str,
        db: AsyncSession,
    ) -> Block:
        """
        Store new block with transactions and image hashes.

        Args:
            block_height: Block number
            previous_hash: Hash of previous block
            timestamp: Unix timestamp
            validator_id: Node ID that created block
            transactions: List of batch transactions
            signature: Validator signature
            db: Database session

        Returns:
            Created Block object
        """
        # Compute transaction hashes
        tx_hashes = [
            compute_transaction_hash(
                tx.image_hashes,
                tx.timestamps,
                tx.aggregator_id,
            )
            for tx in transactions
        ]

        # Compute block hash
        block_hash = compute_block_hash(
            block_height,
            previous_hash,
            timestamp,
            tx_hashes,
            validator_id,
        )

        # Create block
        block = Block(
            block_height=block_height,
            block_hash=block_hash,
            previous_hash=previous_hash,
            timestamp=timestamp,
            validator_id=validator_id,
            transaction_count=len(transactions),
            signature=signature,
        )
        db.add(block)

        # Create transactions and image hashes
        for tx_data, tx_hash in zip(transactions, tx_hashes):
            # Create transaction
            tx = Transaction(
                tx_hash=tx_hash,
                block_height=block_height,
                aggregator_id=tx_data.aggregator_id,
                batch_size=len(tx_data.image_hashes),
                signature=tx_data.signature,
            )
            db.add(tx)
            await db.flush()  # Get tx_id

            # Create image hash records
            for i, image_hash in enumerate(tx_data.image_hashes):
                gps_hash = None
                if tx_data.gps_hashes and i < len(tx_data.gps_hashes):
                    gps_hash = tx_data.gps_hashes[i]

                img_hash = ImageHash(
                    image_hash=image_hash,
                    tx_id=tx.tx_id,
                    block_height=block_height,
                    timestamp=tx_data.timestamps[i],
                    aggregator_id=tx_data.aggregator_id,
                    gps_hash=gps_hash,
                )
                db.add(img_hash)

        await db.commit()
        logger.info(
            f"Stored block {block_height} with {len(transactions)} transactions "
            f"and {sum(len(tx.image_hashes) for tx in transactions)} image hashes"
        )

        # Update node state
        await self.update_node_state(db, block_height, block_hash)

        return block

    async def get_latest_block(self, db: AsyncSession) -> Optional[Block]:
        """Get most recent block."""
        stmt = select(Block).order_by(Block.block_height.desc()).limit(1)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_block_by_height(
        self,
        height: int,
        db: AsyncSession,
    ) -> Optional[Block]:
        """Get block by height."""
        stmt = select(Block).where(Block.block_height == height)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_block_by_hash(
        self,
        block_hash: str,
        db: AsyncSession,
    ) -> Optional[Block]:
        """Get block by hash."""
        stmt = select(Block).where(Block.block_hash == block_hash)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def verify_image_hash(
        self,
        image_hash: str,
        db: AsyncSession,
    ) -> Optional[ImageHash]:
        """
        Verify if image hash exists on blockchain.

        Args:
            image_hash: SHA-256 hash to verify
            db: Database session

        Returns:
            ImageHash record if found, None otherwise
        """
        stmt = select(ImageHash).where(ImageHash.image_hash == image_hash)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_total_hash_count(self, db: AsyncSession) -> int:
        """Get total number of image hashes on blockchain."""
        stmt = select(func.count(ImageHash.image_hash))
        result = await db.execute(stmt)
        return result.scalar_one()

    async def update_node_state(
        self,
        db: AsyncSession,
        block_height: int,
        block_hash: str,
    ) -> None:
        """Update node state after new block."""
        from src.shared.config import settings

        stmt = select(NodeState).where(NodeState.id == 1)
        result = await db.execute(stmt)
        state = result.scalar_one_or_none()

        if not state:
            state = NodeState(
                id=1,
                node_id=settings.node_id,
                current_block_height=block_height,
                total_hashes=0,
            )
            db.add(state)

        state.current_block_height = block_height
        state.last_block_time = datetime.utcnow()

        # Update total hashes count
        total = await self.get_total_hash_count(db)
        state.total_hashes = total

        await db.commit()

    async def get_node_state(self, db: AsyncSession) -> Optional[NodeState]:
        """Get current node state."""
        stmt = select(NodeState).where(NodeState.id == 1)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


# Global storage instance
block_storage = BlockStorage()
