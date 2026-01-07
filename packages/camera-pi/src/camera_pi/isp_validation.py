# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
ISP Validation using Variance-From-Expected Transformation

This module validates that ISP (Image Signal Processor) operations match their
declared parameters by computing the variance between actual transformations
and expected transformations.

This approach is more sensitive than measuring absolute transformation magnitude:
- Allows legitimate extreme processing (e.g., astrophotography noise reduction)
- Detects subtle unauthorized changes
- Tighter thresholds possible (0.15 vs 0.35)

Metric Version: v2.0 (Variance-From-Expected)
"""

import numpy as np
import cv2
from hashlib import sha256
from typing import Dict, Optional, Tuple
import random


def compute_variance_from_expected(
    raw_image: np.ndarray,
    processed_image: np.ndarray,
    isp_parameters: Dict,
    num_samples: int = 100,
    patch_size: int = 64
) -> float:
    """
    Computes variance between actual transformations and expected transformations
    based on declared ISP parameters.

    Args:
        raw_image: Raw Bayer data from sensor (height x width, uint16)
        processed_image: ISP-processed RGB image (height x width x 3, uint8)
        isp_parameters: Dict of applied operations:
            {
                'white_balance': {'red_gain': 1.3, 'blue_gain': 1.1},
                'exposure_adjustment': 0.3,  # stops
                'sharpening': 0.5,  # 0-1 scale
                'noise_reduction': 0.3  # 0-1 scale
            }
        num_samples: Number of random patches to sample
        patch_size: Size of each square patch

    Returns:
        float: Variance metric in range [0, 1]
               0.0-0.1 = minimal variance (ISP behaving as expected)
               0.1-0.2 = acceptable variance (minor artifacts)
               0.2+ = excessive variance (potential manipulation)
    """
    # Seed random generator with raw image hash for deterministic sampling
    raw_hash = sha256(raw_image.tobytes()).digest()
    random.seed(int.from_bytes(raw_hash[:4], 'big'))

    # Convert raw Bayer to RGB for comparison
    raw_rgb = debayer_raw_image(raw_image)

    # Ensure images are same size (may need alignment)
    if raw_rgb.shape != processed_image.shape:
        # Resize if needed
        processed_image = cv2.resize(
            processed_image,
            (raw_rgb.shape[1], raw_rgb.shape[0])
        )

    variances = []

    for i in range(num_samples):
        # Random patch location
        max_x = raw_rgb.shape[1] - patch_size
        max_y = raw_rgb.shape[0] - patch_size

        if max_x <= 0 or max_y <= 0:
            # Image too small for patch
            continue

        x = random.randint(0, max_x)
        y = random.randint(0, max_y)

        # Extract patches
        raw_patch = raw_rgb[y:y+patch_size, x:x+patch_size].copy()
        processed_patch = processed_image[y:y+patch_size, x:x+patch_size].copy()

        # Compute expected transformation for this patch
        expected_patch = apply_expected_transforms(raw_patch, isp_parameters)

        # Compute variance between actual and expected
        patch_variance = compute_patch_variance(
            processed_patch,
            expected_patch,
            isp_parameters
        )

        variances.append(patch_variance)

    if not variances:
        return 0.0

    # Return 95th percentile (robust to outliers)
    return float(np.percentile(variances, 95))


def debayer_raw_image(raw_bayer: np.ndarray) -> np.ndarray:
    """
    Convert raw Bayer data to RGB using simple demosaicing.

    Args:
        raw_bayer: Raw Bayer array (height x width, uint16)

    Returns:
        RGB image (height x width x 3, uint8)
    """
    # Normalize 10-bit to 8-bit
    if raw_bayer.max() > 255:
        normalized = (raw_bayer / 4).astype(np.uint8)  # 10-bit to 8-bit
    else:
        normalized = raw_bayer.astype(np.uint8)

    # Simple Bayer RGGB demosaicing using OpenCV
    # Assume RGGB pattern (most common)
    try:
        rgb = cv2.cvtColor(normalized, cv2.COLOR_BAYER_RGGB2RGB)
    except:
        # If conversion fails, create grayscale RGB
        rgb = np.stack([normalized, normalized, normalized], axis=-1)

    return rgb


def apply_expected_transforms(
    raw_patch: np.ndarray,
    isp_parameters: Dict
) -> np.ndarray:
    """
    Apply declared ISP operations to raw patch to get expected result.

    This simulates what the ISP should have produced given its declared parameters.

    Args:
        raw_patch: Raw RGB patch (patch_size x patch_size x 3, uint8)
        isp_parameters: Declared ISP operations

    Returns:
        Expected transformed patch (patch_size x patch_size x 3, uint8)
    """
    patch = raw_patch.astype(np.float32)

    # Apply white balance
    if 'white_balance' in isp_parameters:
        wb = isp_parameters['white_balance']
        patch[:,:,0] *= wb.get('red_gain', 1.0)
        patch[:,:,2] *= wb.get('blue_gain', 1.0)

    # Apply exposure adjustment (stops to multiplier: 2^stops)
    if 'exposure_adjustment' in isp_parameters:
        exposure_stops = isp_parameters['exposure_adjustment']
        multiplier = 2 ** exposure_stops
        patch = patch * multiplier

    # Apply noise reduction (simplified - Gaussian blur as proxy)
    if 'noise_reduction' in isp_parameters:
        nr_strength = isp_parameters['noise_reduction']
        # Kernel size based on NR strength
        kernel_size = int(3 + (nr_strength * 4))
        if kernel_size % 2 == 0:
            kernel_size += 1
        kernel_size = min(kernel_size, 11)  # Cap at 11x11

        if kernel_size >= 3:
            patch = cv2.GaussianBlur(
                patch,
                (kernel_size, kernel_size),
                sigmaX=0
            )

    # Apply sharpening
    if 'sharpening' in isp_parameters:
        sharp_strength = isp_parameters['sharpening']
        if sharp_strength > 0:
            # Unsharp mask
            kernel = np.array([
                [-1, -1, -1],
                [-1,  9, -1],
                [-1, -1, -1]
            ], dtype=np.float32) * sharp_strength

            patch = cv2.filter2D(patch, -1, kernel)

    # Clip to valid range
    patch = np.clip(patch, 0, 255)

    return patch.astype(np.uint8)


def compute_patch_variance(
    actual_patch: np.ndarray,
    expected_patch: np.ndarray,
    isp_parameters: Dict
) -> float:
    """
    Compute variance between actual and expected patches.

    Returns normalized variance score [0, 1].

    Args:
        actual_patch: Actual ISP-processed patch
        expected_patch: Expected patch based on declared parameters
        isp_parameters: Declared ISP parameters

    Returns:
        Variance score [0, 1]
    """
    # Component variances
    wb_variance = compute_wb_variance(actual_patch, expected_patch, isp_parameters)
    exposure_variance = compute_exposure_variance(actual_patch, expected_patch)
    sharpening_variance = compute_sharpening_variance(actual_patch, expected_patch)
    nr_variance = compute_nr_variance(actual_patch, expected_patch)

    # Weighted combination
    total_variance = (
        0.3 * wb_variance +
        0.3 * exposure_variance +
        0.2 * sharpening_variance +
        0.2 * nr_variance
    )

    return min(total_variance, 1.0)


def compute_wb_variance(
    actual: np.ndarray,
    expected: np.ndarray,
    isp_params: Dict
) -> float:
    """
    White balance variance: color shift difference.

    Args:
        actual: Actual patch
        expected: Expected patch
        isp_params: ISP parameters

    Returns:
        Variance score [0, 1]
    """
    if 'white_balance' not in isp_params:
        return 0.0

    # Compute mean color for each channel
    actual_mean = np.mean(actual, axis=(0,1))
    expected_mean = np.mean(expected, axis=(0,1))

    # Normalized absolute difference
    color_diff = np.mean(np.abs(actual_mean - expected_mean)) / 255.0

    return float(color_diff)


def compute_exposure_variance(actual: np.ndarray, expected: np.ndarray) -> float:
    """
    Exposure variance: brightness difference.

    Args:
        actual: Actual patch
        expected: Expected patch

    Returns:
        Variance score [0, 1]
    """
    actual_brightness = np.mean(actual)
    expected_brightness = np.mean(expected)

    brightness_diff = abs(actual_brightness - expected_brightness) / 255.0

    return float(brightness_diff)


def compute_sharpening_variance(actual: np.ndarray, expected: np.ndarray) -> float:
    """
    Sharpening variance: edge strength difference.

    Args:
        actual: Actual patch
        expected: Expected patch

    Returns:
        Variance score [0, 1]
    """
    actual_edges = compute_edge_strength(actual)
    expected_edges = compute_edge_strength(expected)

    edge_diff = abs(actual_edges - expected_edges)

    return float(edge_diff)


def compute_nr_variance(actual: np.ndarray, expected: np.ndarray) -> float:
    """
    Noise reduction variance: variance/std difference.

    Args:
        actual: Actual patch
        expected: Expected patch

    Returns:
        Variance score [0, 1]
    """
    actual_std = np.std(actual)
    expected_std = np.std(expected)

    std_diff = abs(actual_std - expected_std) / 255.0

    return float(std_diff)


def compute_edge_strength(image: np.ndarray) -> float:
    """
    Compute normalized edge strength using Sobel operator.

    Args:
        image: Image patch (RGB or grayscale)

    Returns:
        Edge strength [0, 1]
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image

    # Compute gradients
    grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)

    # Edge magnitude
    magnitude = np.sqrt(grad_x**2 + grad_y**2)

    # Normalize
    edge_strength = np.mean(magnitude) / 255.0

    return float(edge_strength)


def validate_isp_parameters(isp_params: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate that ISP parameters are within acceptable ranges.

    Prevents cameras from declaring extreme parameters to justify high variance.

    Args:
        isp_params: ISP parameters dict

    Returns:
        Tuple of (is_valid, error_message)
    """
    # White balance limits (typical range: 0.5x to 2.0x)
    if 'white_balance' in isp_params:
        wb = isp_params['white_balance']
        red_gain = wb.get('red_gain', 1.0)
        blue_gain = wb.get('blue_gain', 1.0)

        if red_gain < 0.5 or red_gain > 2.0:
            return False, f"Invalid red_gain: {red_gain} (must be 0.5-2.0)"
        if blue_gain < 0.5 or blue_gain > 2.0:
            return False, f"Invalid blue_gain: {blue_gain} (must be 0.5-2.0)"

    # Exposure limits (typical range: -2 to +2 stops)
    if 'exposure_adjustment' in isp_params:
        exposure = isp_params['exposure_adjustment']
        if exposure < -2.0 or exposure > 2.0:
            return False, f"Invalid exposure: {exposure} (must be -2.0 to +2.0 stops)"

    # Sharpening limits (0 to 1.0)
    if 'sharpening' in isp_params:
        sharp = isp_params['sharpening']
        if sharp < 0.0 or sharp > 1.0:
            return False, f"Invalid sharpening: {sharp} (must be 0.0-1.0)"

    # Noise reduction limits (0 to 1.0)
    if 'noise_reduction' in isp_params:
        nr = isp_params['noise_reduction']
        if nr < 0.0 or nr > 1.0:
            return False, f"Invalid noise_reduction: {nr} (must be 0.0-1.0)"

    return True, None


def create_isp_validation_data(
    raw_image: np.ndarray,
    processed_image: np.ndarray,
    isp_parameters: Dict,
    shooting_mode: str = "standard",
    num_samples: int = 100
) -> Dict:
    """
    Create ISP validation data structure for manufacturer certificate.

    Args:
        raw_image: Raw Bayer data
        processed_image: Processed RGB image
        isp_parameters: ISP parameters used
        shooting_mode: Shooting mode (standard, vivid, neutral)
        num_samples: Number of patches to sample

    Returns:
        Dict suitable for manufacturer_cert['isp_validation']
    """
    # Validate parameters
    params_valid, error = validate_isp_parameters(isp_parameters)
    if not params_valid:
        raise ValueError(f"Invalid ISP parameters: {error}")

    # Compute variance metric
    variance_metric = compute_variance_from_expected(
        raw_image,
        processed_image,
        isp_parameters,
        num_samples=num_samples
    )

    return {
        "variance_metric": variance_metric,
        "isp_parameters": isp_parameters,
        "sample_count": num_samples,
        "shooting_mode": shooting_mode,
        "metric_version": "v2.0"
    }


if __name__ == "__main__":
    """
    Example usage and testing.
    """
    print("=== ISP Validation Test ===\n")

    # Create synthetic test data
    print("Creating test images...")
    raw_bayer = np.random.randint(0, 1024, (304, 405), dtype=np.uint16)

    # Simulate ISP processing
    raw_rgb = debayer_raw_image(raw_bayer)

    # Simulate ISP with known parameters
    isp_params = {
        'white_balance': {'red_gain': 1.25, 'blue_gain': 1.15},
        'exposure_adjustment': 0.5,
        'sharpening': 0.5,
        'noise_reduction': 0.3
    }

    processed = apply_expected_transforms(raw_rgb, isp_params)

    # Add small noise to simulate real ISP
    noise = np.random.normal(0, 5, processed.shape)
    processed = np.clip(processed.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    print("Computing variance from expected...")
    variance = compute_variance_from_expected(
        raw_bayer,
        processed,
        isp_params,
        num_samples=50
    )

    print(f"\nResults:")
    print(f"  ISP Parameters: {isp_params}")
    print(f"  Variance metric: {variance:.4f}")
    print(f"  Status: {'PASS' if variance < 0.15 else 'FAIL'} (threshold: 0.15)")

    # Test parameter validation
    print("\nTesting parameter validation...")
    valid, error = validate_isp_parameters(isp_params)
    print(f"  Valid: {valid}")

    # Test invalid parameters
    invalid_params = {'exposure_adjustment': 3.0}  # Too high
    valid, error = validate_isp_parameters(invalid_params)
    print(f"  Invalid params test: {error}")
