# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
ISP Anomaly Detection

Monitors ISP validation patterns to detect suspicious behavior:
- Cameras consistently failing validation
- Cameras using extreme parameters to justify high variance
- Unusual parameter patterns indicating manipulation attempts
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import json


@dataclass
class ISPSubmissionRecord:
    """Record of a single ISP validation submission."""
    device_serial: str
    timestamp: datetime
    variance_metric: float
    threshold: float
    passed: bool
    isp_parameters: Dict
    flags: List[str]


class ISPAnomalyDetector:
    """
    Detects anomalous ISP validation patterns.

    Monitors:
    - High failure rates
    - Extreme variance patterns
    - Suspicious parameter usage
    - Parameter manipulation attempts
    """

    def __init__(self):
        """Initialize anomaly detector with in-memory storage."""
        # In production, this would use database storage
        self.submissions: Dict[str, List[ISPSubmissionRecord]] = {}

    def record_submission(
        self,
        device_serial: str,
        variance_metric: float,
        threshold: float,
        passed: bool,
        isp_parameters: Dict,
        flags: List[str]
    ) -> None:
        """
        Record an ISP validation submission.

        Args:
            device_serial: Device identifier
            variance_metric: Computed variance metric
            threshold: Threshold used
            passed: Whether validation passed
            isp_parameters: ISP parameters used
            flags: Anomaly flags from validation
        """
        if device_serial not in self.submissions:
            self.submissions[device_serial] = []

        record = ISPSubmissionRecord(
            device_serial=device_serial,
            timestamp=datetime.utcnow(),
            variance_metric=variance_metric,
            threshold=threshold,
            passed=passed,
            isp_parameters=isp_parameters,
            flags=flags
        )

        self.submissions[device_serial].append(record)

        # Keep only recent submissions (last 30 days)
        cutoff = datetime.utcnow() - timedelta(days=30)
        self.submissions[device_serial] = [
            s for s in self.submissions[device_serial]
            if s.timestamp > cutoff
        ]

    def check_device_anomalies(
        self,
        device_serial: str,
        lookback_hours: int = 24
    ) -> Dict:
        """
        Check device for anomalous patterns.

        Args:
            device_serial: Device to check
            lookback_hours: Hours to look back

        Returns:
            Dictionary with anomaly findings
        """
        if device_serial not in self.submissions:
            return {
                "has_anomalies": False,
                "anomalies": [],
                "submission_count": 0
            }

        # Get recent submissions
        cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)
        recent = [s for s in self.submissions[device_serial] if s.timestamp > cutoff]

        if not recent:
            return {
                "has_anomalies": False,
                "anomalies": [],
                "submission_count": 0
            }

        anomalies = []

        # Check 1: High failure rate
        failure_count = sum(1 for s in recent if not s.passed)
        failure_rate = failure_count / len(recent)

        if failure_rate > 0.30:  # 30% failure rate
            anomalies.append({
                "type": "high_failure_rate",
                "severity": "critical",
                "details": f"Failure rate: {failure_rate:.1%} ({failure_count}/{len(recent)})",
                "recommendation": "Consider blacklisting device"
            })
        elif failure_rate > 0.15:  # 15% failure rate
            anomalies.append({
                "type": "elevated_failure_rate",
                "severity": "warning",
                "details": f"Failure rate: {failure_rate:.1%} ({failure_count}/{len(recent)})",
                "recommendation": "Monitor device closely"
            })

        # Check 2: Extreme variance pattern
        extreme_count = sum(1 for s in recent if "extreme_variance" in s.flags)
        if extreme_count >= 3:
            anomalies.append({
                "type": "extreme_variance_pattern",
                "severity": "high",
                "details": f"{extreme_count} extreme variance submissions in {lookback_hours}h",
                "recommendation": "Investigate device or ISP configuration"
            })

        # Check 3: Suspicious parameter consistency
        param_anomaly = self._check_parameter_consistency(recent)
        if param_anomaly:
            anomalies.append(param_anomaly)

        # Check 4: Parameter manipulation attempts
        manipulation_anomaly = self._check_parameter_manipulation(recent)
        if manipulation_anomaly:
            anomalies.append(manipulation_anomaly)

        return {
            "has_anomalies": len(anomalies) > 0,
            "anomalies": anomalies,
            "submission_count": len(recent),
            "failure_rate": failure_rate,
            "extreme_count": extreme_count
        }

    def _check_parameter_consistency(self, submissions: List[ISPSubmissionRecord]) -> Optional[Dict]:
        """
        Check if device consistently uses extreme parameters.

        Args:
            submissions: List of recent submissions

        Returns:
            Anomaly dict if suspicious pattern found, None otherwise
        """
        if len(submissions) < 20:
            return None

        # Count submissions with suspicious parameters flag
        suspicious_count = sum(1 for s in submissions if "suspicious_parameters" in s.flags)
        suspicious_rate = suspicious_count / len(submissions)

        if suspicious_rate > 0.8:  # 80%+ submissions have suspicious params
            # Analyze what parameters are extreme
            extreme_params = self._analyze_extreme_parameters(submissions)

            return {
                "type": "suspicious_parameter_consistency",
                "severity": "high",
                "details": f"{suspicious_rate:.0%} of submissions use extreme parameters",
                "extreme_parameters": extreme_params,
                "recommendation": "Device may be manipulating parameters to justify high variance"
            }

        return None

    def _check_parameter_manipulation(self, submissions: List[ISPSubmissionRecord]) -> Optional[Dict]:
        """
        Check for parameter manipulation patterns.

        Looks for:
        - Parameters that increase just enough to justify variance
        - Correlation between variance and declared parameters

        Args:
            submissions: List of recent submissions

        Returns:
            Anomaly dict if manipulation suspected, None otherwise
        """
        if len(submissions) < 30:
            return None

        # Check for exposure manipulation pattern
        # Device declares higher exposure when variance is high
        high_variance = [s for s in submissions if s.variance_metric > s.threshold * 0.9]
        low_variance = [s for s in submissions if s.variance_metric < s.threshold * 0.5]

        if len(high_variance) < 5 or len(low_variance) < 5:
            return None

        # Average exposure for high vs low variance
        avg_exposure_high = sum(
            abs(s.isp_parameters.get('exposure_adjustment', 0))
            for s in high_variance
        ) / len(high_variance)

        avg_exposure_low = sum(
            abs(s.isp_parameters.get('exposure_adjustment', 0))
            for s in low_variance
        ) / len(low_variance)

        # If high variance submissions use significantly more exposure
        if avg_exposure_high > avg_exposure_low * 1.5:
            return {
                "type": "parameter_manipulation_suspected",
                "severity": "critical",
                "details": f"High variance submissions use {avg_exposure_high/avg_exposure_low:.1f}x more exposure",
                "recommendation": "Device may be declaring extreme parameters to justify high variance"
            }

        return None

    def _analyze_extreme_parameters(self, submissions: List[ISPSubmissionRecord]) -> Dict:
        """
        Analyze which parameters are consistently extreme.

        Args:
            submissions: List of submissions

        Returns:
            Dictionary of extreme parameter frequencies
        """
        extreme_wb = 0
        extreme_exposure = 0
        extreme_nr = 0
        extreme_sharp = 0

        for s in submissions:
            params = s.isp_parameters

            # White balance
            if 'white_balance' in params:
                wb = params['white_balance']
                red = wb.get('red_gain', 1.0)
                blue = wb.get('blue_gain', 1.0)
                if red > 1.7 or red < 0.6 or blue > 1.7 or blue < 0.6:
                    extreme_wb += 1

            # Exposure
            if 'exposure_adjustment' in params:
                if abs(params['exposure_adjustment']) > 1.5:
                    extreme_exposure += 1

            # Noise reduction
            if 'noise_reduction' in params:
                if params['noise_reduction'] > 0.7:
                    extreme_nr += 1

            # Sharpening
            if 'sharpening' in params:
                if params['sharpening'] > 0.8:
                    extreme_sharp += 1

        total = len(submissions)
        return {
            "white_balance": f"{extreme_wb/total:.0%}",
            "exposure": f"{extreme_exposure/total:.0%}",
            "noise_reduction": f"{extreme_nr/total:.0%}",
            "sharpening": f"{extreme_sharp/total:.0%}"
        }

    def get_device_statistics(self, device_serial: str, days: int = 7) -> Dict:
        """
        Get ISP validation statistics for device.

        Args:
            device_serial: Device identifier
            days: Number of days to analyze

        Returns:
            Statistics dictionary
        """
        if device_serial not in self.submissions:
            return {
                "total_submissions": 0,
                "pass_rate": 0.0,
                "avg_variance": 0.0,
                "extreme_count": 0
            }

        cutoff = datetime.utcnow() - timedelta(days=days)
        recent = [s for s in self.submissions[device_serial] if s.timestamp > cutoff]

        if not recent:
            return {
                "total_submissions": 0,
                "pass_rate": 0.0,
                "avg_variance": 0.0,
                "extreme_count": 0
            }

        pass_count = sum(1 for s in recent if s.passed)
        extreme_count = sum(1 for s in recent if "extreme_variance" in s.flags)
        avg_variance = sum(s.variance_metric for s in recent) / len(recent)

        return {
            "total_submissions": len(recent),
            "pass_rate": pass_count / len(recent),
            "avg_variance": avg_variance,
            "extreme_count": extreme_count,
            "days_analyzed": days
        }


# Example usage
if __name__ == "__main__":
    print("=== ISP Anomaly Detection Test ===\n")

    detector = ISPAnomalyDetector()

    # Simulate normal device
    print("Device 1: Normal operation")
    for i in range(50):
        detector.record_submission(
            device_serial="NORMAL-001",
            variance_metric=0.08,  # Well below threshold
            threshold=0.15,
            passed=True,
            isp_parameters={
                "white_balance": {"red_gain": 1.2, "blue_gain": 1.1},
                "exposure_adjustment": 0.3,
                "sharpening": 0.5,
                "noise_reduction": 0.3
            },
            flags=[]
        )

    result = detector.check_device_anomalies("NORMAL-001")
    print(f"  Anomalies: {result['has_anomalies']}")
    print(f"  Submissions: {result['submission_count']}")
    print(f"  Failure rate: {result['failure_rate']:.1%}\n")

    # Simulate suspicious device
    print("Device 2: High failure rate with suspicious parameters")
    for i in range(50):
        # Vary between passing and failing with suspicious params
        variance = 0.18 if i % 3 == 0 else 0.08  # 33% failure rate
        detector.record_submission(
            device_serial="SUSPICIOUS-002",
            variance_metric=variance,
            threshold=0.15,
            passed=(variance < 0.15),
            isp_parameters={
                "white_balance": {"red_gain": 1.85, "blue_gain": 1.82},  # Extreme
                "exposure_adjustment": 1.8,  # Extreme
                "sharpening": 0.5,
                "noise_reduction": 0.9  # Extreme
            },
            flags=["suspicious_parameters"] if i % 3 == 0 else []
        )

    result = detector.check_device_anomalies("SUSPICIOUS-002", lookback_hours=24)
    print(f"  Anomalies: {result['has_anomalies']}")
    print(f"  Submissions: {result['submission_count']}")
    print(f"  Failure rate: {result['failure_rate']:.1%}")

    if result['anomalies']:
        print(f"  Found {len(result['anomalies'])} anomalies:")
        for anomaly in result['anomalies']:
            print(f"    - {anomaly['type']}: {anomaly['severity']}")
            print(f"      {anomaly['details']}")
