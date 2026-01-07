# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Automated abuse detection and blacklisting.

Monitors submission patterns and automatically blacklists devices
that exceed usage thresholds:
- 10,000 submissions/24h: Automatic blacklist
- 8,000 submissions/24h: Warning logged

This is a fully automated system requiring no manual review.
"""

from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from .submission_logger import SubmissionLogger
from .device_registry import DeviceRegistry


@dataclass
class AbuseDetectionResult:
    """Result of abuse detection check."""
    device_serial: str
    submission_count_24h: int
    blacklisted: bool
    warning: bool
    reason: Optional[str] = None


class AbuseDetector:
    """
    Automated abuse detection system.

    Runs periodic checks and auto-blacklists high-volume devices.
    """

    # Thresholds
    BLACKLIST_THRESHOLD = 10_000  # Auto-blacklist at 10k/day
    WARNING_THRESHOLD = 8_000     # Warning at 8k/day
    TIME_WINDOW_HOURS = 24        # 24-hour rolling window

    def __init__(
        self,
        submission_logger: SubmissionLogger,
        device_registry: DeviceRegistry
    ):
        """
        Initialize abuse detector.

        Args:
            submission_logger: Submission log tracker
            device_registry: Device registration database
        """
        self.submission_logger = submission_logger
        self.device_registry = device_registry

    def check_device_abuse(
        self,
        device_serial: str
    ) -> AbuseDetectionResult:
        """
        Check single device for abuse.

        Args:
            device_serial: Device to check

        Returns:
            AbuseDetectionResult with action taken
        """
        # Count submissions in last 24 hours
        count_24h = self.submission_logger.count_submissions(
            device_serial,
            hours=self.TIME_WINDOW_HOURS
        )

        # Check if already blacklisted
        already_blacklisted = self.device_registry.is_device_blacklisted(device_serial)

        # Determine action
        blacklisted = False
        warning = False
        reason = None

        if count_24h >= self.BLACKLIST_THRESHOLD and not already_blacklisted:
            # Auto-blacklist
            reason = f"Exceeded daily limit: {count_24h} submissions in 24h"
            self.device_registry.blacklist_device(
                device_serial=device_serial,
                reason=reason
            )
            blacklisted = True

            print(f"⚠ AUTO-BLACKLIST: {device_serial}")
            print(f"  Count: {count_24h} submissions/24h")
            print(f"  Threshold: {self.BLACKLIST_THRESHOLD}")

        elif count_24h >= self.WARNING_THRESHOLD and not already_blacklisted:
            # Warning (no action, just log)
            warning = True
            reason = f"Approaching limit: {count_24h} submissions in 24h"

            print(f"⚠ WARNING: {device_serial}")
            print(f"  Count: {count_24h} submissions/24h")
            print(f"  Warning threshold: {self.WARNING_THRESHOLD}")
            print(f"  Blacklist threshold: {self.BLACKLIST_THRESHOLD}")

        return AbuseDetectionResult(
            device_serial=device_serial,
            submission_count_24h=count_24h,
            blacklisted=blacklisted,
            warning=warning,
            reason=reason
        )

    def check_all_devices(self) -> List[AbuseDetectionResult]:
        """
        Check all devices for abuse (daily cron job).

        Returns:
            List of results for devices with warnings or blacklists
        """
        print(f"\n{'='*60}")
        print(f"Running automated abuse detection check")
        print(f"Time: {datetime.utcnow().isoformat()}")
        print(f"Thresholds: Warning={self.WARNING_THRESHOLD}, Blacklist={self.BLACKLIST_THRESHOLD}")
        print(f"{'='*60}\n")

        # Get all devices that have submissions
        device_serials = self.submission_logger.get_all_device_serials()

        results = []
        blacklist_count = 0
        warning_count = 0

        for device_serial in device_serials:
            result = self.check_device_abuse(device_serial)

            # Only include results with action taken
            if result.blacklisted or result.warning:
                results.append(result)

                if result.blacklisted:
                    blacklist_count += 1
                if result.warning:
                    warning_count += 1

        print(f"\n{'='*60}")
        print(f"Abuse detection check complete")
        print(f"  Devices checked: {len(device_serials)}")
        print(f"  Warnings issued: {warning_count}")
        print(f"  Auto-blacklisted: {blacklist_count}")
        print(f"{'='*60}\n")

        return results

    def get_top_submitters(
        self,
        limit: int = 20
    ) -> List[Tuple[str, int, bool]]:
        """
        Get devices with highest submission counts.

        Args:
            limit: Number of results

        Returns:
            List of (device_serial, count, is_blacklisted) tuples
        """
        top_submitters = self.submission_logger.get_top_submitters(
            hours=self.TIME_WINDOW_HOURS,
            limit=limit
        )

        results = []
        for device_serial, count in top_submitters:
            is_blacklisted = self.device_registry.is_device_blacklisted(device_serial)
            results.append((device_serial, count, is_blacklisted))

        return results

    def get_abuse_report(self) -> Dict:
        """
        Generate comprehensive abuse detection report.

        Returns:
            Dictionary with abuse detection statistics
        """
        device_serials = self.submission_logger.get_all_device_serials()

        # Count devices in each category
        clean_devices = 0
        warning_devices = 0
        blacklisted_devices = 0

        for device_serial in device_serials:
            count_24h = self.submission_logger.count_submissions(
                device_serial,
                hours=self.TIME_WINDOW_HOURS
            )

            if self.device_registry.is_device_blacklisted(device_serial):
                blacklisted_devices += 1
            elif count_24h >= self.WARNING_THRESHOLD:
                warning_devices += 1
            else:
                clean_devices += 1

        # Get top submitters
        top_submitters = self.get_top_submitters(limit=10)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_devices": len(device_serials),
            "clean_devices": clean_devices,
            "warning_devices": warning_devices,
            "blacklisted_devices": blacklisted_devices,
            "thresholds": {
                "warning": self.WARNING_THRESHOLD,
                "blacklist": self.BLACKLIST_THRESHOLD,
                "time_window_hours": self.TIME_WINDOW_HOURS
            },
            "top_submitters": [
                {
                    "device_serial": serial,
                    "count_24h": count,
                    "is_blacklisted": blacklisted
                }
                for serial, count, blacklisted in top_submitters
            ]
        }


def run_daily_abuse_check(
    submission_logger: SubmissionLogger,
    device_registry: DeviceRegistry,
    save_registries: bool = True
) -> List[AbuseDetectionResult]:
    """
    Convenience function for daily cron job.

    Args:
        submission_logger: Submission log tracker
        device_registry: Device registration database
        save_registries: Save registries after blacklisting (default: True)

    Returns:
        List of abuse detection results
    """
    detector = AbuseDetector(submission_logger, device_registry)
    results = detector.check_all_devices()

    # Save registries if any blacklists occurred
    if save_registries and any(r.blacklisted for r in results):
        device_registry.save_to_file()
        print("✓ Saved updated device registry")

    return results


def check_single_device_abuse(
    device_serial: str,
    submission_logger: SubmissionLogger,
    device_registry: DeviceRegistry
) -> AbuseDetectionResult:
    """
    Check single device for abuse (for API endpoints).

    Args:
        device_serial: Device to check
        submission_logger: Submission log tracker
        device_registry: Device registration database

    Returns:
        AbuseDetectionResult
    """
    detector = AbuseDetector(submission_logger, device_registry)
    return detector.check_device_abuse(device_serial)
