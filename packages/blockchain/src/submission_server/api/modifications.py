# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Modification tracking API endpoints for Birthmark blockchain submission server.

Handles modification records from editing software (GIMP plugin, etc.)
and provides provenance chain verification.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import httpx
import logging
from datetime import datetime

from ...shared.models.schemas import (
    ModificationRecord,
    ModificationResponse,
    ProvenanceChain,
    ProvenanceItem,
)
from ...shared.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["modifications"])


@router.post("/modifications", response_model=ModificationResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_modification_record(
    record: ModificationRecord,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit modification record from editing software.

    The submission server:
    1. Validates the software certificate with SSA (TODO in Phase 3)
    2. Stores the modification record
    3. Links it to the original image hash
    4. Returns confirmation

    Args:
        record: Modification record from editing software
        db: Database session

    Returns:
        ModificationResponse with status and chain ID
    """
    try:
        logger.info(f"Received modification record for final hash: {record.final_image_hash[:16]}...")

        # TODO Phase 3: Validate software certificate with SSA
        # For now, accept all modification records

        # Check if original image was authenticated
        original_exists = await db.execute(
            select(ConfirmedHash).where(
                ConfirmedHash.image_hash == record.original_image_hash
            )
        )
        original_confirmed = original_exists.scalars().first()

        if not original_confirmed and record.authenticated:
            logger.warning(
                f"Original image {record.original_image_hash[:16]} claimed as authenticated but not found"
            )

        # Store modification record
        mod_record = ModificationRecordDB(
            original_image_hash=record.original_image_hash,
            final_image_hash=record.final_image_hash,
            modification_level=record.modification_level,
            authenticated=record.authenticated,
            original_width=record.original_dimensions[0] if record.original_dimensions else None,
            original_height=record.original_dimensions[1] if record.original_dimensions else None,
            final_width=record.final_dimensions[0] if record.final_dimensions else None,
            final_height=record.final_dimensions[1] if record.final_dimensions else None,
            software_id=record.software_id,
            plugin_version=record.plugin_version,
            initialized_at=datetime.fromisoformat(record.initialized_at),
            exported_at=datetime.fromisoformat(record.exported_at),
            authority_type=record.authority_type,
        )

        db.add(mod_record)
        await db.commit()
        await db.refresh(mod_record)

        logger.info(
            f"Stored modification record: {record.software_id} "
            f"level={record.modification_level} final_hash={record.final_image_hash[:16]}..."
        )

        # Generate verification URL
        verification_url = f"/api/v1/provenance/{record.final_image_hash}"

        return ModificationResponse(
            status="recorded",
            final_image_hash=record.final_image_hash,
            modification_level=record.modification_level,
            chain_id=f"mod_{mod_record.id}",
            verification_url=verification_url,
            message="Modification record accepted and stored"
        )

    except Exception as e:
        logger.error(f"Error storing modification record: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store modification record: {str(e)}"
        )


@router.get("/provenance/{image_hash}", response_model=ProvenanceChain)
async def get_provenance_chain(
    image_hash: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete provenance chain for an image.

    Traces back through modification records to find the original
    authenticated capture.

    Args:
        image_hash: SHA-256 hash of the image to query
        db: Database session

    Returns:
        ProvenanceChain with complete history
    """
    try:
        logger.info(f"Querying provenance chain for: {image_hash[:16]}...")

        chain = []
        current_hash = image_hash
        verified = False

        # Trace backwards through modification records
        max_depth = 10  # Prevent infinite loops
        depth = 0

        while depth < max_depth:
            # Check if this hash is a modified image
            mod_result = await db.execute(
                select(ModificationRecordDB).where(
                    ModificationRecordDB.final_image_hash == current_hash
                )
            )
            mod_record = mod_result.scalars().first()

            if mod_record:
                # Add modification to chain
                chain.insert(0, ProvenanceItem(
                    hash=mod_record.final_image_hash,
                    type="modification",
                    timestamp=mod_record.exported_at.isoformat(),
                    authority_type=mod_record.authority_type,
                    authority_id=mod_record.software_id,
                    modification_level=mod_record.modification_level,
                    software_version=mod_record.plugin_version,
                ))

                # Continue tracing to original
                current_hash = mod_record.original_image_hash
                depth += 1
            else:
                # No more modifications, check if this is an authenticated capture
                capture_result = await db.execute(
                    select(ConfirmedHash).where(
                        ConfirmedHash.image_hash == current_hash
                    )
                )
                capture = capture_result.scalars().first()

                if capture:
                    # Found authenticated capture
                    chain.insert(0, ProvenanceItem(
                        hash=capture.image_hash,
                        type="capture",
                        timestamp=datetime.fromtimestamp(capture.timestamp).isoformat(),
                        authority_type="manufacturer",
                        authority_id=capture.submission_server or "unknown",
                        modification_level=0,
                    ))
                    verified = True

                break  # End of chain

        if not chain:
            # No provenance found
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No provenance chain found for this image"
            )

        return ProvenanceChain(
            image_hash=image_hash,
            verified=verified,
            chain=chain,
            chain_length=len(chain)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying provenance chain: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query provenance chain: {str(e)}"
        )


@router.get("/modifications/{image_hash}")
async def get_modification_history(
    image_hash: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all modification records for an image (either as original or final).

    Args:
        image_hash: SHA-256 hash to query
        db: Database session

    Returns:
        List of modification records
    """
    try:
        # Query as original hash
        original_query = await db.execute(
            select(ModificationRecordDB).where(
                ModificationRecordDB.original_image_hash == image_hash
            )
        )
        as_original = original_query.scalars().all()

        # Query as final hash
        final_query = await db.execute(
            select(ModificationRecordDB).where(
                ModificationRecordDB.final_image_hash == image_hash
            )
        )
        as_final = final_query.scalars().all()

        return {
            "image_hash": image_hash,
            "as_original": [
                {
                    "final_hash": r.final_image_hash,
                    "modification_level": r.modification_level,
                    "software_id": r.software_id,
                    "exported_at": r.exported_at.isoformat(),
                }
                for r in as_original
            ],
            "as_final": [
                {
                    "original_hash": r.original_image_hash,
                    "modification_level": r.modification_level,
                    "software_id": r.software_id,
                    "exported_at": r.exported_at.isoformat(),
                }
                for r in as_final
            ]
        }

    except Exception as e:
        logger.error(f"Error querying modification history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query modification history: {str(e)}"
        )
