# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Persistent submission queue for reliable certificate delivery.

Saves certificate bundles to disk before transmission and only deletes
them after receiving server acknowledgment. Retransmits on camera restart.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)


@dataclass
class QueuedSubmission:
    """A submission bundle saved to disk awaiting transmission."""

    bundle_id: str  # Unique ID (hash + timestamp)
    bundle_data: dict  # Serialized certificate bundle
    created_at: float  # Unix timestamp
    attempts: int = 0  # Number of transmission attempts
    last_attempt: Optional[float] = None


class PersistentQueue:
    """
    Persistent queue for certificate bundles.

    Saves bundles to disk before transmission, ensuring no data loss
    even if camera loses power or network connection during submission.
    """

    def __init__(self, queue_dir: Path):
        """
        Initialize persistent queue.

        Args:
            queue_dir: Directory to store pending submissions
        """
        self.queue_dir = Path(queue_dir)
        self.queue_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Persistent queue initialized: {self.queue_dir}")

    def enqueue(self, bundle_id: str, bundle_data: dict) -> None:
        """
        Save bundle to disk for pending transmission.

        Args:
            bundle_id: Unique identifier (e.g., hash[:16] + timestamp)
            bundle_data: Serialized certificate bundle
        """
        submission = QueuedSubmission(
            bundle_id=bundle_id,
            bundle_data=bundle_data,
            created_at=time.time(),
        )

        filepath = self.queue_dir / f"{bundle_id}.json"

        with open(filepath, 'w') as f:
            json.dump({
                'bundle_id': submission.bundle_id,
                'bundle_data': submission.bundle_data,
                'created_at': submission.created_at,
                'attempts': submission.attempts,
                'last_attempt': submission.last_attempt,
            }, f, indent=2)

        logger.info(f"✓ Queued: {bundle_id} → {filepath.name}")

    def dequeue(self, bundle_id: str) -> None:
        """
        Remove bundle from disk after successful transmission.

        Args:
            bundle_id: Identifier of successfully transmitted bundle
        """
        filepath = self.queue_dir / f"{bundle_id}.json"

        if filepath.exists():
            filepath.unlink()
            logger.info(f"✓ Dequeued: {bundle_id}")
        else:
            logger.warning(f"⚠ Bundle not found for dequeue: {bundle_id}")

    def record_attempt(self, bundle_id: str) -> None:
        """
        Record a transmission attempt for a bundle.

        Args:
            bundle_id: Identifier of bundle being attempted
        """
        filepath = self.queue_dir / f"{bundle_id}.json"

        if not filepath.exists():
            return

        with open(filepath, 'r') as f:
            data = json.load(f)

        data['attempts'] = data.get('attempts', 0) + 1
        data['last_attempt'] = time.time()

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def get_pending(self) -> List[QueuedSubmission]:
        """
        Get all pending submissions from disk.

        Returns:
            List of queued submissions ordered by creation time
        """
        pending = []

        for filepath in sorted(self.queue_dir.glob("*.json")):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)

                submission = QueuedSubmission(
                    bundle_id=data['bundle_id'],
                    bundle_data=data['bundle_data'],
                    created_at=data['created_at'],
                    attempts=data.get('attempts', 0),
                    last_attempt=data.get('last_attempt'),
                )

                pending.append(submission)

            except Exception as e:
                logger.error(f"Error loading queued submission {filepath}: {e}")

        return pending

    def get_count(self) -> int:
        """
        Get number of pending submissions.

        Returns:
            Count of pending submissions
        """
        return len(list(self.queue_dir.glob("*.json")))

    def cleanup_old(self, max_age_hours: int = 24) -> int:
        """
        Clean up old submissions that failed repeatedly.

        Args:
            max_age_hours: Maximum age in hours before cleanup

        Returns:
            Number of submissions cleaned up
        """
        cleanup_threshold = time.time() - (max_age_hours * 3600)
        cleaned = 0

        for filepath in self.queue_dir.glob("*.json"):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)

                # Clean up if:
                # 1. Very old (> max_age_hours)
                # 2. Many failed attempts (> 10)
                if (data['created_at'] < cleanup_threshold and
                    data.get('attempts', 0) > 10):

                    logger.warning(
                        f"Cleaning up old submission: {data['bundle_id']} "
                        f"(age: {(time.time() - data['created_at']) / 3600:.1f}h, "
                        f"attempts: {data.get('attempts', 0)})"
                    )

                    filepath.unlink()
                    cleaned += 1

            except Exception as e:
                logger.error(f"Error during cleanup of {filepath}: {e}")

        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} old submissions")

        return cleaned
