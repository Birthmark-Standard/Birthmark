# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""Transaction validation logic (replaces smart contracts)."""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.database.models import ImageHash
from src.shared.models.schemas import BatchTransaction
from src.shared.crypto.hashing import verify_hash_format

logger = logging.getLogger(__name__)


class TransactionValidator:
    """
    Validates transactions before including in blocks.

    This replaces what would be smart contract logic in Ethereum.
    Business rules are enforced in native Python code.
    """

    def __init__(self, authorized_aggregators: Optional[set[str]] = None):
        """
        Initialize validator.

        Args:
            authorized_aggregators: Set of authorized aggregator node IDs.
                                   If None, all aggregators are allowed (Phase 1).
        """
        self.authorized_aggregators = authorized_aggregators

    async def validate_transaction(
        self,
        transaction: BatchTransaction,
        db: AsyncSession,
    ) -> tuple[bool, Optional[str]]:
        """
        Validate transaction against all business rules.

        Args:
            transaction: Batch transaction to validate
            db: Database session for duplicate checks

        Returns:
            (is_valid, error_message)
        """
        # Check 1: Authorized aggregator?
        if not self._is_authorized_aggregator(transaction.aggregator_id):
            return False, f"Unauthorized aggregator: {transaction.aggregator_id}"

        # Check 2: Valid hash formats?
        for image_hash in transaction.image_hashes:
            if not verify_hash_format(image_hash):
                return False, f"Invalid hash format: {image_hash}"

        # Check 3: Matching array lengths?
        if len(transaction.image_hashes) != len(transaction.timestamps):
            return False, "Image hashes and timestamps length mismatch"

        if transaction.gps_hashes is not None:
            if len(transaction.gps_hashes) != len(transaction.image_hashes):
                return False, "GPS hashes length mismatch"

        # Check 4: No duplicate hashes in this transaction?
        if len(transaction.image_hashes) != len(set(transaction.image_hashes)):
            return False, "Duplicate hashes within transaction"

        # Check 5: No hashes already on blockchain?
        duplicate_check = await self._check_duplicates(transaction.image_hashes, db)
        if duplicate_check:
            return False, f"Duplicate hash(es) already on blockchain: {duplicate_check}"

        # Check 6: Valid timestamps (not in future, not too old)?
        import time
        current_time = int(time.time())
        for ts in transaction.timestamps:
            if ts > current_time + 300:  # 5 minutes tolerance for clock skew
                return False, f"Timestamp in future: {ts}"
            if ts < current_time - (365 * 24 * 60 * 60):  # Not more than 1 year old
                return False, f"Timestamp too old: {ts}"

        # Check 7: Batch size within limits?
        from src.shared.config import settings
        if len(transaction.image_hashes) < settings.batch_size_min:
            return False, f"Batch too small: {len(transaction.image_hashes)} < {settings.batch_size_min}"
        if len(transaction.image_hashes) > settings.batch_size_max:
            return False, f"Batch too large: {len(transaction.image_hashes)} > {settings.batch_size_max}"

        # All checks passed
        return True, None

    def _is_authorized_aggregator(self, aggregator_id: str) -> bool:
        """Check if aggregator is authorized to submit."""
        if self.authorized_aggregators is None:
            # Phase 1: All aggregators allowed
            return True
        return aggregator_id in self.authorized_aggregators

    async def _check_duplicates(
        self,
        image_hashes: list[str],
        db: AsyncSession,
    ) -> Optional[str]:
        """
        Check if any hashes already exist on blockchain.

        Args:
            image_hashes: List of hashes to check
            db: Database session

        Returns:
            First duplicate hash found, or None if no duplicates
        """
        # Query for any existing hashes
        stmt = select(ImageHash.image_hash).where(
            ImageHash.image_hash.in_(image_hashes)
        )
        result = await db.execute(stmt)
        existing = result.scalars().all()

        if existing:
            return existing[0]  # Return first duplicate
        return None

    async def validate_batch_size(self, batch_size: int) -> tuple[bool, Optional[str]]:
        """
        Validate batch size is within acceptable range.

        Args:
            batch_size: Number of hashes in batch

        Returns:
            (is_valid, error_message)
        """
        from src.shared.config import settings

        if batch_size < settings.batch_size_min:
            return False, f"Batch size {batch_size} below minimum {settings.batch_size_min}"

        if batch_size > settings.batch_size_max:
            return False, f"Batch size {batch_size} above maximum {settings.batch_size_max}"

        return True, None


# Global validator instance (Phase 1: no authorization list)
transaction_validator = TransactionValidator()
