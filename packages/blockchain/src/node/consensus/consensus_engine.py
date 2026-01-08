# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""Pluggable consensus engine for block proposal and validation."""

import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.models.schemas import BatchTransaction, BlockProposal
from src.shared.crypto.signatures import ValidatorKeys
from src.shared.crypto.hashing import compute_block_hash
from src.node.storage.block_storage import block_storage
from src.node.consensus.transaction_validator import transaction_validator

logger = logging.getLogger(__name__)


class ConsensusEngine(ABC):
    """
    Abstract base class for consensus engines.

    This design allows switching from single-node to multi-node
    consensus without changing the calling code.
    """

    @abstractmethod
    async def propose_block(
        self,
        transactions: list[BatchTransaction],
        validator_id: str,
        validator_keys: ValidatorKeys,
        db: AsyncSession,
    ) -> Optional[BlockProposal]:
        """
        Propose a new block with transactions.

        Args:
            transactions: List of validated transactions
            validator_id: This node's ID
            validator_keys: Signing keys
            db: Database session

        Returns:
            Approved block proposal, or None if rejected
        """
        pass

    @abstractmethod
    async def broadcast_block(self, block: BlockProposal) -> None:
        """Broadcast block to peer nodes (no-op for Phase 1)."""
        pass

    @abstractmethod
    async def sync_with_peers(self, db: AsyncSession) -> None:
        """Sync blockchain state with peers (no-op for Phase 1)."""
        pass


class SingleNodeConsensus(ConsensusEngine):
    """
    Phase 1 consensus: Single node, auto-accept all valid transactions.

    No voting, no peers, instant finality.
    """

    async def propose_block(
        self,
        transactions: list[BatchTransaction],
        validator_id: str,
        validator_keys: ValidatorKeys,
        db: AsyncSession,
    ) -> Optional[BlockProposal]:
        """
        Create block from transactions (instant approval).

        Args:
            transactions: Validated transactions
            validator_id: This node's ID
            validator_keys: Signing keys
            db: Database session

        Returns:
            Block proposal (always succeeds if transactions valid)
        """
        if not transactions:
            logger.warning("No transactions to propose")
            return None

        # Get latest block
        latest_block = await block_storage.get_latest_block(db)
        if latest_block:
            block_height = latest_block.block_height + 1
            previous_hash = latest_block.block_hash
        else:
            # Genesis block
            block_height = 0
            previous_hash = "0" * 64

        # Create proposal
        timestamp = int(time.time())

        # Compute transaction hashes for block hash
        from src.shared.crypto.hashing import compute_transaction_hash
        tx_hashes = [
            compute_transaction_hash(
                tx.image_hashes,
                tx.timestamps,
                tx.aggregator_id,
            )
            for tx in transactions
        ]

        # Sign block
        block_data = f"{block_height}{previous_hash}{timestamp}{','.join(tx_hashes)}{validator_id}"
        signature = validator_keys.sign(block_data.encode('utf-8'))

        proposal = BlockProposal(
            block_height=block_height,
            previous_hash=previous_hash,
            timestamp=timestamp,
            transactions=transactions,
            validator_id=validator_id,
            signature=signature,
        )

        logger.info(
            f"Proposed block {block_height} with {len(transactions)} transactions "
            f"({sum(len(tx.image_hashes) for tx in transactions)} hashes)"
        )

        return proposal

    async def broadcast_block(self, block: BlockProposal) -> None:
        """No-op for single node."""
        pass

    async def sync_with_peers(self, db: AsyncSession) -> None:
        """No-op for single node."""
        pass


class ProofOfAuthorityConsensus(ConsensusEngine):
    """
    Phase 2+ consensus: Multi-node PoA with 2/3 majority voting.

    Features:
    - Gossip protocol for block propagation
    - Validator voting (2/3 quorum required)
    - State synchronization
    - Byzantine fault tolerance
    """

    def __init__(self, validator_nodes: list[str]):
        """
        Initialize PoA consensus.

        Args:
            validator_nodes: List of authorized validator node IDs
        """
        self.validator_nodes = set(validator_nodes)
        self.quorum = (2 * len(validator_nodes) // 3) + 1

    async def propose_block(
        self,
        transactions: list[BatchTransaction],
        validator_id: str,
        validator_keys: ValidatorKeys,
        db: AsyncSession,
    ) -> Optional[BlockProposal]:
        """
        Propose block and collect votes from validators.

        Args:
            transactions: Validated transactions
            validator_id: This node's ID
            validator_keys: Signing keys
            db: Database session

        Returns:
            Block proposal if quorum reached, None otherwise
        """
        # TODO: Phase 2 implementation
        # 1. Create proposal (similar to single node)
        # 2. Broadcast to peer validators
        # 3. Collect votes
        # 4. Return proposal if quorum reached
        raise NotImplementedError("PoA consensus is Phase 2+")

    async def broadcast_block(self, block: BlockProposal) -> None:
        """Broadcast block to all peer validators."""
        # TODO: Phase 2 implementation
        # - Use gossip protocol
        # - Send to all peers in validator_nodes
        raise NotImplementedError("PoA consensus is Phase 2+")

    async def sync_with_peers(self, db: AsyncSession) -> None:
        """Synchronize blockchain state with peers."""
        # TODO: Phase 2 implementation
        # - Query peers for latest block height
        # - Fetch missing blocks
        # - Validate and store
        raise NotImplementedError("PoA consensus is Phase 2+")


def get_consensus_engine(mode: str, validator_nodes: Optional[list[str]] = None) -> ConsensusEngine:
    """
    Factory function to get consensus engine based on configuration.

    Args:
        mode: 'single' or 'poa'
        validator_nodes: List of validator IDs (for PoA)

    Returns:
        Consensus engine instance
    """
    if mode == "single":
        return SingleNodeConsensus()
    elif mode == "poa":
        if not validator_nodes:
            raise ValueError("PoA mode requires validator_nodes list")
        return ProofOfAuthorityConsensus(validator_nodes)
    else:
        raise ValueError(f"Unknown consensus mode: {mode}")
