"""
Background validation worker for MA (Manufacturer Authority) validation.

Handles asynchronous validation with retry logic and monitoring alerts.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from src.shared.database.models import PendingSubmission
from src.shared.database.connection import get_async_session
from src.submission_server.validation.sma_client import sma_client
from src.submission_server.blockchain.blockchain_client import blockchain_client

logger = logging.getLogger(__name__)


class ValidationWorker:
    """
    Background worker for MA validation with retry logic.

    Workflow:
    1. Try validation immediately (inline)
    2. If fails: Retry 3x with exponential backoff (2s, 4s, 8s)
    3. If all fail: Schedule retry in 30 minutes
    4. If 30-min retry fails: Alert monitoring server
    5. Keep alerting every 10 minutes until cleared
    """

    def __init__(self, monitoring_url: Optional[str] = None):
        """
        Initialize validation worker.

        Args:
            monitoring_url: Foundation monitoring server URL (optional)
        """
        self.running = False
        self.monitoring_url = monitoring_url or "http://monitoring.birthmarkstandard.org/alert"
        self.check_interval = 30  # Check for pending validations every 30s
        self.alert_interval = 600  # Alert every 10 minutes
        self.retry_delay = 1800  # Retry after 30 minutes

        # Track MA health per authority
        self.ma_failures = {}  # authority_id -> count of pending submissions
        self.last_alert = {}  # authority_id -> last alert timestamp

    async def start(self):
        """Start the background validation worker."""
        if self.running:
            logger.warning("Validation worker already running")
            return

        self.running = True
        logger.info("✓ Validation worker started")

        # Main worker loop
        while self.running:
            try:
                await self._process_pending_validations()
                await self._check_stuck_validations()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in validation worker: {e}")
                await asyncio.sleep(self.check_interval)

    async def stop(self):
        """Stop the background validation worker."""
        self.running = False
        logger.info("✓ Validation worker stopped")

    async def _process_pending_validations(self):
        """Process submissions pending MA validation."""
        async for session in get_async_session():
            try:
                # Find submissions pending validation
                stmt = select(PendingSubmission).where(
                    PendingSubmission.validation_status == "pending_ma_validation",
                    PendingSubmission.validation_retry_count < 5  # Max 5 total attempts
                )
                result = await session.execute(stmt)
                pending = result.scalars().all()

                if not pending:
                    return

                logger.info(f"Processing {len(pending)} pending validations")

                for submission in pending:
                    await self._validate_submission(submission, session)

                await session.commit()

            except Exception as e:
                logger.error(f"Error processing pending validations: {e}")

    async def _validate_submission(
        self,
        submission: PendingSubmission,
        session: AsyncSession
    ):
        """
        Validate a single submission with MA.

        Args:
            submission: Pending submission to validate
            session: Database session
        """
        # Check if we should retry yet (respect retry delay)
        if submission.validation_next_retry:
            next_retry = datetime.fromisoformat(submission.validation_next_retry)
            if datetime.utcnow() < next_retry:
                logger.debug(
                    f"Skipping submission {submission.id} - "
                    f"next retry at {next_retry}"
                )
                return

        # Increment retry count
        submission.validation_retry_count = (submission.validation_retry_count or 0) + 1

        logger.info(
            f"Validating submission {submission.id} with MA "
            f"(attempt {submission.validation_retry_count}/5)"
        )

        try:
            # Call MA for validation
            validation_result = await sma_client.validate_certificate_bundle(
                camera_cert=submission.camera_cert or "",
                image_hash=submission.image_hash,
                timestamp=submission.timestamp,
                gps_hash=submission.gps_hash,
                bundle_signature=submission.device_signature.decode()
                    if isinstance(submission.device_signature, bytes)
                    else submission.device_signature,
            )

            # Update submission with validation result
            submission.validation_attempted_at = datetime.utcnow()
            submission.sma_validated = validation_result.valid
            submission.validation_result = "PASS" if validation_result.valid else "FAIL"

            if validation_result.valid:
                # Success! Submit to blockchain
                logger.info(f"✅ MA validation PASSED for submission {submission.id}")

                submission.validation_status = "validated"
                submission.validation_next_retry = None

                # Submit to blockchain
                await self._submit_to_blockchain(submission, session)

                # Clear failure tracking
                if submission.manufacturer_authority_id in self.ma_failures:
                    self.ma_failures[submission.manufacturer_authority_id] -= 1
                    if self.ma_failures[submission.manufacturer_authority_id] <= 0:
                        del self.ma_failures[submission.manufacturer_authority_id]
                        logger.info(
                            f"✓ MA {submission.manufacturer_authority_id} recovered"
                        )

            else:
                # Validation failed (legitimate rejection)
                logger.warning(
                    f"❌ MA validation FAILED for submission {submission.id}: "
                    f"{validation_result.message}"
                )
                submission.validation_status = "rejected"
                submission.validation_next_retry = None

        except Exception as e:
            # Network/timeout error - schedule retry
            logger.error(f"MA validation error for submission {submission.id}: {e}")

            if submission.validation_retry_count < 3:
                # Exponential backoff: 2s, 4s, 8s
                backoff_seconds = 2 ** submission.validation_retry_count
                next_retry = datetime.utcnow() + timedelta(seconds=backoff_seconds)
                submission.validation_next_retry = next_retry.isoformat()
                logger.info(
                    f"⏱ Scheduling retry in {backoff_seconds}s "
                    f"(attempt {submission.validation_retry_count + 1}/5)"
                )

            elif submission.validation_retry_count < 5:
                # After 3 quick retries, schedule 30-minute retry
                next_retry = datetime.utcnow() + timedelta(seconds=self.retry_delay)
                submission.validation_next_retry = next_retry.isoformat()
                logger.warning(
                    f"⏱ All quick retries failed, scheduling retry in 30 minutes"
                )

                # Track MA failure
                authority_id = submission.manufacturer_authority_id or "UNKNOWN"
                self.ma_failures[authority_id] = self.ma_failures.get(authority_id, 0) + 1

            else:
                # All retries exhausted - alert monitoring
                logger.error(
                    f"❌ All 5 validation attempts failed for submission {submission.id}"
                )
                submission.validation_status = "validation_failed"
                submission.validation_next_retry = None

                # Track MA failure
                authority_id = submission.manufacturer_authority_id or "UNKNOWN"
                self.ma_failures[authority_id] = self.ma_failures.get(authority_id, 0) + 1

                # Send alert
                await self._send_monitoring_alert(
                    authority_id,
                    self.ma_failures[authority_id]
                )

    async def _check_stuck_validations(self):
        """Check for validations that have been stuck and need monitoring alerts."""
        if not self.ma_failures:
            return

        current_time = datetime.utcnow()

        for authority_id, pending_count in list(self.ma_failures.items()):
            # Check if we should send alert
            last_alert_time = self.last_alert.get(authority_id)

            if last_alert_time is None or \
               (current_time - last_alert_time).total_seconds() >= self.alert_interval:

                logger.warning(
                    f"⚠️ MA {authority_id} has {pending_count} stuck validations"
                )

                await self._send_monitoring_alert(authority_id, pending_count)
                self.last_alert[authority_id] = current_time

    async def _submit_to_blockchain(
        self,
        submission: PendingSubmission,
        session: AsyncSession
    ):
        """
        Submit validated record to blockchain.

        Args:
            submission: Validated submission
            session: Database session
        """
        try:
            blockchain_result = await blockchain_client.submit_hash(
                image_hash=submission.image_hash,
                timestamp=submission.timestamp,
                submission_server_id="submission_server_phase1_001",
                modification_level=submission.modification_level or 0,
                parent_image_hash=submission.parent_image_hash,
                manufacturer_authority_id=submission.manufacturer_authority_id or "UNKNOWN",
                owner_hash=submission.gps_hash,  # Phase 1: Using gps_hash for owner_hash
            )

            submission.blockchain_posted = True
            submission.block_number = blockchain_result.get("block_height")

            logger.info(
                f"✅ Submitted to blockchain: hash={submission.image_hash[:16]}..., "
                f"block={submission.block_number}"
            )

        except Exception as e:
            logger.error(
                f"Error submitting {submission.image_hash[:16]}... to blockchain: {e}"
            )

    async def _send_monitoring_alert(self, authority_id: str, pending_count: int):
        """
        Send alert to foundation monitoring server.

        Args:
            authority_id: MA that is failing
            pending_count: Number of submissions waiting for this MA
        """
        if not self.monitoring_url:
            logger.warning(f"No monitoring URL configured - alert not sent")
            return

        try:
            alert_data = {
                "alert_type": "ma_validation_failure",
                "authority_id": authority_id,
                "pending_count": pending_count,
                "timestamp": datetime.utcnow().isoformat(),
                "severity": "critical" if pending_count > 10 else "warning",
                "message": f"MA {authority_id} has {pending_count} submissions stuck in validation"
            }

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    self.monitoring_url,
                    json=alert_data
                )

                if response.status_code == 200:
                    logger.info(f"✓ Monitoring alert sent for MA {authority_id}")
                else:
                    logger.error(
                        f"Failed to send monitoring alert: HTTP {response.status_code}"
                    )

        except Exception as e:
            logger.error(f"Error sending monitoring alert: {e}")


# Global worker instance
validation_worker = ValidationWorker()
