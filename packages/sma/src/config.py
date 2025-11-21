"""
SMA Configuration

Configuration settings for the Simulated Manufacturer Authority including
ISP validation thresholds and anomaly detection parameters.
"""

# ISP Variance Thresholds (Variance-From-Expected v2.0)
# Much tighter thresholds than previous transformation magnitude approach
ISP_VARIANCE_THRESHOLDS = {
    "RASPBERRY_PI_HQ": {
        "standard": 0.15,  # Standard photography mode
        "vivid": 0.20,     # Vivid color mode (more processing)
        "neutral": 0.10    # Minimal processing mode
    },
    "IOS_DEVICE": {  # Phase 2
        "standard": 0.18,
        "portrait": 0.22,
        "night": 0.25
    }
}

# Anomaly Detection Thresholds
ANOMALY_THRESHOLDS = {
    # Variance metric anomalies
    "extreme_multiplier": 2.0,  # Flag if variance > threshold * 2.0
    "high_failure_rate": 0.15,  # 15% failure rate triggers investigation
    "critical_failure_rate": 0.30,  # 30% failure rate triggers auto-blacklist consideration

    # Auto-flagging for extreme values
    "auto_flag_extreme_count": 3,  # Auto-flag after 3 extreme variance submissions
    "extreme_lookback_hours": 24,  # Look back 24 hours for extreme submissions

    # Parameter manipulation detection
    "suspicious_param_consistency": 0.9,  # Flag if 90%+ submissions use same extreme params
    "param_analysis_window": 50,  # Analyze last 50 submissions for patterns
}

# Abuse Detection Thresholds (from existing abuse_detection.py)
ABUSE_THRESHOLDS = {
    "daily_submission_limit": 10_000,  # Auto-blacklist at 10k/day
    "daily_warning_threshold": 8_000,  # Warning at 8k/day
    "time_window_hours": 24
}

# ISP Parameter Validation Ranges
ISP_PARAMETER_LIMITS = {
    "white_balance": {
        "red_gain": {"min": 0.5, "max": 2.0},
        "blue_gain": {"min": 0.5, "max": 2.0},
        "green_gain": {"min": 0.5, "max": 2.0}  # Optional
    },
    "exposure_adjustment": {
        "min": -2.0,  # -2 stops
        "max": 2.0    # +2 stops
    },
    "sharpening": {
        "min": 0.0,
        "max": 1.0
    },
    "noise_reduction": {
        "min": 0.0,
        "max": 1.0
    },
    "contrast": {  # Optional
        "min": 0.5,
        "max": 1.5
    },
    "saturation": {  # Optional
        "min": 0.0,
        "max": 2.0
    }
}

# Supported Metric Versions
SUPPORTED_METRIC_VERSIONS = ["v2.0"]

# Supported Shooting Modes by Device Family
SUPPORTED_SHOOTING_MODES = {
    "RASPBERRY_PI_HQ": ["standard", "vivid", "neutral"],
    "IOS_DEVICE": ["standard", "portrait", "night", "vivid"]
}

def get_variance_threshold(device_family: str, shooting_mode: str = "standard") -> float:
    """
    Get variance threshold for device and shooting mode.

    Args:
        device_family: Device family (e.g., "RASPBERRY_PI_HQ")
        shooting_mode: Shooting mode (e.g., "standard")

    Returns:
        Variance threshold (0.0-1.0)

    Raises:
        ValueError: If device family or shooting mode is unsupported
    """
    if device_family not in ISP_VARIANCE_THRESHOLDS:
        raise ValueError(f"Unsupported device family: {device_family}")

    thresholds = ISP_VARIANCE_THRESHOLDS[device_family]

    if shooting_mode not in thresholds:
        # Fall back to standard mode
        return thresholds.get("standard", 0.15)

    return thresholds[shooting_mode]


def validate_isp_parameters(isp_params: dict, device_family: str) -> tuple[bool, str | None]:
    """
    Validate ISP parameters are within acceptable ranges.

    Prevents devices from declaring extreme parameters to justify high variance.

    Args:
        isp_params: ISP parameters dictionary
        device_family: Device family for context

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isp_params:
        return True, None

    # White balance validation
    if 'white_balance' in isp_params:
        wb = isp_params['white_balance']
        limits = ISP_PARAMETER_LIMITS['white_balance']

        for channel in ['red_gain', 'blue_gain', 'green_gain']:
            if channel in wb:
                value = wb[channel]
                if value < limits[channel]['min'] or value > limits[channel]['max']:
                    return False, f"Invalid {channel}: {value} (must be {limits[channel]['min']}-{limits[channel]['max']})"

    # Exposure validation
    if 'exposure_adjustment' in isp_params:
        exposure = isp_params['exposure_adjustment']
        limits = ISP_PARAMETER_LIMITS['exposure_adjustment']
        if exposure < limits['min'] or exposure > limits['max']:
            return False, f"Invalid exposure: {exposure} (must be {limits['min']} to {limits['max']} stops)"

    # Sharpening validation
    if 'sharpening' in isp_params:
        sharp = isp_params['sharpening']
        limits = ISP_PARAMETER_LIMITS['sharpening']
        if sharp < limits['min'] or sharp > limits['max']:
            return False, f"Invalid sharpening: {sharp} (must be {limits['min']}-{limits['max']})"

    # Noise reduction validation
    if 'noise_reduction' in isp_params:
        nr = isp_params['noise_reduction']
        limits = ISP_PARAMETER_LIMITS['noise_reduction']
        if nr < limits['min'] or nr > limits['max']:
            return False, f"Invalid noise_reduction: {nr} (must be {limits['min']}-{limits['max']})"

    # Contrast validation (optional)
    if 'contrast' in isp_params:
        contrast = isp_params['contrast']
        limits = ISP_PARAMETER_LIMITS['contrast']
        if contrast < limits['min'] or contrast > limits['max']:
            return False, f"Invalid contrast: {contrast} (must be {limits['min']}-{limits['max']})"

    # Saturation validation (optional)
    if 'saturation' in isp_params:
        saturation = isp_params['saturation']
        limits = ISP_PARAMETER_LIMITS['saturation']
        if saturation < limits['min'] or saturation > limits['max']:
            return False, f"Invalid saturation: {saturation} (must be {limits['min']}-{limits['max']})"

    return True, None


def is_metric_version_supported(version: str) -> bool:
    """Check if metric version is supported."""
    return version in SUPPORTED_METRIC_VERSIONS


def is_shooting_mode_supported(device_family: str, shooting_mode: str) -> bool:
    """Check if shooting mode is supported for device family."""
    if device_family not in SUPPORTED_SHOOTING_MODES:
        return False
    return shooting_mode in SUPPORTED_SHOOTING_MODES[device_family]
