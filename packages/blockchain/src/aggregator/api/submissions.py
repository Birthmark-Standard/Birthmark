"""Aggregator API for camera submissions."""

import logging
import uuid
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.database.connection import get_db
from src.shared.database.models import PendingSubmission
from src.shared.models.schemas import (
    AuthenticationBundle,
    CameraSubmission,
    CertificateBundle,
    SubmissionResponse,
)
from src.aggregator.validation.sma_client import sma_client
from src.aggregator.validation.certificate_validator import certificate_validator
from src.aggregator.blockchain.blockchain_client import blockchain_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["aggregator"])


@router.post("/submit", response_model=SubmissionResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_camera_bundle(
    submission: CameraSubmission,
    db: AsyncSession = Depends(get_db),
) -> SubmissionResponse:
    """
    Submit camera authentication bundle with 2-hash array (raw + processed).

    This is the Phase 1 endpoint for cameras to submit image hashes for verification.
    The submission includes 1-2 hashes (raw, optionally processed) grouped by transaction_id.

    Args:
        submission: Camera submission with image_hashes array and structured camera_token
        db: Database session

    Returns:
        Receipt with transaction ID and status
    """
    transaction_id = str(uuid.uuid4())

    logger.info(
        f"Received camera submission {transaction_id}: "
        f"{len(submission.image_hashes)} hashes, "
        f"manufacturer={submission.manufacturer_cert.authority_id}"
    )

    # Store all image hashes with shared transaction_id
    submission_records = []
    for entry in submission.image_hashes:
        pending = PendingSubmission(
            image_hash=entry.image_hash,
            modification_level=entry.modification_level,
            parent_image_hash=entry.parent_image_hash,
            transaction_id=transaction_id,
            manufacturer_authority_id=submission.manufacturer_cert.authority_id,
            camera_token_json=submission.camera_token.model_dump_json(),
            timestamp=submission.timestamp,
            sma_validated=False,
            # Legacy fields set to None
            encrypted_token=None,
            table_references=None,
            key_indices=None,
            device_signature=None,
        )
        db.add(pending)
        submission_records.append(pending)

    await db.commit()

    logger.info(
        f"Camera submission {transaction_id} queued: "
        f"hashes={[s.image_hash[:16] + '...' for s in submission_records]}"
    )

    # Validate camera token with SMA (validates once for all hashes in transaction)
    try:
        await validate_camera_transaction_inline(
            transaction_id=transaction_id,
            camera_token=submission.camera_token,
            manufacturer_authority_id=submission.manufacturer_cert.authority_id,
            validation_endpoint=submission.manufacturer_cert.validation_endpoint,
            db=db,
        )
    except Exception as e:
        logger.error(f"Validation error for transaction {transaction_id}: {e}")

    return SubmissionResponse(
        receipt_id=transaction_id,
        status="pending_validation",
        message=f"Submitted {len(submission.image_hashes)} hashes for validation",
    )


async def validate_camera_transaction_inline(
    transaction_id: str,
    camera_token,  # CameraToken object
    manufacturer_authority_id: str,
    validation_endpoint: str,
    db: AsyncSession,
) -> None:
    """
    Validate camera transaction with SMA (inline for Phase 1).

    All hashes in the transaction share the same camera_token validation.
    If validation passes, all hashes are marked as validated.
    If validation fails, all hashes are marked as failed.

    Args:
        transaction_id: UUID grouping all hashes from this camera submission
        camera_token: Structured CameraToken object
        manufacturer_authority_id: Manufacturer ID (e.g., "CANON_001")
        validation_endpoint: SMA validation URL
        db: Database session
    """
    logger.info(f"Validating camera transaction {transaction_id} with SMA")

    # Call SMA for validation (new format)
    validation_result = await sma_client.validate_camera_token(
        camera_token=camera_token,
        manufacturer_authority_id=manufacturer_authority_id,
    )

    # Update all submissions in this transaction
    from sqlalchemy import update

    stmt = (
        update(PendingSubmission)
        .where(PendingSubmission.transaction_id == transaction_id)
        .values(
            validation_attempted_at=datetime.utcnow(),
            sma_validated=validation_result.valid,
            validation_result="PASS" if validation_result.valid else "FAIL",
        )
    )

    await db.execute(stmt)
    await db.commit()

    if not validation_result.valid:
        logger.warning(
            f"SMA validation FAILED for transaction {transaction_id}: "
            f"{validation_result.message}"
        )
    else:
        logger.info(f"SMA validation PASSED for transaction {transaction_id}")

        # Submit validated hashes to blockchain immediately (no batching)
        from sqlalchemy import select

        stmt = select(PendingSubmission).where(
            PendingSubmission.transaction_id == transaction_id
        )
        result = await db.execute(stmt)
        submissions = result.scalars().all()

        for submission in submissions:
            try:
                blockchain_result = await blockchain_client.submit_hash(
                    image_hash=submission.image_hash,
                    timestamp=submission.timestamp,
                    aggregator_id="aggregator_node_001",  # TODO: Get from config
                    modification_level=submission.modification_level,
                    parent_image_hash=submission.parent_image_hash,
                    manufacturer_authority_id=submission.manufacturer_authority_id,
                )

                if blockchain_result.success:
                    # Update submission with blockchain tx_id
                    submission.tx_id = blockchain_result.tx_id
                    logger.info(
                        f"Hash {submission.image_hash[:16]}... submitted to blockchain: "
                        f"tx_id={blockchain_result.tx_id}, block_height={blockchain_result.block_height}"
                    )
                else:
                    logger.error(
                        f"Blockchain submission failed for {submission.image_hash[:16]}...: "
                        f"{blockchain_result.message}"
                    )

            except Exception as e:
                logger.error(
                    f"Error submitting {submission.image_hash[:16]}... to blockchain: {e}"
                )

        await db.commit()


@router.post("/submit-legacy", response_model=SubmissionResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_authentication_bundle_legacy(
    bundle: AuthenticationBundle,
    db: AsyncSession = Depends(get_db),
) -> SubmissionResponse:
    """
    Submit authentication bundle from camera (LEGACY endpoint).

    This is the legacy entry point for cameras to submit image hashes for verification.
    The bundle is queued for SMA validation and blockchain submission.

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
    The bundle is validated with SMA and submitted to blockchain.

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
