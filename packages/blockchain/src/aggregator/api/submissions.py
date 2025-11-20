"""Aggregator API for camera submissions."""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.database.connection import get_db
from src.shared.database.models import PendingSubmission
from src.shared.models.schemas import AuthenticationBundle, CertificateBundle, SubmissionResponse
from src.aggregator.validation.sma_client import sma_client
from src.aggregator.validation.certificate_validator import certificate_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["aggregator"])


@router.post("/submit", response_model=SubmissionResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_authentication_bundle(
    bundle: AuthenticationBundle,
    db: AsyncSession = Depends(get_db),
) -> SubmissionResponse:
    """
    Submit authentication bundle from camera.

    This is the entry point for cameras to submit image hashes for verification.
    The bundle is queued for SMA validation and batching.

    Args:
        bundle: Authentication bundle with image hash and encrypted camera token
        db: Database session

    Returns:
        Receipt with submission ID and status
    """
    receipt_id = str(uuid.uuid4())

    logger.info(
        f"Received submission {receipt_id}: hash={bundle.image_hash[:16]}..., "
        f"timestamp={bundle.timestamp}"
    )

    # Create pending submission record
    submission = PendingSubmission(
        image_hash=bundle.image_hash,
        encrypted_token=bundle.encrypted_nuc_token,
        table_references=bundle.table_references,
        key_indices=bundle.key_indices,
        timestamp=bundle.timestamp,
        gps_hash=bundle.gps_hash,
        device_signature=bundle.device_signature,
        sma_validated=False,
        batched=False,
    )

    db.add(submission)
    await db.commit()

    logger.info(f"Submission {receipt_id} queued for validation")

    # Trigger background validation (in real system, this would be async worker)
    # For Phase 1, we validate inline
    try:
        await validate_submission_inline(submission, db)
    except Exception as e:
        logger.error(f"Validation error for {receipt_id}: {e}")

    return SubmissionResponse(
        receipt_id=receipt_id,
        status="pending_validation",
        message="Submission received and queued for validation",
    )


async def validate_submission_inline(
    submission: PendingSubmission,
    db: AsyncSession,
) -> None:
    """
    Validate submission with SMA (inline for Phase 1).

    In Phase 2+, this should be a background worker.

    Args:
        submission: Pending submission record
        db: Database session
    """
    logger.info(f"Validating submission ID={submission.id} with SMA")

    # Call SMA for validation
    validation_result = await sma_client.validate_token(
        encrypted_token=submission.encrypted_token,
        table_references=submission.table_references,
        key_indices=submission.key_indices,
    )

    # Update submission record
    submission.validation_attempted_at = datetime.utcnow()
    submission.sma_validated = validation_result.valid
    submission.validation_result = "PASS" if validation_result.valid else "FAIL"

    if not validation_result.valid:
        logger.warning(
            f"SMA validation FAILED for submission {submission.id}: "
            f"{validation_result.message}"
        )
    else:
        logger.info(f"SMA validation PASSED for submission {submission.id}")

    await db.commit()


@router.post("/submit-cert", response_model=SubmissionResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_certificate_bundle(
    bundle: CertificateBundle,
    db: AsyncSession = Depends(get_db),
) -> SubmissionResponse:
    """
    Submit certificate-based authentication bundle (Phase 2).

    This endpoint accepts X.509 certificate bundles from iOS devices with ECDSA signatures.
    The bundle is validated with SMA and queued for batching to blockchain.

    Args:
        bundle: Certificate bundle with image hash, certificate, timestamp, and signature
        db: Database session

    Returns:
        Receipt with submission ID and status
    """
    receipt_id = str(uuid.uuid4())

    logger.info(
        f"Received certificate submission {receipt_id}: hash={bundle.image_hash[:16]}..., "
        f"timestamp={bundle.timestamp}"
    )

    # Create pending submission record
    submission = PendingSubmission(
        image_hash=bundle.image_hash,
        encrypted_token=b"",  # Not used in Phase 2 (certificate-based)
        table_references=[],  # Not used in Phase 2
        key_indices=[],       # Not used in Phase 2
        timestamp=bundle.timestamp,
        gps_hash=bundle.gps_hash,
        device_signature=bundle.bundle_signature.encode() if isinstance(bundle.bundle_signature, str) else bundle.bundle_signature,
        sma_validated=False,
        batched=False,
    )

    db.add(submission)
    await db.commit()

    logger.info(f"Certificate submission {receipt_id} queued for validation")

    # Validate with SMA inline
    try:
        await validate_certificate_submission_inline(
            submission,
            bundle.camera_cert,
            bundle.image_hash,
            bundle.timestamp,
            bundle.gps_hash,
            bundle.bundle_signature,
            db
        )
    except Exception as e:
        logger.error(f"Validation error for {receipt_id}: {e}")

    return SubmissionResponse(
        receipt_id=receipt_id,
        status="pending_validation",
        message="Certificate submission received and queued for validation",
    )


async def validate_certificate_submission_inline(
    submission: PendingSubmission,
    camera_cert: str,
    image_hash: str,
    timestamp: int,
    gps_hash: Optional[str],
    bundle_signature: str,
    db: AsyncSession,
) -> None:
    """
    Validate certificate bundle submission with SMA (Phase 2).

    Args:
        submission: Pending submission record
        camera_cert: Base64-encoded PEM camera certificate
        image_hash: SHA-256 image hash
        timestamp: Unix timestamp when photo was taken
        gps_hash: Optional SHA-256 GPS hash
        bundle_signature: Base64-encoded ECDSA signature
        db: Database session
    """
    logger.info(f"Validating certificate bundle submission ID={submission.id} with SMA")

    # Call SMA for certificate bundle validation
    validation_result = await sma_client.validate_certificate_bundle(
        camera_cert=camera_cert,
        image_hash=image_hash,
        timestamp=timestamp,
        gps_hash=gps_hash,
        bundle_signature=bundle_signature,
    )

    # Update submission record
    submission.validation_attempted_at = datetime.utcnow()
    submission.sma_validated = validation_result.valid
    submission.validation_result = "PASS" if validation_result.valid else "FAIL"

    if not validation_result.valid:
        logger.warning(
            f"SMA validation FAILED for submission {submission.id}: "
            f"{validation_result.message}"
        )
    else:
        logger.info(f"SMA validation PASSED for submission {submission.id}")

    await db.commit()


@router.get("/submission/{receipt_id}", response_model=SubmissionResponse)
async def get_submission_status(
    receipt_id: str,
    db: AsyncSession = Depends(get_db),
) -> SubmissionResponse:
    """
    Get status of a submission by receipt ID.

    Args:
        receipt_id: Receipt ID from original submission
        db: Database session

    Returns:
        Current status of submission
    """
    # Note: This is a simplified version. In production, we'd store receipt_id
    # in the database for proper tracking.
    return SubmissionResponse(
        receipt_id=receipt_id,
        status="unknown",
        message="Receipt tracking not yet implemented",
    )
