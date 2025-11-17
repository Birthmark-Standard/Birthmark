"""Batching service to create blocks from validated submissions."""

import asyncio
import logging
from typing import List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.database.connection import get_async_db
from src.shared.database.models import PendingSubmission, Transaction
from src.shared.models.schemas import BatchTransaction
from src.shared.config import settings
from src.node.consensus.consensus_engine import get_consensus_engine
from src.node.storage.block_storage import block_storage
from src.shared.crypto.signatures import ValidatorKeys

logger = logging.getLogger(__name__)


class BatchingService:
    """
    Collects validated submissions and creates blockchain batches.

    In Phase 1, this runs periodically as a background task.
    In Phase 2+, this would be a separate worker process.
    """

    def __init__(
        self,
        validator_keys: ValidatorKeys,
        batch_interval_seconds: int = 60,
    ):
        """
        Initialize batching service.

        Args:
            validator_keys: Keys for signing blocks
            batch_interval_seconds: How often to check for pending submissions
        """
        self.validator_keys = validator_keys
        self.batch_interval = batch_interval_seconds
        self.running = False

    async def start(self) -> None:
        """Start background batching loop."""
        self.running = True
        logger.info(f"Starting batching service (interval: {self.batch_interval}s)")

        while self.running:
            try:
                await self._process_pending_submissions()
            except Exception as e:
                logger.error(f"Batching error: {e}", exc_info=True)

            # Wait before next iteration
            await asyncio.sleep(self.batch_interval)

    async def stop(self) -> None:
        """Stop background batching loop."""
        logger.info("Stopping batching service")
        self.running = False

    async def _process_pending_submissions(self) -> None:
        """Collect pending submissions and create batch."""
        async with get_async_db() as db:
            # Get validated but unbatched submissions
            stmt = (
                select(PendingSubmission)
                .where(
                    PendingSubmission.sma_validated == True,  # noqa: E712
                    PendingSubmission.batched == False,  # noqa: E712
                )
                .limit(settings.batch_size_max)
            )
            result = await db.execute(stmt)
            pending = result.scalars().all()

            if not pending:
                logger.debug("No pending submissions to batch")
                return

            logger.info(f"Found {len(pending)} validated submissions to batch")

            # Check if we have enough for a batch
            if len(pending) < settings.batch_size_min:
                logger.debug(
                    f"Waiting for more submissions ({len(pending)} < {settings.batch_size_min})"
                )
                return

            # Create batch transaction
            batch = BatchTransaction(
                image_hashes=[s.image_hash for s in pending],
                timestamps=[s.timestamp for s in pending],
                gps_hashes=[s.gps_hash for s in pending],
                aggregator_id=settings.node_id,
                signature=self._sign_batch([s.image_hash for s in pending]),
            )

            # Get consensus engine
            consensus = get_consensus_engine(
                settings.consensus_mode,
                settings.validator_nodes_list or None,
            )

            # Propose block
            proposal = await consensus.propose_block(
                transactions=[batch],
                validator_id=settings.node_id,
                validator_keys=self.validator_keys,
                db=db,
            )

            if not proposal:
                logger.error("Block proposal failed")
                return

            # Store block
            await block_storage.store_block(
                block_height=proposal.block_height,
                previous_hash=proposal.previous_hash,
                timestamp=proposal.timestamp,
                validator_id=proposal.validator_id,
                transactions=proposal.transactions,
                signature=proposal.signature,
                db=db,
            )

            # Mark submissions as batched
            submission_ids = [s.id for s in pending]
            stmt = (
                update(PendingSubmission)
                .where(PendingSubmission.id.in_(submission_ids))
                .values(batched=True)
            )
            await db.execute(stmt)
            await db.commit()

            logger.info(
                f"Created block {proposal.block_height} with {len(pending)} images"
            )

    def _sign_batch(self, image_hashes: List[str]) -> str:
        """Sign batch of image hashes."""
        batch_data = ",".join(sorted(image_hashes))
        return self.validator_keys.sign(batch_data.encode('utf-8'))
