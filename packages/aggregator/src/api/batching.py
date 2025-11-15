"""Batching API endpoints for manual batch creation (Phase 1)."""

import logging
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.database import get_db
from src.models import Submission, Batch, MerkleProof
from src.config import settings
from src.merkle import generate_merkle_tree, calculate_tree_depth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/batching", tags=["batching"])


class CreateBatchRequest(BaseModel):
    """Request to create a batch manually."""

    max_size: int = 1000  # Maximum number of submissions to include


class CreateBatchResponse(BaseModel):
    """Response after creating a batch."""

    batch_id: str
    image_count: int
    merkle_root: str
    tree_depth: int
    status: str
    created_at: str


@router.post("/create-batch", response_model=CreateBatchResponse)
async def create_batch_manually(
    request: CreateBatchRequest,
    db: AsyncSession = Depends(get_db),
) -> CreateBatchResponse:
    """
    Manually create a batch from validated submissions (Phase 1).

    Fetches up to max_size validated submissions, generates Merkle tree,
    and stores proofs. Posts to blockchain if enabled.
    """
    # 1. Get validated submissions not yet in batch
    stmt = (
        select(Submission)
        .where(Submission.validation_status == "validated")
        .where(Submission.batch_id.is_(None))
        .order_by(Submission.received_at)
        .limit(request.max_size)
    )
    result = await db.execute(stmt)
    submissions = result.scalars().all()

    if not submissions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No validated submissions available for batching",
        )

    logger.info(f"Creating batch with {len(submissions)} submissions")

    # 2. Create batch record (placeholder merkle_root)
    batch = Batch(
        image_count=len(submissions),
        merkle_root="0" * 64,  # Placeholder
        tree_depth=calculate_tree_depth(len(submissions)),
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    db.add(batch)
    await db.flush()  # Get batch_id

    # 3. Update submissions with batch_id
    submission_ids = [s.submission_id for s in submissions]
    stmt = (
        update(Submission)
        .where(Submission.submission_id.in_(submission_ids))
        .values(batch_id=batch.batch_id)
    )
    await db.execute(stmt)
    await db.commit()

    # 4. Generate Merkle tree
    image_hashes = [s.image_hash for s in submissions]
    merkle_root, proofs = generate_merkle_tree(image_hashes)

    # 5. Update batch with merkle_root
    stmt = (
        update(Batch)
        .where(Batch.batch_id == batch.batch_id)
        .values(merkle_root=merkle_root, status="merkle_complete")
    )
    await db.execute(stmt)

    # 6. Store Merkle proofs
    for idx, image_hash in enumerate(image_hashes):
        proof = MerkleProof(
            batch_id=batch.batch_id,
            image_hash=image_hash,
            leaf_index=idx,
            proof_path=proofs[image_hash],  # JSONB will serialize automatically
        )
        db.add(proof)

    await db.commit()

    logger.info(f"Batch {batch.batch_id} created with Merkle root {merkle_root}")

    # 7. Post to blockchain (if enabled)
    if settings.blockchain_enabled:
        from src.blockchain import post_batch_to_blockchain

        await post_batch_to_blockchain(batch.batch_id, merkle_root, len(submissions), db)
    else:
        # Phase 1: Mock blockchain posting
        from src.blockchain import mock_blockchain_post

        await mock_blockchain_post(batch.batch_id, merkle_root, len(submissions), db)

    # Refresh batch to get updated status
    await db.refresh(batch)

    return CreateBatchResponse(
        batch_id=str(batch.batch_id),
        image_count=batch.image_count,
        merkle_root=batch.merkle_root,
        tree_depth=batch.tree_depth,
        status=batch.status,
        created_at=batch.created_at.isoformat() + "Z",
    )


@router.get("/stats")
async def get_batching_stats(db: AsyncSession = Depends(get_db)):
    """Get batching statistics."""
    from sqlalchemy import func

    # Count pending submissions
    stmt = (
        select(func.count())
        .select_from(Submission)
        .where(Submission.validation_status == "validated")
        .where(Submission.batch_id.is_(None))
    )
    result = await db.execute(stmt)
    pending_count = result.scalar_one()

    # Count total batches
    stmt = select(func.count()).select_from(Batch)
    result = await db.execute(stmt)
    total_batches = result.scalar_one()

    # Get last batch
    stmt = select(Batch).order_by(Batch.created_at.desc()).limit(1)
    result = await db.execute(stmt)
    last_batch = result.scalar_one_or_none()

    return {
        "pending_validated_submissions": pending_count,
        "total_batches": total_batches,
        "last_batch": {
            "batch_id": str(last_batch.batch_id),
            "image_count": last_batch.image_count,
            "merkle_root": last_batch.merkle_root,
            "created_at": last_batch.created_at.isoformat() + "Z",
            "status": last_batch.status,
        }
        if last_batch
        else None,
        "ready_for_batch": pending_count >= settings.batch_size,
    }
