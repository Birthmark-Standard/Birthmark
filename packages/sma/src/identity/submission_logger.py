# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Submission logging for abuse detection.

Tracks device submission history to enable:
- Automated blacklisting at 10,000/day
- Warning system at 8,000/day
- Usage statistics and monitoring

Phase 2: JSON file storage
Phase 3: PostgreSQL database storage
"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict


@dataclass
class SubmissionRecord:
    """
    Single submission record.

    Database schema (Phase 3):
    CREATE TABLE submissions (
        id SERIAL PRIMARY KEY,
        device_serial VARCHAR(255) NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        validation_result VARCHAR(10) NOT NULL,
        INDEX idx_device_timestamp (device_serial, timestamp)
    );
    """
    device_serial: str
    timestamp: str  # ISO 8601 timestamp
    validation_result: str  # "pass" or "fail"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SubmissionRecord":
        """Create from dictionary (JSON deserialization)."""
        return cls(**data)


class SubmissionLogger:
    """
    Logs and queries device submission history.

    Phase 2: File-based storage
    Phase 3: Database-backed storage
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize submission logger.

        Args:
            storage_path: Path to JSON file for submission logs
        """
        self.storage_path = storage_path
        self._submissions: List[SubmissionRecord] = []

        if storage_path and storage_path.exists():
            self.load_from_file(storage_path)

    def log_submission(
        self,
        device_serial: str,
        validation_result: str,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Log a device submission.

        Args:
            device_serial: Device serial number
            validation_result: "pass" or "fail"
            timestamp: Submission timestamp (default: now)
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        record = SubmissionRecord(
            device_serial=device_serial,
            timestamp=timestamp.isoformat(),
            validation_result=validation_result
        )

        self._submissions.append(record)

    def count_submissions(
        self,
        device_serial: str,
        since: Optional[datetime] = None,
        hours: Optional[int] = None
    ) -> int:
        """
        Count submissions for a device.

        Args:
            device_serial: Device serial number
            since: Count submissions since this timestamp
            hours: Count submissions in last N hours (shorthand)

        Returns:
            Number of submissions matching criteria
        """
        if hours is not None:
            since = datetime.utcnow() - timedelta(hours=hours)

        count = 0
        for record in self._submissions:
            if record.device_serial != device_serial:
                continue

            if since:
                record_time = datetime.fromisoformat(record.timestamp)
                if record_time < since:
                    continue

            count += 1

        return count

    def get_submissions(
        self,
        device_serial: Optional[str] = None,
        since: Optional[datetime] = None,
        hours: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[SubmissionRecord]:
        """
        Get submission records with optional filtering.

        Args:
            device_serial: Optional filter by device
            since: Optional filter by timestamp
            hours: Optional filter by last N hours
            limit: Optional limit number of results

        Returns:
            List of matching submission records
        """
        if hours is not None:
            since = datetime.utcnow() - timedelta(hours=hours)

        results = []
        for record in reversed(self._submissions):  # Most recent first
            if device_serial and record.device_serial != device_serial:
                continue

            if since:
                record_time = datetime.fromisoformat(record.timestamp)
                if record_time < since:
                    continue

            results.append(record)

            if limit and len(results) >= limit:
                break

        return results

    def get_top_submitters(
        self,
        hours: int = 24,
        limit: int = 10
    ) -> List[tuple[str, int]]:
        """
        Get devices with most submissions in time window.

        Args:
            hours: Time window in hours (default: 24)
            limit: Number of results (default: 10)

        Returns:
            List of (device_serial, count) tuples, sorted by count descending
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        counts: Dict[str, int] = defaultdict(int)

        for record in self._submissions:
            record_time = datetime.fromisoformat(record.timestamp)
            if record_time >= since:
                counts[record.device_serial] += 1

        # Sort by count descending
        sorted_counts = sorted(
            counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_counts[:limit]

    def check_abuse_threshold(
        self,
        device_serial: str,
        threshold: int = 10_000,
        hours: int = 24
    ) -> tuple[bool, int]:
        """
        Check if device has exceeded abuse threshold.

        Args:
            device_serial: Device serial number
            threshold: Submission threshold (default: 10,000)
            hours: Time window in hours (default: 24)

        Returns:
            Tuple of (exceeded_threshold, current_count)
        """
        count = self.count_submissions(device_serial, hours=hours)
        return (count >= threshold, count)

    def get_all_device_serials(self) -> List[str]:
        """
        Get list of all device serials that have submissions.

        Returns:
            List of unique device serial numbers
        """
        serials = set()
        for record in self._submissions:
            serials.add(record.device_serial)
        return sorted(serials)

    def save_to_file(self, path: Optional[Path] = None) -> None:
        """
        Save submission logs to JSON file.

        Args:
            path: Output file path (uses self.storage_path if None)
        """
        if path is None:
            path = self.storage_path

        if path is None:
            raise ValueError("No storage path specified")

        data = {
            "total_submissions": len(self._submissions),
            "last_updated": datetime.utcnow().isoformat(),
            "submissions": [
                record.to_dict()
                for record in self._submissions
            ]
        }

        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write to file
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        # Set restrictive permissions
        path.chmod(0o600)

    def load_from_file(self, path: Optional[Path] = None) -> None:
        """
        Load submission logs from JSON file.

        Args:
            path: Input file path (uses self.storage_path if None)
        """
        if path is None:
            path = self.storage_path

        if path is None:
            raise ValueError("No storage path specified")

        if not path.exists():
            raise FileNotFoundError(f"Submission log file not found: {path}")

        with open(path, "r") as f:
            data = json.load(f)

        self._submissions = [
            SubmissionRecord.from_dict(record_data)
            for record_data in data["submissions"]
        ]

    def get_statistics(self) -> dict:
        """
        Get statistics about submissions.

        Returns:
            Dictionary with submission statistics
        """
        if not self._submissions:
            return {
                "total_submissions": 0,
                "unique_devices": 0,
                "oldest_submission": None,
                "newest_submission": None
            }

        timestamps = [
            datetime.fromisoformat(r.timestamp)
            for r in self._submissions
        ]

        unique_devices = len(set(r.device_serial for r in self._submissions))

        return {
            "total_submissions": len(self._submissions),
            "unique_devices": unique_devices,
            "oldest_submission": min(timestamps).isoformat(),
            "newest_submission": max(timestamps).isoformat(),
            "submissions_last_24h": self.count_submissions_all(hours=24),
            "submissions_last_1h": self.count_submissions_all(hours=1)
        }

    def count_submissions_all(self, hours: int) -> int:
        """
        Count total submissions across all devices in time window.

        Args:
            hours: Time window in hours

        Returns:
            Total submission count
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        count = 0

        for record in self._submissions:
            record_time = datetime.fromisoformat(record.timestamp)
            if record_time >= since:
                count += 1

        return count

    def cleanup_old_submissions(self, days: int = 90) -> int:
        """
        Remove submissions older than specified days.

        Args:
            days: Remove submissions older than this many days

        Returns:
            Number of submissions removed
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        original_count = len(self._submissions)

        self._submissions = [
            record for record in self._submissions
            if datetime.fromisoformat(record.timestamp) >= cutoff
        ]

        removed = original_count - len(self._submissions)
        return removed
