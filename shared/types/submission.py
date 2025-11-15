#!/usr/bin/env python3
"""
Camera submission data structures

This module defines the data structures for authentication bundles submitted
from cameras to the aggregation server.
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class AuthenticationBundle:
    """
    Complete authentication bundle submitted by camera to aggregation server.

    This bundle contains everything needed to authenticate an image:
    - Image hash (what we're authenticating)
    - Encrypted NUC token (proves camera authenticity)
    - Table references and key indices (for SMA to decrypt token)
    - Timestamp (when image was captured)
    - Optional GPS hash (where image was captured)
    - Device signature (proves bundle came from provisioned device)

    The aggregation server forwards the encrypted token to the SMA for validation,
    but NEVER shares the image hash with the SMA (privacy guarantee).

    Attributes:
        image_hash: SHA-256 hash of raw Bayer sensor data (64 hex chars)
        encrypted_nuc_token: AES-GCM encrypted NUC hash (96 hex chars = 48 bytes)
        nonce: Encryption nonce (24 hex chars = 12 bytes)
        table_references: List of 3 table IDs used (values 0-2499)
        key_indices: List of 3 key indices corresponding to tables (values 0-999)
        timestamp: Unix timestamp when image was captured
        gps_hash: Optional SHA-256 hash of GPS coordinates (64 hex chars)
        device_signature: Device's signature over the bundle (hex string)

    Example:
        >>> bundle = AuthenticationBundle(
        ...     image_hash="a1b2c3...",  # 64 chars
        ...     encrypted_nuc_token="d4e5f6...",  # 96 chars (48 bytes)
        ...     nonce="789abc...",  # 24 chars (12 bytes)
        ...     table_references=[42, 1337, 2001],
        ...     key_indices=[7, 99, 512],
        ...     timestamp=1732000000,
        ...     gps_hash="optional...",
        ...     device_signature="signed..."
        ... )
    """

    image_hash: str
    encrypted_nuc_token: str  # Hex-encoded ciphertext (48 bytes = 96 hex chars)
    nonce: str  # Hex-encoded nonce (12 bytes = 24 hex chars)
    table_references: List[int]  # 3 table IDs
    key_indices: List[int]  # 3 key indices
    timestamp: int  # Unix timestamp
    gps_hash: Optional[str] = None  # Optional GPS coordinate hash
    device_signature: Optional[str] = None  # Optional device signature

    def __post_init__(self):
        """Validate bundle after initialization."""
        # Validate image_hash
        if not isinstance(self.image_hash, str) or len(self.image_hash) != 64:
            raise ValueError(f"image_hash must be 64-character hex string, got {len(self.image_hash)}")

        # Validate encrypted_nuc_token
        if not isinstance(self.encrypted_nuc_token, str) or len(self.encrypted_nuc_token) != 96:
            raise ValueError(
                f"encrypted_nuc_token must be 96-character hex string (48 bytes), "
                f"got {len(self.encrypted_nuc_token)}"
            )

        # Validate nonce
        if not isinstance(self.nonce, str) or len(self.nonce) != 24:
            raise ValueError(f"nonce must be 24-character hex string (12 bytes), got {len(self.nonce)}")

        # Validate table_references
        if not isinstance(self.table_references, list) or len(self.table_references) != 3:
            raise ValueError(f"table_references must be list of 3 integers, got {self.table_references}")

        for table_id in self.table_references:
            if not isinstance(table_id, int) or not (0 <= table_id < 2500):
                raise ValueError(f"table_id must be 0-2499, got {table_id}")

        # Validate key_indices
        if not isinstance(self.key_indices, list) or len(self.key_indices) != 3:
            raise ValueError(f"key_indices must be list of 3 integers, got {self.key_indices}")

        for key_index in self.key_indices:
            if not isinstance(key_index, int) or not (0 <= key_index < 1000):
                raise ValueError(f"key_index must be 0-999, got {key_index}")

        # Validate timestamp
        if not isinstance(self.timestamp, int) or self.timestamp < 0:
            raise ValueError(f"timestamp must be non-negative integer, got {self.timestamp}")

        # Validate GPS hash if present
        if self.gps_hash is not None and len(self.gps_hash) != 64:
            raise ValueError(f"gps_hash must be 64-character hex string if provided, got {len(self.gps_hash)}")


@dataclass
class SubmissionResponse:
    """
    Response from aggregation server after receiving submission.

    The server immediately returns a receipt to the camera, then processes
    the submission asynchronously.

    Attributes:
        receipt_id: Unique identifier for this submission (UUID)
        status: Initial status ("pending_validation", "queued", "rejected")
        received_at: ISO 8601 timestamp when server received submission
        estimated_confirmation_time: Optional estimated time for blockchain confirmation

    Example:
        >>> response = SubmissionResponse(
        ...     receipt_id="550e8400-e29b-41d4-a716-446655440000",
        ...     status="pending_validation",
        ...     received_at="2024-11-13T10:30:00Z"
        ... )
    """

    receipt_id: str
    status: str
    received_at: str  # ISO 8601 timestamp
    estimated_confirmation_time: Optional[str] = None  # ISO 8601 timestamp

    def __post_init__(self):
        """Validate response after initialization."""
        valid_statuses = ["pending_validation", "queued", "rejected", "validating"]
        if self.status not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}, got {self.status}")


if __name__ == "__main__":
    print("=" * 80)
    print("Testing Authentication Bundle Data Structures")
    print("=" * 80)

    # Test 1: Valid bundle
    print("\nTest 1: Valid Authentication Bundle")
    try:
        bundle = AuthenticationBundle(
            image_hash="a" * 64,
            encrypted_nuc_token="b" * 96,
            nonce="c" * 24,
            table_references=[0, 500, 1000],
            key_indices=[0, 500, 999],
            timestamp=1732000000,
            gps_hash="d" * 64,
            device_signature="e" * 128
        )
        print(f"  ✓ Created valid bundle")
        print(f"    Image hash: {bundle.image_hash[:16]}...")
        print(f"    Tables: {bundle.table_references}")
        print(f"    Keys: {bundle.key_indices}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")

    # Test 2: Invalid image hash
    print("\nTest 2: Invalid Image Hash (too short)")
    try:
        bundle = AuthenticationBundle(
            image_hash="short",
            encrypted_nuc_token="b" * 96,
            nonce="c" * 24,
            table_references=[0, 500, 1000],
            key_indices=[0, 500, 999],
            timestamp=1732000000
        )
        print(f"  ✗ Should have failed")
    except ValueError as e:
        print(f"  ✓ Correctly rejected: {str(e)[:60]}...")

    # Test 3: Invalid table references
    print("\nTest 3: Invalid Table Reference (out of range)")
    try:
        bundle = AuthenticationBundle(
            image_hash="a" * 64,
            encrypted_nuc_token="b" * 96,
            nonce="c" * 24,
            table_references=[0, 500, 3000],  # 3000 is out of range
            key_indices=[0, 500, 999],
            timestamp=1732000000
        )
        print(f"  ✗ Should have failed")
    except ValueError as e:
        print(f"  ✓ Correctly rejected: {str(e)[:60]}...")

    # Test 4: Submission response
    print("\nTest 4: Submission Response")
    try:
        response = SubmissionResponse(
            receipt_id="550e8400-e29b-41d4-a716-446655440000",
            status="pending_validation",
            received_at="2024-11-13T10:30:00Z",
            estimated_confirmation_time="2024-11-13T10:35:00Z"
        )
        print(f"  ✓ Created valid response")
        print(f"    Receipt ID: {response.receipt_id}")
        print(f"    Status: {response.status}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")

    print("\n" + "=" * 80)
    print("✓ All tests passed")
    print("=" * 80)
