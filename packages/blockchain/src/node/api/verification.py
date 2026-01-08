# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""Public verification API for querying image hashes."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.database.connection import get_db
from src.shared.models.schemas import VerificationResponse, BlockInfo
from src.node.storage.block_storage import block_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["verification"])


@router.get("/verify/{image_hash}", response_model=VerificationResponse)
async def verify_image(
    image_hash: str = Path(..., min_length=64, max_length=64, description="SHA-256 hash (64 hex chars)"),
    db: AsyncSession = Depends(get_db),
) -> VerificationResponse:
    """
    Verify if an image hash exists on the blockchain.

    This is the primary verification endpoint. Clients can query any SHA-256
    hash to check if it was authenticated by a legitimate camera.

    Args:
        image_hash: SHA-256 hash to verify (64 hex characters)
        db: Database session

    Returns:
        Verification result with timestamp and block info if found
    """
    # Normalize hash to lowercase
    image_hash = image_hash.lower()

    logger.info(f"Verification query for hash: {image_hash[:16]}...")

    # Query blockchain
    result = await block_storage.verify_image_hash(image_hash, db)

    if result:
        logger.info(
            f"Hash VERIFIED: {image_hash[:16]}... found in block {result.block_height}"
        )
        return VerificationResponse(
            verified=True,
            image_hash=result.image_hash,
            timestamp=result.timestamp,
            block_height=result.block_height,
            aggregator=result.aggregator_id,
            tx_hash=None,  # Could add transaction hash lookup
            gps_hash=result.gps_hash,
        )
    else:
        logger.info(f"Hash NOT FOUND: {image_hash[:16]}...")
        return VerificationResponse(
            verified=False,
            image_hash=image_hash,
        )


@router.get("/block/{block_height}", response_model=BlockInfo)
async def get_block(
    block_height: int = Path(..., ge=0, description="Block height"),
    db: AsyncSession = Depends(get_db),
) -> BlockInfo:
    """
    Get block information by height.

    Args:
        block_height: Block number to query
        db: Database session

    Returns:
        Block information

    Raises:
        HTTPException: If block not found
    """
    block = await block_storage.get_block_by_height(block_height, db)

    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block {block_height} not found",
        )

    return BlockInfo(
        block_height=block.block_height,
        block_hash=block.block_hash,
        previous_hash=block.previous_hash,
        timestamp=block.timestamp,
        validator_id=block.validator_id,
        transaction_count=block.transaction_count,
        created_at=block.created_at.isoformat(),
    )


@router.get("/block/latest", response_model=Optional[BlockInfo])
async def get_latest_block(
    db: AsyncSession = Depends(get_db),
) -> Optional[BlockInfo]:
    """
    Get the most recent block.

    Args:
        db: Database session

    Returns:
        Latest block information, or None if no blocks exist
    """
    block = await block_storage.get_latest_block(db)

    if not block:
        return None

    return BlockInfo(
        block_height=block.block_height,
        block_hash=block.block_hash,
        previous_hash=block.previous_hash,
        timestamp=block.timestamp,
        validator_id=block.validator_id,
        transaction_count=block.transaction_count,
        created_at=block.created_at.isoformat(),
    )
