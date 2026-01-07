#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Birthmark Camera - Installation Test Script

Validates that the Birthmark camera system is correctly installed and configured.
Tests each component individually and reports any issues.

Usage:
    python test_installation.py [--full] [--capture]

Options:
    --full      Run full test suite including network connectivity
    --capture   Perform a test capture (requires camera hardware)
"""

import sys
import json
import hashlib
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Tuple

# Test result tracking
@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    details: Optional[str] = None


class InstallationTester:
    """Test Birthmark camera installation."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize tester."""
        self.data_dir = data_dir or Path.home() / "birthmark" / "data"
        self.results: List[TestResult] = []

    def add_result(self, name: str, passed: bool, message: str, details: str = None):
        """Add a test result."""
        self.results.append(TestResult(name, passed, message, details))

    def test_python_version(self) -> bool:
        """Test Python version >= 3.10."""
        version = sys.version_info
        passed = version.major >= 3 and version.minor >= 10
        self.add_result(
            "Python Version",
            passed,
            f"Python {version.major}.{version.minor}.{version.micro}",
            "Requires Python 3.10+" if not passed else None
        )
        return passed

    def test_core_imports(self) -> bool:
        """Test that core dependencies can be imported."""
        modules = [
            ("numpy", "numpy"),
            ("cryptography", "cryptography"),
            ("requests", "requests"),
            ("PIL", "pillow"),
            ("pydantic", "pydantic"),
        ]

        all_passed = True
        for module_name, package_name in modules:
            try:
                __import__(module_name)
                self.add_result(f"Import {module_name}", True, "OK")
            except ImportError as e:
                self.add_result(
                    f"Import {module_name}",
                    False,
                    f"Failed to import",
                    f"pip install {package_name}"
                )
                all_passed = False

        return all_passed

    def test_camera_imports(self) -> bool:
        """Test camera-specific imports."""
        try:
            from picamera2 import Picamera2
            self.add_result("Import picamera2", True, "OK (hardware available)")
            return True
        except ImportError:
            self.add_result(
                "Import picamera2",
                False,
                "Not available",
                "picamera2 requires Raspberry Pi OS with libcamera"
            )
            return False

    def test_opencv(self) -> bool:
        """Test OpenCV for ISP validation."""
        try:
            import cv2
            self.add_result("Import OpenCV", True, f"Version {cv2.__version__}")
            return True
        except ImportError:
            self.add_result(
                "Import OpenCV",
                False,
                "Not available",
                "pip install opencv-python-headless"
            )
            return False

    def test_birthmark_package(self) -> bool:
        """Test Birthmark camera package installation."""
        modules = [
            "camera_pi.raw_capture",
            "camera_pi.tpm_interface",
            "camera_pi.camera_token",
            "camera_pi.aggregation_client",
            "camera_pi.provisioning_client",
            "camera_pi.isp_validation",
        ]

        all_passed = True
        for module in modules:
            try:
                __import__(module)
                short_name = module.split(".")[-1]
                self.add_result(f"Module {short_name}", True, "OK")
            except ImportError as e:
                self.add_result(
                    f"Module {module}",
                    False,
                    f"Import failed: {e}",
                    "pip install -e /path/to/camera-pi"
                )
                all_passed = False

        return all_passed

    def test_provisioning_file(self) -> bool:
        """Test that provisioning file exists and is valid."""
        prov_file = self.data_dir / "provisioning.json"

        if not prov_file.exists():
            self.add_result(
                "Provisioning File",
                False,
                f"Not found: {prov_file}",
                "Run install_provisioning.sh with your provisioning file"
            )
            return False

        try:
            with open(prov_file) as f:
                data = json.load(f)

            # Check required fields
            required = [
                "device_serial",
                "device_certificate",
                "device_private_key",
                "table_assignments",
                "nuc_hash",
                "master_keys"
            ]

            missing = [f for f in required if f not in data]
            if missing:
                self.add_result(
                    "Provisioning File",
                    False,
                    f"Missing fields: {missing}",
                    "Re-provision the device with SMA"
                )
                return False

            # Validate structure
            if len(data["table_assignments"]) != 3:
                self.add_result(
                    "Provisioning File",
                    False,
                    f"Expected 3 table assignments, got {len(data['table_assignments'])}",
                    None
                )
                return False

            self.add_result(
                "Provisioning File",
                True,
                f"Device: {data['device_serial']}",
                f"Tables: {data['table_assignments']}"
            )
            return True

        except json.JSONDecodeError as e:
            self.add_result(
                "Provisioning File",
                False,
                f"Invalid JSON: {e}",
                None
            )
            return False

    def test_crypto_operations(self) -> bool:
        """Test cryptographic operations."""
        try:
            from camera_pi.crypto.key_derivation import derive_encryption_key
            from camera_pi.crypto.encryption import encrypt_data, decrypt_data

            # Test key derivation
            master_key = bytes(32)  # Test key
            derived = derive_encryption_key(master_key, 0)
            assert len(derived) == 32, "Derived key wrong length"

            self.add_result("Key Derivation", True, "OK")

            # Test encryption
            test_data = b"test plaintext"
            encrypted, nonce, tag = encrypt_data(test_data, derived)
            decrypted = decrypt_data(encrypted, derived, nonce, tag)
            assert decrypted == test_data, "Decryption mismatch"

            self.add_result("AES-GCM Encryption", True, "OK")
            return True

        except Exception as e:
            self.add_result("Crypto Operations", False, str(e), None)
            return False

    def test_token_generation(self) -> bool:
        """Test camera token generation."""
        try:
            from camera_pi.camera_token import TokenGenerator

            # Create mock data
            nuc_hash = bytes(32)
            master_keys = {0: bytes(32), 1: bytes(32), 2: bytes(32)}
            table_assignments = [0, 1, 2]

            generator = TokenGenerator(
                nuc_hash=nuc_hash,
                master_keys=master_keys,
                table_assignments=table_assignments
            )

            token = generator.generate_token()
            assert token.ciphertext is not None
            assert token.nonce is not None
            assert token.auth_tag is not None

            self.add_result("Token Generation", True, "OK")
            return True

        except Exception as e:
            self.add_result("Token Generation", False, str(e), None)
            return False

    def test_isp_validation(self) -> bool:
        """Test ISP validation functions."""
        try:
            import numpy as np
            from camera_pi.isp_validation import (
                validate_isp_parameters,
                debayer_raw_image,
            )

            # Test parameter validation
            valid_params = {
                'white_balance': {'red_gain': 1.0, 'blue_gain': 1.0},
                'exposure_adjustment': 0.0,
                'sharpening': 0.5,
                'noise_reduction': 0.3
            }
            is_valid, _ = validate_isp_parameters(valid_params)
            assert is_valid, "Valid parameters rejected"

            self.add_result("ISP Parameter Validation", True, "OK")

            # Test debayering (small test image)
            test_bayer = np.random.randint(0, 1024, (100, 100), dtype=np.uint16)
            rgb = debayer_raw_image(test_bayer)
            assert rgb.shape == (100, 100, 3), f"Wrong shape: {rgb.shape}"

            self.add_result("Debayering", True, "OK")
            return True

        except Exception as e:
            self.add_result("ISP Validation", False, str(e), None)
            return False

    def test_mock_capture(self) -> bool:
        """Test capture with mock camera."""
        try:
            from camera_pi.raw_capture import MockCaptureManager

            with MockCaptureManager() as camera:
                result = camera.capture_with_hash(
                    capture_processed=True,
                    validate_isp=False  # Skip ISP validation for speed
                )

            assert len(result.image_hash) == 64, "Wrong hash length"
            assert result.raw_bayer is not None, "No raw data"

            self.add_result(
                "Mock Capture",
                True,
                f"Hash: {result.image_hash[:16]}...",
                f"Capture: {result.capture_time:.3f}s, Hash: {result.hash_time:.3f}s"
            )
            return True

        except Exception as e:
            self.add_result("Mock Capture", False, str(e), None)
            return False

    def test_real_capture(self) -> bool:
        """Test capture with real camera (if available)."""
        try:
            from camera_pi.raw_capture import RawCaptureManager, PICAMERA_AVAILABLE

            if not PICAMERA_AVAILABLE:
                self.add_result(
                    "Real Capture",
                    False,
                    "picamera2 not available",
                    "Only available on Raspberry Pi"
                )
                return False

            with RawCaptureManager() as camera:
                result = camera.capture_with_hash(
                    capture_processed=True,
                    validate_isp=True
                )

            self.add_result(
                "Real Capture",
                True,
                f"Hash: {result.image_hash[:16]}...",
                f"Size: {result.raw_bayer.shape}, ISP variance: {result.isp_variance}"
            )
            return True

        except Exception as e:
            self.add_result("Real Capture", False, str(e), None)
            return False

    def test_server_connectivity(self, aggregator_url: str = None) -> bool:
        """Test connectivity to aggregation server."""
        if aggregator_url is None:
            config_file = self.data_dir / "config.json"
            if config_file.exists():
                with open(config_file) as f:
                    config = json.load(f)
                aggregator_url = config.get("aggregator_url")

        if not aggregator_url:
            self.add_result(
                "Server Connectivity",
                False,
                "No aggregator URL configured",
                f"Set aggregator_url in {self.data_dir}/config.json"
            )
            return False

        try:
            import requests
            response = requests.get(f"{aggregator_url}/health", timeout=5)

            if response.status_code == 200:
                self.add_result(
                    "Server Connectivity",
                    True,
                    f"Connected to {aggregator_url}",
                    f"Status: {response.json().get('status', 'unknown')}"
                )
                return True
            else:
                self.add_result(
                    "Server Connectivity",
                    False,
                    f"HTTP {response.status_code}",
                    None
                )
                return False

        except Exception as e:
            self.add_result(
                "Server Connectivity",
                False,
                f"Connection failed: {e}",
                None
            )
            return False

    def print_results(self):
        """Print test results."""
        print("\n" + "=" * 70)
        print("  BIRTHMARK INSTALLATION TEST RESULTS")
        print("=" * 70 + "\n")

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)

        for result in self.results:
            status = "\033[92m✓\033[0m" if result.passed else "\033[91m✗\033[0m"
            print(f"  {status} {result.name}: {result.message}")
            if result.details:
                print(f"      {result.details}")

        print("\n" + "-" * 70)
        print(f"  Total: {passed} passed, {failed} failed")
        print("-" * 70 + "\n")

        if failed == 0:
            print("\033[92m  All tests passed! Installation is ready.\033[0m\n")
        else:
            print("\033[91m  Some tests failed. Please fix the issues above.\033[0m\n")

        return failed == 0

    def run_basic_tests(self) -> bool:
        """Run basic installation tests."""
        self.test_python_version()
        self.test_core_imports()
        self.test_opencv()
        self.test_camera_imports()
        self.test_birthmark_package()
        self.test_provisioning_file()
        self.test_crypto_operations()
        self.test_token_generation()
        self.test_isp_validation()
        self.test_mock_capture()
        return self.print_results()

    def run_full_tests(self, test_capture: bool = False) -> bool:
        """Run full test suite."""
        self.run_basic_tests()

        # Clear results to re-print
        results_backup = self.results.copy()
        self.results = results_backup

        # Additional tests
        self.test_server_connectivity()

        if test_capture:
            self.test_real_capture()

        return self.print_results()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Test Birthmark camera installation"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full test suite including network connectivity"
    )
    parser.add_argument(
        "--capture",
        action="store_true",
        help="Perform a test capture (requires camera hardware)"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Path to Birthmark data directory"
    )

    args = parser.parse_args()

    print("\n\033[94m")
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║        Birthmark Camera - Installation Test                   ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print("\033[0m")

    tester = InstallationTester(data_dir=args.data_dir)

    if args.full or args.capture:
        success = tester.run_full_tests(test_capture=args.capture)
    else:
        success = tester.run_basic_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
