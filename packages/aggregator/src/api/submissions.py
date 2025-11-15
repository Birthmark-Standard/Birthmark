"""Submission API endpoints for camera and software submissions."""

import uuid
import time
import logging
from typing import Union, Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from src.database import get_db
from src.models import Submission
from src.config import settings
from src.schemas import (
    CameraSubmissionRequest,
    SoftwareSubmissionRequest,
    SubmissionResponse,
    ErrorResponse,
    CameraToken,
    CameraValidationBatchRequest,
    CameraValidationRequest,
    SoftwareValidationBatchRequest,
    SoftwareValidationRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["submissions"])


@router.post(
    "/submit",
    response_model=SubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
async def submit_authentication_bundle(
    request: Union[CameraSubmissionRequest, SoftwareSubmissionRequest],
    db: AsyncSession = Depends(get_db),
) -> SubmissionResponse:
    """
    Submit authentication bundle from camera or software.

    - **Camera submissions**: 1-4 image hashes with camera token
    - **Software submissions**: Single edited hash with parent reference

    Returns submission IDs and estimated batch time.
    """
    if isinstance(request, CameraSubmissionRequest):
        return await handle_camera_submission(request, db)
    elif isinstance(request, SoftwareSubmissionRequest):
        return await handle_software_submission(request, db)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_SUBMISSION_TYPE", "message": "Invalid submission type"},
        )


async def handle_camera_submission(
    request: CameraSubmissionRequest, db: AsyncSession
) -> SubmissionResponse:
    """Handle camera submission with 1-4 image hashes."""

    # 1. Check for duplicate submissions
    image_hashes = [entry.image_hash for entry in request.image_hashes]
    stmt = select(Submission).where(Submission.image_hash.in_(image_hashes))
    result = await db.execute(stmt)
    existing = result.scalars().all()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "error",
                "error_code": "DUPLICATE_SUBMISSION",
                "message": f"Image hash already submitted: {existing[0].image_hash}",
                "field": "image_hashes",
            },
        )

    # 2. Validate parent-child relationships
    for entry in request.image_hashes:
        if entry.modification_level == 1 and entry.parent_image_hash is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "error_code": "MISSING_PARENT_HASH",
                    "message": "Processed images (modification_level=1) must have parent_image_hash",
                    "field": "image_hashes",
                },
            )

    # 3. Generate transaction_id for this camera submission (all hashes share validation)
    transaction_id = uuid.uuid4()

    # 4. Store all image hashes with same camera_token and transaction_id
    submission_ids = []
    for entry in request.image_hashes:
        submission = Submission(
            submission_type="camera",
            image_hash=entry.image_hash,
            modification_level=entry.modification_level,
            parent_image_hash=entry.parent_image_hash,
            camera_token_ciphertext=request.camera_token.ciphertext,
            camera_token_auth_tag=request.camera_token.auth_tag,
            camera_token_nonce=request.camera_token.nonce,
            table_id=request.camera_token.table_id,
            key_index=request.camera_token.key_index,
            manufacturer_authority_id=request.manufacturer_cert.authority_id,
            manufacturer_validation_endpoint=request.manufacturer_cert.validation_endpoint,
            timestamp=request.timestamp,
            transaction_id=transaction_id,
            validation_status="pending",
            received_at=datetime.now(timezone.utc),
        )
        db.add(submission)
        await db.flush()  # Get submission_id
        submission_ids.append(submission.submission_id)

    await db.commit()

    # 5. Validate with SMA (inline for Phase 1)
    if settings.sma_enabled:
        await validate_camera_transaction(transaction_id, request, db)

    # 6. Get queue position and estimate batch time
    queue_position = await get_queue_position(db)
    estimated_batch_time = estimate_batch_time()

    return SubmissionResponse(
        status="accepted",
        submission_ids=submission_ids,
        queue_position=queue_position,
        estimated_batch_time=estimated_batch_time,
    )


async def handle_software_submission(
    request: SoftwareSubmissionRequest, db: AsyncSession
) -> SubmissionResponse:
    """Handle software submission with single edited hash."""

    # 1. Check for duplicate submission
    stmt = select(Submission).where(Submission.image_hash == request.image_hash)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "error",
                "error_code": "DUPLICATE_SUBMISSION",
                "message": f"Image hash already submitted: {request.image_hash}",
                "field": "image_hash",
            },
        )

    # 2. Store submission
    submission = Submission(
        submission_type="software",
        image_hash=request.image_hash,
        modification_level=request.modification_level,
        parent_image_hash=request.parent_image_hash,
        program_token=request.program_token,
        developer_authority_id=request.developer_cert.authority_id,
        developer_version_string=request.developer_cert.version_string,
        developer_validation_endpoint=request.developer_cert.validation_endpoint,
        validation_status="pending",
        received_at=datetime.now(timezone.utc),
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    # 3. Validate with SSA (inline for Phase 1)
    if settings.ssa_enabled:
        await validate_software_submission(submission.submission_id, request, db)

    # 4. Get queue position and estimate batch time
    queue_position = await get_queue_position(db)
    estimated_batch_time = estimate_batch_time()

    return SubmissionResponse(
        status="accepted",
        submission_ids=[submission.submission_id],
        queue_position=queue_position,
        estimated_batch_time=estimated_batch_time,
    )


async def get_queue_position(db: AsyncSession) -> int:
    """Get current queue position (number of pending submissions)."""
    from sqlalchemy import func

    stmt = select(func.count()).select_from(Submission).where(Submission.batch_id.is_(None))
    result = await db.execute(stmt)
    count = result.scalar_one()
    return count


def estimate_batch_time() -> str:
    """
    Estimate when next batch will be posted.

    Phase 1: Simple estimate based on batch size of 1000.
    Phase 2+: Use actual batching logic with time constraints.
    """
    from datetime import timedelta

    # Simple estimate: next batch in ~15 minutes
    estimated_time = datetime.now(timezone.utc) + timedelta(minutes=15)
    return estimated_time.isoformat().replace("+00:00", "Z")


async def validate_camera_transaction(
    transaction_id: uuid.UUID, request: CameraSubmissionRequest, db: AsyncSession
) -> None:
    """
    Validate camera transaction with SMA (inline for Phase 1).

    All submissions with this transaction_id will be updated with validation result.
    """
    try:
        # Build validation request
        validation_req = CameraValidationRequest(
            transaction_id=str(transaction_id),
            camera_token=request.camera_token,
            manufacturer_authority_id=request.manufacturer_cert.authority_id,
        )

        # Call SMA validation endpoint
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.sma_endpoint,
                json={"validation_requests": [validation_req.model_dump()]},
                timeout=10.0,
            )
            response.raise_for_status()
            result = response.json()

        # Process validation result
        if result["validation_results"]:
            validation_result = result["validation_results"][0]
            if validation_result["status"] == "pass":
                # Update all submissions in this transaction as validated
                stmt = (
                    update(Submission)
                    .where(Submission.transaction_id == transaction_id)
                    .values(
                        validation_status="validated",
                        validated_at=datetime.now(timezone.utc),
                    )
                )
                await db.execute(stmt)
                await db.commit()
                logger.info(f"Camera transaction {transaction_id} validated successfully")
            else:
                # Validation failed
                error_msg = validation_result.get("status", "Unknown error")
                stmt = (
                    update(Submission)
                    .where(Submission.transaction_id == transaction_id)
                    .values(
                        validation_status="validation_failed",
                        validation_error=error_msg,
                    )
                )
                await db.execute(stmt)
                await db.commit()
                logger.warning(
                    f"Camera transaction {transaction_id} validation failed: {error_msg}"
                )

    except Exception as e:
        logger.error(f"SMA validation error for transaction {transaction_id}: {e}")
        # Leave submissions in pending state on error
        # Could implement retry logic here for Phase 2


async def validate_software_submission(
    submission_id: uuid.UUID, request: SoftwareSubmissionRequest, db: AsyncSession
) -> None:
    """
    Validate software submission with SSA (inline for Phase 1).
    """
    try:
        # Build validation request
        validation_req = SoftwareValidationRequest(
            submission_id=str(submission_id),
            program_token=request.program_token,
            developer_authority_id=request.developer_cert.authority_id,
            version_string=request.developer_cert.version_string,
        )

        # Call SSA validation endpoint
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.ssa_endpoint,
                json={"validation_requests": [validation_req.model_dump()]},
                timeout=10.0,
            )
            response.raise_for_status()
            result = response.json()

        # Process validation result
        if result["validation_results"]:
            validation_result = result["validation_results"][0]
            if validation_result["status"] == "pass":
                # Update submission as validated
                stmt = (
                    update(Submission)
                    .where(Submission.submission_id == submission_id)
                    .values(
                        validation_status="validated",
                        validated_at=datetime.now(timezone.utc),
                    )
                )
                await db.execute(stmt)
                await db.commit()
                logger.info(f"Software submission {submission_id} validated successfully")
            else:
                # Validation failed
                error_msg = validation_result.get("status", "Unknown error")
                stmt = (
                    update(Submission)
                    .where(Submission.submission_id == submission_id)
                    .values(
                        validation_status="validation_failed",
                        validation_error=error_msg,
                    )
                )
                await db.execute(stmt)
                await db.commit()
                logger.warning(
                    f"Software submission {submission_id} validation failed: {error_msg}"
                )

    except Exception as e:
        logger.error(f"SSA validation error for submission {submission_id}: {e}")
        # Leave submission in pending state on error
        # Could implement retry logic here for Phase 2
