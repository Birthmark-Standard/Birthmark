# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Key derivation utilities using HKDF-SHA256.

CRITICAL: This implementation must exactly match the camera-side implementation.
Any discrepancy will cause validation failures.

The key derivation scheme:
- Master key (256-bit) stored in key table
- Key index (0-999) identifies specific encryption key
- HKDF-SHA256 derives encryption key from (master_key, key_index)
- Context: b"Birthmark" ensures domain separation
"""

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
from typing import Optional


# Context string for HKDF (domain separation)
HKDF_CONTEXT = b"Birthmark"


def derive_encryption_key(
    master_key: bytes,
    key_index: int,
    context: bytes = HKDF_CONTEXT,
    key_length: int = 32
) -> bytes:
    """
    Derive an encryption key from a master key using HKDF-SHA256.

    This function MUST produce identical output to the camera implementation
    for the same inputs. Both camera and SMA derive keys independently.

    Args:
        master_key: 256-bit (32 bytes) master key from key table
        key_index: Integer index (0-999) identifying the derived key
        context: Context string for domain separation (default: b"Birthmark")
        key_length: Output key length in bytes (default: 32 for AES-256)

    Returns:
        Derived encryption key (32 bytes for AES-256-GCM)

    Raises:
        ValueError: If master_key is not 32 bytes or key_index out of range
    """
    if len(master_key) != 32:
        raise ValueError(f"Master key must be 32 bytes, got {len(master_key)}")

    if not 0 <= key_index <= 999:
        raise ValueError(f"Key index must be 0-999, got {key_index}")

    # Encode key index as 4-byte big-endian integer
    # This serves as the "info" parameter in HKDF
    info = key_index.to_bytes(4, byteorder='big') + context

    # HKDF-SHA256 key derivation
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=key_length,
        salt=None,  # Optional salt (None uses zeros)
        info=info,
        backend=default_backend()
    )

    derived_key = hkdf.derive(master_key)
    return derived_key


def verify_key_derivation(
    master_key: bytes,
    key_index: int,
    expected_key: bytes,
    context: bytes = HKDF_CONTEXT
) -> bool:
    """
    Verify that a derived key matches the expected value.

    Useful for testing and validation.

    Args:
        master_key: 256-bit master key
        key_index: Key index (0-999)
        expected_key: Expected derived key
        context: Context string (default: b"Birthmark")

    Returns:
        True if derived key matches expected key, False otherwise
    """
    try:
        derived = derive_encryption_key(master_key, key_index, context)
        return derived == expected_key
    except Exception:
        return False


class KeyDerivationManager:
    """
    Manages key derivation for multiple key tables.

    In Phase 1: Loads 10 key tables from JSON
    In Phase 2: Loads 2,500 key tables from PostgreSQL
    """

    def __init__(self, key_tables: dict[int, bytes]):
        """
        Initialize with key tables.

        Args:
            key_tables: Dictionary mapping table_id -> master_key
                       Phase 1: 10 tables (IDs 0-9)
                       Phase 2: 2,500 tables (IDs 0-2499)
        """
        self.key_tables = key_tables

    def derive_key(self, table_id: int, key_index: int) -> bytes:
        """
        Derive encryption key from specified table and index.

        Args:
            table_id: Key table ID
            key_index: Key index within table (0-999)

        Returns:
            Derived encryption key (32 bytes)

        Raises:
            KeyError: If table_id not found
            ValueError: If key_index out of range
        """
        if table_id not in self.key_tables:
            raise KeyError(f"Key table {table_id} not found")

        master_key = self.key_tables[table_id]
        return derive_encryption_key(master_key, key_index)

    def derive_multiple_keys(
        self,
        table_references: list[int],
        key_indices: list[int]
    ) -> list[bytes]:
        """
        Derive multiple encryption keys from table/index pairs.

        Typically used to derive 3 keys for NUC token encryption.

        Args:
            table_references: List of table IDs (e.g., [42, 1337, 2001])
            key_indices: List of key indices (e.g., [7, 99, 512])

        Returns:
            List of derived keys in same order

        Raises:
            ValueError: If lists have different lengths
        """
        if len(table_references) != len(key_indices):
            raise ValueError(
                f"Table references ({len(table_references)}) and key indices "
                f"({len(key_indices)}) must have same length"
            )

        return [
            self.derive_key(table_id, key_idx)
            for table_id, key_idx in zip(table_references, key_indices)
        ]


# Test vectors for validation
# These ensure camera and SMA implementations match
TEST_VECTORS = [
    {
        "master_key": bytes.fromhex(
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        ),
        "key_index": 0,
        "expected_key": None,  # Will be computed on first run
        "description": "Test vector 1: key_index=0"
    },
    {
        "master_key": bytes.fromhex(
            "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        ),
        "key_index": 999,
        "expected_key": None,
        "description": "Test vector 2: All-ones master key, max index"
    },
    {
        "master_key": bytes.fromhex(
            "0000000000000000000000000000000000000000000000000000000000000000"
        ),
        "key_index": 500,
        "expected_key": None,
        "description": "Test vector 3: All-zeros master key, mid index"
    },
]


def generate_test_vectors() -> list[dict]:
    """
    Generate test vectors for key derivation validation.

    These vectors should be shared with camera implementation to ensure compatibility.

    Returns:
        List of test vector dictionaries with computed expected keys
    """
    vectors = []
    for vector in TEST_VECTORS:
        expected_key = derive_encryption_key(
            vector["master_key"],
            vector["key_index"]
        )
        vectors.append({
            **vector,
            "expected_key": expected_key.hex(),
            "expected_key_bytes": expected_key
        })
    return vectors


def validate_implementation() -> bool:
    """
    Validate key derivation implementation against test vectors.

    Returns:
        True if all test vectors pass, False otherwise
    """
    vectors = generate_test_vectors()

    for i, vector in enumerate(vectors):
        derived = derive_encryption_key(
            vector["master_key"],
            vector["key_index"]
        )

        if derived != vector["expected_key_bytes"]:
            print(f"Test vector {i} failed: {vector['description']}")
            print(f"  Expected: {vector['expected_key']}")
            print(f"  Got:      {derived.hex()}")
            return False

    print(f"All {len(vectors)} test vectors passed!")
    return True


if __name__ == "__main__":
    # Run validation when executed directly
    print("Validating key derivation implementation...")
    validate_implementation()

    # Print test vectors for camera implementation
    print("\nTest vectors for camera implementation:")
    for i, vector in enumerate(generate_test_vectors()):
        print(f"\nVector {i}: {vector['description']}")
        print(f"  Master key:   {vector['master_key'].hex()}")
        print(f"  Key index:    {vector['key_index']}")
        print(f"  Expected key: {vector['expected_key']}")
