#!/usr/bin/env python3
"""Initialize genesis block for Birthmark blockchain."""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.shared.config import settings
from src.shared.database.connection import get_async_db
from src.shared.database.models import Block, NodeState
from src.shared.crypto.hashing import sha256_hex
from src.shared.crypto.signatures import ValidatorKeys
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_genesis_block():
    """Create the genesis block (block 0)."""
    logger.info("Initializing genesis block...")

    async with get_async_db() as db:
        # Check if genesis block already exists
        stmt = select(Block).where(Block.block_height == 0)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            logger.warning(f"Genesis block already exists: {existing.block_hash}")
            return

        # Load or generate validator keys
        key_path = Path(settings.validator_key_path)
        if key_path.exists():
            logger.info(f"Loading validator keys from {key_path}")
            validator_keys = ValidatorKeys.load_from_file(key_path)
        else:
            logger.info("Generating new validator keys")
            validator_keys = ValidatorKeys.generate()
            validator_keys.save_to_file(key_path)
            logger.info(f"Saved validator keys to {key_path}")

        # Create genesis block
        genesis_timestamp = int(time.time())
        if settings.genesis_timestamp:
            genesis_timestamp = settings.genesis_timestamp

        validator_id = settings.genesis_validator or settings.node_id

        # Genesis block has no previous hash
        previous_hash = "0" * 64

        # Compute genesis hash (no transactions)
        genesis_data = f"BIRTHMARK_GENESIS_{genesis_timestamp}_{validator_id}"
        genesis_hash = sha256_hex(genesis_data.encode('utf-8'))

        # Sign genesis block
        signature_data = f"0{previous_hash}{genesis_timestamp}{validator_id}"
        signature = validator_keys.sign(signature_data.encode('utf-8'))

        # Create genesis block
        genesis = Block(
            block_height=0,
            block_hash=genesis_hash,
            previous_hash=previous_hash,
            timestamp=genesis_timestamp,
            validator_id=validator_id,
            transaction_count=0,
            signature=signature,
        )

        db.add(genesis)

        # Initialize node state
        state = NodeState(
            id=1,
            node_id=settings.node_id,
            current_block_height=0,
            total_hashes=0,
            genesis_hash=genesis_hash,
        )
        db.add(state)

        await db.commit()

        logger.info(f"Genesis block created!")
        logger.info(f"  Block height: 0")
        logger.info(f"  Block hash: {genesis_hash}")
        logger.info(f"  Timestamp: {genesis_timestamp}")
        logger.info(f"  Validator: {validator_id}")


async def main():
    """Main entry point."""
    try:
        await create_genesis_block()
        logger.info("Genesis initialization complete!")
    except Exception as e:
        logger.error(f"Genesis initialization failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
