#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
SMA validation data structures

This module defines the data structures for validation requests between
the aggregation server and the SMA (Simulated Manufacturer Authority).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidationRequest:
    """
    Request from aggregation server to SMA for NUC token validation.

    CRITICAL PRIVACY INVARIANT: This request contains the encrypted NUC token
    but NEVER contains the image hash. The SMA validates the camera's authenticity
    without learning what image was captured.

    Attributes:
        encrypted_nuc_hash: Hex-encoded encrypted NUC hash (96 chars = 48 bytes)
        table_id: Table ID to use for decryption (0-2499)
        key_index: Key index within table (0-999)
        nonce: Hex-encoded nonce used for encryption (24 chars = 12 bytes)
        request_id: Optional unique identifier for this validation request

    Example:
        >>> request = ValidationRequest(
        ...     encrypted_nuc_hash="a" * 96,
        ...     table_id=42,
        ...     key_index=123,
        ...     nonce="b" * 24
        ... )
    """

    encrypted_nuc_hash: str  # 96 hex chars (48 bytes)
    table_id: int  # 0-2499
    key_index: int  # 0-999
    nonce: str  # 24 hex chars (12 bytes)
    request_id: Optional[str] = None  # UUID for tracking

    def __post_init__(self):
        """Validate request after initialization."""
        # Validate encrypted_nuc_hash
        if not isinstance(self.encrypted_nuc_hash, str) or len(self.encrypted_nuc_hash) != 96:
            raise ValueError(
                f"encrypted_nuc_hash must be 96-character hex string (48 bytes), "
                f"got {len(self.encrypted_nuc_hash)}"
            )

        # Validate table_id
        if not isinstance(self.table_id, int) or not (0 <= self.table_id < 2500):
            raise ValueError(f"table_id must be 0-2499, got {self.table_id}")

        # Validate key_index
        if not isinstance(self.key_index, int) or not (0 <= self.key_index < 1000):
            raise ValueError(f"key_index must be 0-999, got {self.key_index}")

        # Validate nonce
        if not isinstance(self.nonce, str) or len(self.nonce) != 24:
            raise ValueError(f"nonce must be 24-character hex string (12 bytes), got {len(self.nonce)}")


@dataclass
class ValidationResponse:
    """
    Response from SMA after validating NUC token.

    The SMA returns a simple PASS/FAIL response. If PASS, the camera is legitimate.
    If FAIL, either the token is invalid or the camera is not registered.

    Attributes:
        validation_result: "PASS" or "FAIL"
        manufacturer_id: Identifier for the SMA/manufacturer
        device_family: Optional device type ("Raspberry Pi", "iOS", etc.)
        device_serial: Optional device serial (only on PASS, for logging)
        timestamp: ISO 8601 timestamp of validation
        error: Optional error message (only on FAIL)

    Example:
        >>> response = ValidationResponse(
        ...     validation_result="PASS",
        ...     manufacturer_id="SimulatedMfg",
        ...     device_family="Raspberry Pi",
        ...     device_serial="RaspberryPi-001",
        ...     timestamp="2024-11-13T10:30:00Z"
        ... )
    """

    validation_result: str  # "PASS" or "FAIL"
    manufacturer_id: str
    timestamp: str  # ISO 8601
    device_family: Optional[str] = None
    device_serial: Optional[str] = None  # Only on PASS
    error: Optional[str] = None  # Only on FAIL

    def __post_init__(self):
        """Validate response after initialization."""
        valid_results = ["PASS", "FAIL"]
        if self.validation_result not in valid_results:
            raise ValueError(
                f"validation_result must be one of {valid_results}, got {self.validation_result}"
            )

    def is_valid(self) -> bool:
        """Check if validation passed."""
        return self.validation_result == "PASS"


if __name__ == "__main__":
    print("=" * 80)
    print("Testing Validation Data Structures")
    print("=" * 80)

    # Test 1: Valid validation request
    print("\nTest 1: Valid Validation Request")
    try:
        request = ValidationRequest(
            encrypted_nuc_hash="a" * 96,
            table_id=42,
            key_index=123,
            nonce="b" * 24,
            request_id="550e8400-e29b-41d4-a716-446655440000"
        )
        print(f"  ✓ Created valid request")
        print(f"    Encrypted NUC: {request.encrypted_nuc_hash[:16]}...")
        print(f"    Table: {request.table_id}, Key: {request.key_index}")
        print(f"    Request ID: {request.request_id}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")

    # Test 2: Invalid table_id
    print("\nTest 2: Invalid Table ID (out of range)")
    try:
        request = ValidationRequest(
            encrypted_nuc_hash="a" * 96,
            table_id=3000,  # Out of range
            key_index=123,
            nonce="b" * 24
        )
        print(f"  ✗ Should have failed")
    except ValueError as e:
        print(f"  ✓ Correctly rejected: {str(e)[:60]}...")

    # Test 3: PASS validation response
    print("\nTest 3: PASS Validation Response")
    try:
        response = ValidationResponse(
            validation_result="PASS",
            manufacturer_id="SimulatedMfg",
            device_family="Raspberry Pi",
            device_serial="RaspberryPi-001",
            timestamp="2024-11-13T10:30:00Z"
        )
        print(f"  ✓ Created PASS response")
        print(f"    Result: {response.validation_result}")
        print(f"    Device: {response.device_serial}")
        print(f"    Is valid: {response.is_valid()}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")

    # Test 4: FAIL validation response
    print("\nTest 4: FAIL Validation Response")
    try:
        response = ValidationResponse(
            validation_result="FAIL",
            manufacturer_id="SimulatedMfg",
            timestamp="2024-11-13T10:30:00Z",
            error="NUC hash does not match any registered device"
        )
        print(f"  ✓ Created FAIL response")
        print(f"    Result: {response.validation_result}")
        print(f"    Error: {response.error}")
        print(f"    Is valid: {response.is_valid()}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")

    # Test 5: Invalid validation result
    print("\nTest 5: Invalid Validation Result")
    try:
        response = ValidationResponse(
            validation_result="MAYBE",  # Invalid
            manufacturer_id="SimulatedMfg",
            timestamp="2024-11-13T10:30:00Z"
        )
        print(f"  ✗ Should have failed")
    except ValueError as e:
        print(f"  ✓ Correctly rejected: {str(e)[:60]}...")

    print("\n" + "=" * 80)
    print("✓ All tests passed")
    print("=" * 80)
