"""
ISP Validation for SMA

Validates ISP transformation data from camera submissions using variance-from-expected
metrics. This module verifies that:
1. ISP parameters are within acceptable ranges
2. Variance metrics are below thresholds
3. Metric versions are supported
4. Shooting modes are valid for device family

Related to camera-pi/src/camera_pi/isp_validation.py
"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import sys
from pathlib import Path

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    get_variance_threshold,
    validate_isp_parameters,
    is_metric_version_supported,
    is_shooting_mode_supported,
    ANOMALY_THRESHOLDS
)


@dataclass
class ISPValidationResult:
    """Result of ISP validation check."""
    is_valid: bool
    reason: Optional[str]
    variance_metric: Optional[float]
    threshold: Optional[float]
    flags: list[str]  # Anomaly flags


def validate_isp_submission(
    isp_validation_data: Optional[Dict],
    device_family: str,
    device_serial: str
) -> ISPValidationResult:
    """
    Validate ISP transformation data from camera submission.

    Args:
        isp_validation_data: ISP validation dict from submission
        device_family: Device family (e.g., "RASPBERRY_PI_HQ")
        device_serial: Device serial for logging

    Returns:
        ISPValidationResult with validation outcome and flags
    """
    flags = []

    # Check if ISP validation data is present
    if not isp_validation_data:
        return ISPValidationResult(
            is_valid=False,
            reason="MISSING_ISP_VALIDATION",
            variance_metric=None,
            threshold=None,
            flags=["missing_isp_data"]
        )

    # Check metric version
    metric_version = isp_validation_data.get('metric_version')
    if not metric_version:
        return ISPValidationResult(
            is_valid=False,
            reason="MISSING_METRIC_VERSION",
            variance_metric=None,
            threshold=None,
            flags=["missing_version"]
        )

    if not is_metric_version_supported(metric_version):
        return ISPValidationResult(
            is_valid=False,
            reason=f"UNSUPPORTED_METRIC_VERSION: {metric_version}",
            variance_metric=None,
            threshold=None,
            flags=["unsupported_version"]
        )

    # Get shooting mode
    shooting_mode = isp_validation_data.get('shooting_mode', 'standard')

    # Validate shooting mode for device family
    if not is_shooting_mode_supported(device_family, shooting_mode):
        return ISPValidationResult(
            is_valid=False,
            reason=f"UNSUPPORTED_SHOOTING_MODE: {shooting_mode} for {device_family}",
            variance_metric=None,
            threshold=None,
            flags=["unsupported_mode"]
        )

    # Validate ISP parameters
    isp_parameters = isp_validation_data.get('isp_parameters', {})
    params_valid, param_error = validate_isp_parameters(isp_parameters, device_family)

    if not params_valid:
        return ISPValidationResult(
            is_valid=False,
            reason=f"INVALID_ISP_PARAMETERS: {param_error}",
            variance_metric=None,
            threshold=None,
            flags=["invalid_parameters"]
        )

    # Check variance metric
    variance_metric = isp_validation_data.get('variance_metric')
    if variance_metric is None:
        return ISPValidationResult(
            is_valid=False,
            reason="MISSING_VARIANCE_METRIC",
            variance_metric=None,
            threshold=None,
            flags=["missing_metric"]
        )

    # Get threshold for device and mode
    try:
        threshold = get_variance_threshold(device_family, shooting_mode)
    except ValueError as e:
        return ISPValidationResult(
            is_valid=False,
            reason=f"THRESHOLD_ERROR: {e}",
            variance_metric=variance_metric,
            threshold=None,
            flags=["threshold_error"]
        )

    # Check for extreme variance (anomaly detection)
    extreme_threshold = threshold * ANOMALY_THRESHOLDS['extreme_multiplier']
    if variance_metric > extreme_threshold:
        flags.append("extreme_variance")

    # Validate variance against threshold
    if variance_metric > threshold:
        return ISPValidationResult(
            is_valid=False,
            reason="EXCESSIVE_VARIANCE",
            variance_metric=variance_metric,
            threshold=threshold,
            flags=flags + ["excessive_variance"]
        )

    # Check for suspicious parameter patterns
    if _has_suspicious_parameters(isp_parameters):
        flags.append("suspicious_parameters")

    # All checks passed
    return ISPValidationResult(
        is_valid=True,
        reason=None,
        variance_metric=variance_metric,
        threshold=threshold,
        flags=flags
    )


def _has_suspicious_parameters(isp_params: Dict) -> bool:
    """
    Check for suspicious parameter combinations.

    Args:
        isp_params: ISP parameters dictionary

    Returns:
        True if parameters look suspicious
    """
    # Check for consistently extreme parameters
    extreme_count = 0

    # Extreme white balance (far from neutral)
    if 'white_balance' in isp_params:
        wb = isp_params['white_balance']
        red_gain = wb.get('red_gain', 1.0)
        blue_gain = wb.get('blue_gain', 1.0)

        if red_gain > 1.8 or red_gain < 0.6:
            extreme_count += 1
        if blue_gain > 1.8 or blue_gain < 0.6:
            extreme_count += 1

    # Extreme exposure
    if 'exposure_adjustment' in isp_params:
        exposure = abs(isp_params['exposure_adjustment'])
        if exposure > 1.5:  # More than 1.5 stops
            extreme_count += 1

    # Very high noise reduction
    if 'noise_reduction' in isp_params:
        nr = isp_params['noise_reduction']
        if nr > 0.8:  # Very aggressive NR
            extreme_count += 1

    # If 2+ extreme parameters, flag as suspicious
    return extreme_count >= 2


def format_validation_response(result: ISPValidationResult) -> Dict:
    """
    Format ISP validation result as API response.

    Args:
        result: ISPValidationResult

    Returns:
        Dictionary for API response
    """
    response = {
        "status": "PASS" if result.is_valid else "FAIL",
        "isp_validation": {
            "variance_metric": result.variance_metric,
            "threshold": result.threshold,
            "flags": result.flags
        }
    }

    if not result.is_valid:
        response["reason"] = result.reason

    return response


def log_validation_metrics(
    device_serial: str,
    result: ISPValidationResult,
    isp_parameters: Dict
) -> None:
    """
    Log validation metrics for monitoring and anomaly detection.

    Args:
        device_serial: Device identifier
        result: Validation result
        isp_parameters: ISP parameters used
    """
    # This would integrate with submission_logger or a separate metrics system
    print(f"[ISP Validation] Device: {device_serial}")
    print(f"  Result: {result.is_valid}")
    print(f"  Variance: {result.variance_metric:.4f}" if result.variance_metric else "  Variance: None")
    print(f"  Threshold: {result.threshold:.4f}" if result.threshold else "  Threshold: None")

    if result.flags:
        print(f"  Flags: {', '.join(result.flags)}")

    if result.reason:
        print(f"  Reason: {result.reason}")


# Example usage
if __name__ == "__main__":
    print("=== ISP Validator Test ===\n")

    # Test 1: Valid submission
    print("Test 1: Valid submission")
    isp_data_valid = {
        "variance_metric": 0.08,
        "isp_parameters": {
            "white_balance": {"red_gain": 1.25, "blue_gain": 1.15},
            "exposure_adjustment": 0.5,
            "sharpening": 0.5,
            "noise_reduction": 0.3
        },
        "sample_count": 100,
        "shooting_mode": "standard",
        "metric_version": "v2.0"
    }

    result = validate_isp_submission(isp_data_valid, "RASPBERRY_PI_HQ", "TEST-001")
    print(f"  Valid: {result.is_valid}")
    print(f"  Variance: {result.variance_metric:.4f}, Threshold: {result.threshold:.4f}")
    print(f"  Flags: {result.flags}\n")

    # Test 2: Excessive variance
    print("Test 2: Excessive variance")
    isp_data_excessive = {
        "variance_metric": 0.25,  # Above 0.15 threshold
        "isp_parameters": {
            "white_balance": {"red_gain": 1.2, "blue_gain": 1.1},
            "exposure_adjustment": 0.3,
            "sharpening": 0.5,
            "noise_reduction": 0.3
        },
        "sample_count": 100,
        "shooting_mode": "standard",
        "metric_version": "v2.0"
    }

    result = validate_isp_submission(isp_data_excessive, "RASPBERRY_PI_HQ", "TEST-002")
    print(f"  Valid: {result.is_valid}")
    print(f"  Reason: {result.reason}")
    print(f"  Flags: {result.flags}\n")

    # Test 3: Invalid parameters
    print("Test 3: Invalid parameters")
    isp_data_invalid = {
        "variance_metric": 0.08,
        "isp_parameters": {
            "white_balance": {"red_gain": 3.0, "blue_gain": 1.1},  # red_gain too high
            "exposure_adjustment": 0.5,
            "sharpening": 0.5,
            "noise_reduction": 0.3
        },
        "sample_count": 100,
        "shooting_mode": "standard",
        "metric_version": "v2.0"
    }

    result = validate_isp_submission(isp_data_invalid, "RASPBERRY_PI_HQ", "TEST-003")
    print(f"  Valid: {result.is_valid}")
    print(f"  Reason: {result.reason}\n")

    # Test 4: Missing data
    print("Test 4: Missing ISP validation data")
    result = validate_isp_submission(None, "RASPBERRY_PI_HQ", "TEST-004")
    print(f"  Valid: {result.is_valid}")
    print(f"  Reason: {result.reason}")
