# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Integration Test for ISP Variance-From-Expected Validation

Tests the complete flow:
1. Camera captures raw + processed images
2. Camera computes variance-from-expected metric
3. Camera includes ISP validation in bundle
4. SMA validates ISP parameters and variance threshold
5. SMA detects anomalies in parameter patterns

This demonstrates the new v2.0 variance-from-expected approach which is more
sensitive than the previous absolute transformation magnitude method.
"""

import sys
from pathlib import Path
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from camera_pi.isp_validation import (
    compute_variance_from_expected,
    validate_isp_parameters,
    create_isp_validation_data,
    debayer_raw_image,
    apply_expected_transforms
)


def test_normal_isp_processing():
    """Test 1: Normal ISP processing with low variance."""
    print("=" * 60)
    print("Test 1: Normal ISP Processing")
    print("=" * 60)

    # Create synthetic test data
    raw_bayer = np.random.randint(0, 1024, (304, 405), dtype=np.uint16)
    raw_rgb = debayer_raw_image(raw_bayer)

    # Define ISP parameters
    isp_params = {
        'white_balance': {'red_gain': 1.25, 'blue_gain': 1.15},
        'exposure_adjustment': 0.3,
        'sharpening': 0.5,
        'noise_reduction': 0.3
    }

    # Simulate ISP processing
    processed = apply_expected_transforms(raw_rgb, isp_params)

    # Add small realistic noise
    noise = np.random.normal(0, 3, processed.shape)
    processed = np.clip(processed.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    # Compute variance
    variance = compute_variance_from_expected(
        raw_bayer,
        processed,
        isp_params,
        num_samples=50
    )

    print(f"ISP Parameters: {isp_params}")
    print(f"Variance metric: {variance:.4f}")
    print(f"Threshold: 0.15 (standard mode)")
    print(f"Status: {'PASS ✓' if variance < 0.15 else 'FAIL ✗'}")
    print(f"Expected: PASS (normal processing should have low variance)\n")

    assert variance < 0.15, f"Normal processing should pass: variance={variance:.4f}"
    print("✓ Test 1 PASSED\n")


def test_extreme_but_declared_processing():
    """Test 2: Extreme processing that matches declared parameters."""
    print("=" * 60)
    print("Test 2: Extreme But Declared Processing")
    print("=" * 60)

    raw_bayer = np.random.randint(0, 1024, (304, 405), dtype=np.uint16)
    raw_rgb = debayer_raw_image(raw_bayer)

    # Declare extreme parameters
    isp_params = {
        'white_balance': {'red_gain': 1.8, 'blue_gain': 1.7},
        'exposure_adjustment': 1.5,  # Heavy exposure boost
        'sharpening': 0.8,
        'noise_reduction': 0.8  # Heavy noise reduction
    }

    # Apply those exact transforms
    processed = apply_expected_transforms(raw_rgb, isp_params)
    noise = np.random.normal(0, 5, processed.shape)
    processed = np.clip(processed.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    # Compute variance
    variance = compute_variance_from_expected(
        raw_bayer,
        processed,
        isp_params,
        num_samples=50
    )

    print(f"ISP Parameters (EXTREME): {isp_params}")
    print(f"Variance metric: {variance:.4f}")
    print(f"Threshold: 0.15 (standard mode)")
    print(f"Status: {'PASS ✓' if variance < 0.15 else 'FAIL ✗'}")
    print(f"Expected: PASS (extreme but matching declared parameters)\n")

    # Should still pass because it matches declared parameters
    assert variance < 0.20, f"Declared extreme processing should pass: variance={variance:.4f}"
    print("✓ Test 2 PASSED\n")


def test_unauthorized_manipulation():
    """Test 3: Unauthorized manipulation not matching declared params."""
    print("=" * 60)
    print("Test 3: Unauthorized Manipulation")
    print("=" * 60)

    raw_bayer = np.random.randint(0, 1024, (304, 405), dtype=np.uint16)
    raw_rgb = debayer_raw_image(raw_bayer)

    # Declare modest parameters
    isp_params = {
        'white_balance': {'red_gain': 1.2, 'blue_gain': 1.1},
        'exposure_adjustment': 0.3,
        'sharpening': 0.5,
        'noise_reduction': 0.3
    }

    # But apply very different transforms (simulating manipulation)
    processed = apply_expected_transforms(raw_rgb, isp_params)

    # Add significant content changes (manipulation)
    manipulation = np.random.uniform(-50, 50, processed.shape)
    processed = np.clip(processed.astype(np.float32) + manipulation, 0, 255).astype(np.uint8)

    # Compute variance
    variance = compute_variance_from_expected(
        raw_bayer,
        processed,
        isp_params,
        num_samples=50
    )

    print(f"Declared ISP Parameters (MODEST): {isp_params}")
    print(f"Actual Processing: Heavy manipulation applied")
    print(f"Variance metric: {variance:.4f}")
    print(f"Threshold: 0.15 (standard mode)")
    print(f"Status: {'PASS ✓' if variance < 0.15 else 'FAIL ✗'}")
    print(f"Expected: FAIL (manipulation not matching declared params)\n")

    assert variance > 0.15, f"Manipulation should be detected: variance={variance:.4f}"
    print("✓ Test 3 PASSED\n")


def test_parameter_validation():
    """Test 4: ISP parameter validation."""
    print("=" * 60)
    print("Test 4: ISP Parameter Validation")
    print("=" * 60)

    # Valid parameters
    valid_params = {
        'white_balance': {'red_gain': 1.5, 'blue_gain': 1.3},
        'exposure_adjustment': 1.0,
        'sharpening': 0.7,
        'noise_reduction': 0.5
    }

    valid, error = validate_isp_parameters(valid_params)
    print(f"Valid params: {valid_params}")
    print(f"  Result: {'VALID ✓' if valid else 'INVALID ✗'}")
    assert valid, f"Valid params should pass: {error}"

    # Invalid parameters (extreme red gain)
    invalid_params = {
        'white_balance': {'red_gain': 3.0, 'blue_gain': 1.1},  # Too high
        'exposure_adjustment': 0.5,
        'sharpening': 0.5,
        'noise_reduction': 0.3
    }

    valid, error = validate_isp_parameters(invalid_params)
    print(f"\nInvalid params: {invalid_params}")
    print(f"  Result: {'VALID ✓' if valid else 'INVALID ✗'}")
    print(f"  Error: {error}")
    assert not valid, "Invalid params should be rejected"

    # Invalid exposure
    invalid_exposure = {
        'exposure_adjustment': 3.0  # Too high (limit is ±2 stops)
    }

    valid, error = validate_isp_parameters(invalid_exposure)
    print(f"\nInvalid exposure: {invalid_exposure}")
    print(f"  Result: {'VALID ✓' if valid else 'INVALID ✗'}")
    print(f"  Error: {error}")
    assert not valid, "Invalid exposure should be rejected"

    print("\n✓ Test 4 PASSED\n")


def test_complete_validation_data_structure():
    """Test 5: Complete ISP validation data structure."""
    print("=" * 60)
    print("Test 5: ISP Validation Data Structure")
    print("=" * 60)

    raw_bayer = np.random.randint(0, 1024, (304, 405), dtype=np.uint16)
    raw_rgb = debayer_raw_image(raw_bayer)

    isp_params = {
        'white_balance': {'red_gain': 1.25, 'blue_gain': 1.15},
        'exposure_adjustment': 0.5,
        'sharpening': 0.5,
        'noise_reduction': 0.3
    }

    processed = apply_expected_transforms(raw_rgb, isp_params)
    noise = np.random.normal(0, 3, processed.shape)
    processed = np.clip(processed.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    # Create validation data structure
    validation_data = create_isp_validation_data(
        raw_bayer,
        processed,
        isp_params,
        shooting_mode="standard",
        num_samples=100
    )

    print("ISP Validation Data Structure:")
    print(f"  variance_metric: {validation_data['variance_metric']:.4f}")
    print(f"  isp_parameters: {validation_data['isp_parameters']}")
    print(f"  sample_count: {validation_data['sample_count']}")
    print(f"  shooting_mode: {validation_data['shooting_mode']}")
    print(f"  metric_version: {validation_data['metric_version']}")

    assert 'variance_metric' in validation_data
    assert 'isp_parameters' in validation_data
    assert 'sample_count' in validation_data
    assert 'shooting_mode' in validation_data
    assert validation_data['metric_version'] == 'v2.0'

    print("\n✓ Test 5 PASSED\n")


def test_sma_integration():
    """Test 6: SMA validation integration."""
    print("=" * 60)
    print("Test 6: SMA Validation Integration")
    print("=" * 60)

    # Add SMA path
    sma_path = Path(__file__).parent.parent.parent.parent / "sma" / "src"
    sys.path.insert(0, str(sma_path))

    try:
        from validation.isp_validator import validate_isp_submission

        # Test valid submission
        isp_data = {
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

        result = validate_isp_submission(isp_data, "RASPBERRY_PI_HQ", "TEST-001")

        print("Valid submission:")
        print(f"  Result: {'PASS ✓' if result.is_valid else 'FAIL ✗'}")
        print(f"  Variance: {result.variance_metric:.4f}")
        print(f"  Threshold: {result.threshold:.4f}")
        print(f"  Flags: {result.flags}")

        assert result.is_valid, "Valid submission should pass"

        # Test excessive variance
        isp_data_excessive = isp_data.copy()
        isp_data_excessive["variance_metric"] = 0.25  # Above threshold

        result = validate_isp_submission(isp_data_excessive, "RASPBERRY_PI_HQ", "TEST-002")

        print("\nExcessive variance submission:")
        print(f"  Result: {'PASS ✓' if result.is_valid else 'FAIL ✗'}")
        print(f"  Reason: {result.reason}")
        print(f"  Variance: {result.variance_metric:.4f}")
        print(f"  Threshold: {result.threshold:.4f}")

        assert not result.is_valid, "Excessive variance should fail"
        assert result.reason == "EXCESSIVE_VARIANCE"

        print("\n✓ Test 6 PASSED\n")

    except ImportError as e:
        print(f"⚠ SMA modules not available: {e}")
        print("Skipping SMA integration test\n")


def run_all_tests():
    """Run all integration tests."""
    print("\n" + "=" * 60)
    print("ISP VARIANCE-FROM-EXPECTED VALIDATION TEST SUITE")
    print("=" * 60 + "\n")

    tests = [
        test_normal_isp_processing,
        test_extreme_but_declared_processing,
        test_unauthorized_manipulation,
        test_parameter_validation,
        test_complete_validation_data_structure,
        test_sma_integration
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ TEST FAILED: {e}\n")
            failed += 1
        except Exception as e:
            print(f"✗ TEST ERROR: {e}\n")
            failed += 1

    print("=" * 60)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
