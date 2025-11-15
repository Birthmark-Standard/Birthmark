"""
Standardized hashing utilities for Birthmark Standard.

All SHA-256 hashing in the Birthmark system uses these functions to ensure
consistency across components.
"""

import hashlib


def compute_sha256(data: bytes) -> str:
    """
    Compute SHA-256 hash of raw bytes.

    Args:
        data: Raw bytes to hash (e.g., raw Bayer sensor data)

    Returns:
        64-character hex string (lowercase)

    Example:
        >>> raw_sensor_data = b"..."  # 24MB of raw Bayer data
        >>> image_hash = compute_sha256(raw_sensor_data)
        >>> len(image_hash)
        64
    """
    return hashlib.sha256(data).hexdigest()


def compute_sha256_bytes(data: bytes) -> bytes:
    """
    Compute SHA-256 hash and return as raw bytes.

    Args:
        data: Raw bytes to hash

    Returns:
        32 bytes (256 bits) of hash output

    Example:
        >>> nuc_map = b"..."  # Raw NUC correction map
        >>> nuc_hash = compute_sha256_bytes(nuc_map)
        >>> len(nuc_hash)
        32
    """
    return hashlib.sha256(data).digest()


def verify_hash_format(hash_string: str) -> bool:
    """
    Verify that a string is a valid SHA-256 hash.

    Args:
        hash_string: String to validate

    Returns:
        True if valid 64-char hex string, False otherwise

    Example:
        >>> verify_hash_format("a1b2c3..." * 21 + "de")  # 64 chars
        True
        >>> verify_hash_format("not a hash")
        False
    """
    if len(hash_string) != 64:
        return False
    try:
        int(hash_string, 16)
        return True
    except ValueError:
        return False
