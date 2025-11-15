"""Verification API endpoints for querying image authenticity."""

import json
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import Submission, Batch, MerkleProof
from src.schemas import (
    VerificationResponse,
    BatchVerifyRequest,
    BatchVerifyResponse,
    AuthorityInfo,
    BlockchainInfo,
    MerkleProofStep,
    ProvenanceResponse,
    ProvenanceEntry,
    OriginalCaptureInfo,
)

router = APIRouter(prefix="/api/v1", tags=["verification"])


@router.get("/verify", response_model=VerificationResponse)
async def verify_image(
    image_hash: str = Query(..., min_length=64, max_length=64),
    db: AsyncSession = Depends(get_db),
) -> VerificationResponse:
    """
    Verify image authenticity by hash.

    Returns verification status, modification level, authority info, and Merkle proof.
    """
    image_hash = image_hash.lower()

    # Query submission with batch info
    stmt = (
        select(Submission, Batch, MerkleProof)
        .outerjoin(Batch, Submission.batch_id == Batch.batch_id)
        .outerjoin(MerkleProof, MerkleProof.image_hash == Submission.image_hash)
        .where(Submission.image_hash == image_hash)
    )
    result = await db.execute(stmt)
    row = result.first()

    if not row:
        return VerificationResponse(
            status="not_found",
            image_hash=image_hash,
            message="This image hash has not been authenticated via Birthmark Protocol",
        )

    submission, batch, merkle_proof = row

    # Validation failed
    if submission.validation_status == "validation_failed":
        return VerificationResponse(
            status="validation_failed",
            image_hash=image_hash,
            submission_type=submission.submission_type,
            message="Authentication failed",
            error=submission.validation_error,
        )

    # Pending (not yet batched)
    if submission.batch_id is None:
        from src.api.submissions import estimate_batch_time

        return VerificationResponse(
            status="pending",
            image_hash=image_hash,
            submission_type=submission.submission_type,
            modification_level=submission.modification_level,
            message="Image submitted but not yet posted to blockchain",
            validation_status=submission.validation_status,
            estimated_batch_time=estimate_batch_time(),
        )

    # Verified (in batch)
    authority = build_authority_info(submission)
    mod_description = get_modification_description(
        submission.modification_level, submission.submission_type
    )

    # Parse Merkle proof
    proof_steps = None
    if merkle_proof:
        proof_path = merkle_proof.proof_path
        if isinstance(proof_path, str):
            proof_path = json.loads(proof_path)
        proof_steps = [MerkleProofStep(**step) for step in proof_path]

    blockchain_info = None
    if batch.zksync_tx_hash:
        blockchain_info = BlockchainInfo(
            network="zkSync Era (Mock)" if batch.zksync_tx_hash.startswith("0xMOCK_") else "zkSync Era",
            tx_hash=batch.zksync_tx_hash,
            block_number=batch.zksync_block_number or 0,
            confirmed_at=batch.confirmed_at.isoformat() + "Z" if batch.confirmed_at else "",
        )

    return VerificationResponse(
        status="verified",
        image_hash=image_hash,
        submission_type=submission.submission_type,
        modification_level=submission.modification_level,
        modification_level_description=mod_description,
        parent_image_hash=submission.parent_image_hash,
        authority=authority,
        batch_id=str(submission.batch_id) if submission.batch_id else None,
        batch_index=merkle_proof.leaf_index if merkle_proof else None,
        timestamp=submission.timestamp,
        merkle_root=batch.merkle_root if batch else None,
        merkle_proof=proof_steps,
        blockchain=blockchain_info,
    )


@router.post("/verify/batch", response_model=BatchVerifyResponse)
async def verify_batch(
    request: BatchVerifyRequest,
    db: AsyncSession = Depends(get_db),
) -> BatchVerifyResponse:
    """Verify multiple images at once (max 100)."""
    results = []
    for image_hash in request.image_hashes:
        result = await verify_image(image_hash=image_hash, db=db)
        results.append(result)

    return BatchVerifyResponse(results=results)


def build_authority_info(submission: Submission) -> AuthorityInfo:
    """Build authority info based on submission type."""
    if submission.submission_type == "camera":
        # Extract manufacturer name from authority_id (e.g., "CANON_001" -> "Canon")
        manufacturer_name = submission.manufacturer_authority_id.split("_")[0].capitalize()
        return AuthorityInfo(
            type="manufacturer",
            authority_id=submission.manufacturer_authority_id,
            name=manufacturer_name,
        )
    else:
        return AuthorityInfo(
            type="developer",
            authority_id=submission.developer_authority_id,
            version_string=submission.developer_version_string,
        )


def get_modification_description(modification_level: int, submission_type: str) -> str:
    """Get human-readable modification level description."""
    descriptions = {
        (0, "camera"): "raw",
        (1, "camera"): "processed",
        (1, "software"): "slight_modifications",
        (2, "software"): "significant_modifications",
    }
    return descriptions.get((modification_level, submission_type), "unknown")


@router.get("/provenance", response_model=ProvenanceResponse)
async def get_provenance_chain(
    image_hash: str = Query(..., min_length=64, max_length=64),
    db: AsyncSession = Depends(get_db),
) -> ProvenanceResponse:
    """
    Trace the complete provenance chain for an image.

    Follows parent_image_hash references back to the original camera capture,
    showing the full modification history.
    """
    image_hash = image_hash.lower()

    # Build chain by following parent_image_hash references
    chain: list[ProvenanceEntry] = []
    current_hash = image_hash
    max_depth = 100  # Prevent infinite loops
    visited_hashes = set()

    for _ in range(max_depth):
        if current_hash in visited_hashes:
            # Circular reference detected, break
            break
        visited_hashes.add(current_hash)

        # Query submission
        stmt = select(Submission).where(Submission.image_hash == current_hash)
        result = await db.execute(stmt)
        submission = result.scalar_one_or_none()

        if not submission:
            # Parent not found, break chain
            break

        # Build authority info
        authority = build_authority_info(submission)

        # Build provenance entry
        entry = ProvenanceEntry(
            image_hash=submission.image_hash,
            submission_type=submission.submission_type,
            modification_level=submission.modification_level,
            modification_level_description=get_modification_description(
                submission.modification_level, submission.submission_type
            ),
            authority=authority,
            timestamp=submission.timestamp,
            parent_image_hash=submission.parent_image_hash,
        )
        chain.append(entry)

        # Move to parent
        if submission.parent_image_hash is None:
            # Reached original image
            break
        current_hash = submission.parent_image_hash

    # Reverse chain to show oldest first (original capture at top)
    chain.reverse()

    # Extract original capture info (first entry in chain)
    original_capture = None
    if chain and chain[0].submission_type == "camera":
        original_capture = OriginalCaptureInfo(
            image_hash=chain[0].image_hash,
            timestamp=chain[0].timestamp,
            manufacturer=chain[0].authority.authority_id,
        )

    # Total modification level is the highest in the chain
    total_modification_level = max((entry.modification_level for entry in chain), default=None)

    return ProvenanceResponse(
        image_hash=image_hash,
        provenance_chain=chain,
        chain_length=len(chain),
        original_capture=original_capture,
        total_modification_level=total_modification_level,
    )
