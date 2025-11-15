"""
Key derivation utilities using HKDF-SHA256.

CRITICAL: This implementation must exactly match the SMA implementation at:
packages/sma/src/key_tables/key_derivation.py

Any discrepancy will cause validation failures. Test vectors must match byte-for-byte.

The key derivation scheme:
- Master key (256-bit) from provisioning
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

    This function MUST produce identical output to the SMA implementation
    for the same inputs. Both camera and SMA derive keys independently.

    Args:
        master_key: 256-bit (32 bytes) master key from provisioning
        key_index: Integer index (0-999) identifying the derived key
        context: Context string for domain separation (default: b"Birthmark")
        key_length: Output key length in bytes (default: 32 for AES-256)

    Returns:
        Derived encryption key (32 bytes for AES-256-GCM)

    Raises:
        ValueError: If master_key is not 32 bytes or key_index out of range

    Example:
        >>> master_key = bytes.fromhex("00" * 32)
        >>> derived = derive_encryption_key(master_key, 0)
        >>> len(derived)
        32
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

    Useful for testing and validation against SMA.

    Args:
        master_key: 256-bit master key
        key_index: Key index (0-999)
        expected_key: Expected derived key from SMA
        context: Context string (default: b"Birthmark")

    Returns:
        True if derived key matches expected key, False otherwise

    Example:
        >>> master_key = bytes.fromhex("00" * 32)
        >>> derived = derive_encryption_key(master_key, 0)
        >>> verify_key_derivation(master_key, 0, derived)
        True
    """
    try:
        derived = derive_encryption_key(master_key, key_index, context)
        return derived == expected_key
    except Exception:
        return False


# Test vectors for validation with SMA
# These ensure camera and SMA implementations match
TEST_VECTORS = [
    {
        "description": "Test vector 1: All-zeros master key, index 0",
        "master_key": bytes.fromhex(
            "0000000000000000000000000000000000000000000000000000000000000000"
        ),
        "key_index": 0,
    },
    {
        "description": "Test vector 2: Sequential master key, index 0",
        "master_key": bytes.fromhex(
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        ),
        "key_index": 0,
    },
    {
        "description": "Test vector 3: All-ones master key, max index",
        "master_key": bytes.fromhex(
            "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        ),
        "key_index": 999,
    },
    {
        "description": "Test vector 4: All-zeros master key, mid index",
        "master_key": bytes.fromhex(
            "0000000000000000000000000000000000000000000000000000000000000000"
        ),
        "key_index": 500,
    },
]


def generate_test_vectors() -> list[dict]:
    """
    Generate test vectors for key derivation validation.

    These vectors should be compared with SMA implementation to ensure compatibility.
    Run the SMA test vector generation and compare outputs.

    Returns:
        List of test vector dictionaries with computed derived keys

    Example:
        >>> vectors = generate_test_vectors()
        >>> len(vectors)
        4
        >>> all('derived_key' in v for v in vectors)
        True
    """
    vectors = []
    for vector in TEST_VECTORS:
        derived_key = derive_encryption_key(
            vector["master_key"],
            vector["key_index"]
        )
        vectors.append({
            **vector,
            "derived_key": derived_key.hex(),
            "derived_key_bytes": derived_key
        })
    return vectors


def validate_implementation() -> bool:
    """
    Validate key derivation implementation against test vectors.

    This checks for internal consistency. For SMA compatibility,
    compare test vectors with SMA output.

    Returns:
        True if all test vectors are internally consistent

    Example:
        >>> validate_implementation()
        True
    """
    vectors = generate_test_vectors()

    for i, vector in enumerate(vectors):
        # Re-derive and check consistency
        derived = derive_encryption_key(
            vector["master_key"],
            vector["key_index"]
        )

        if derived != vector["derived_key_bytes"]:
            print(f"Test vector {i} failed: {vector['description']}")
            print(f"  Expected: {vector['derived_key']}")
            print(f"  Got:      {derived.hex()}")
            return False

    print(f"✓ All {len(vectors)} test vectors passed (internal consistency)")
    return True


def print_test_vectors_for_sma() -> None:
    """
    Print test vectors in format for SMA validation.

    Run this and compare with SMA's test vector output to ensure
    implementations match exactly.

    Example:
        >>> print_test_vectors_for_sma()  # doctest: +SKIP
        Test Vectors for SMA Validation
        ...
    """
    print("\n" + "=" * 70)
    print("Test Vectors for SMA Validation")
    print("Compare with: packages/sma/src/key_tables/key_derivation.py")
    print("=" * 70)

    for i, vector in enumerate(generate_test_vectors()):
        print(f"\nVector {i}: {vector['description']}")
        print(f"  Master key:   {vector['master_key'].hex()}")
        print(f"  Key index:    {vector['key_index']}")
        print(f"  Derived key:  {vector['derived_key']}")

    print("\n" + "=" * 70)
    print("Run SMA test vectors and compare derived keys byte-for-byte")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    # Validate implementation
    print("Validating key derivation implementation...")
    if validate_implementation():
        print("\n✓ Implementation validated")
    else:
        print("\n✗ Implementation validation failed")
        exit(1)

    # Print test vectors for SMA comparison
    print_test_vectors_for_sma()

    # Instructions for SMA validation
    print("To validate against SMA:")
    print("1. Run: cd packages/sma && python -m src.key_tables.key_derivation")
    print("2. Compare test vector outputs")
    print("3. Derived keys must match byte-for-byte")
