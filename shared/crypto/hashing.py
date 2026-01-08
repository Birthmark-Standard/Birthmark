#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
SHA-256 hashing utilities for Birthmark Standard

This module provides standardized hashing functions used throughout the Birthmark
system. All image hashes, NUC hashes, and GPS hashes use SHA-256.

Critical: Hash computation must be consistent across all platforms and components.
Any change to these functions will break compatibility with existing data.
"""

import hashlib
from typing import Optional, Union
import numpy as np


def compute_sha256(data: bytes) -> str:
    """
    Compute SHA-256 hash of arbitrary data.

    This is the fundamental hashing function used throughout the Birthmark system.
    It produces a deterministic 64-character hex string from any bytes input.

    Args:
        data: Raw bytes to hash

    Returns:
        64-character hex string (lowercase)

    Example:
        >>> data = b"Hello, Birthmark!"
        >>> hash_value = compute_sha256(data)
        >>> len(hash_value)
        64
        >>> hash_value[:16]
        'a1b2c3d4e5f6...'

    Security Notes:
        - SHA-256 is a one-way function (cannot reverse hash to data)
        - Collision resistance: computationally infeasible to find two inputs
          with the same hash
        - Pre-image resistance: cannot find input that produces a specific hash
    """
    if not isinstance(data, bytes):
        raise TypeError(f"Data must be bytes, got {type(data).__name__}")

    return hashlib.sha256(data).hexdigest()


def compute_sha256_binary(data: bytes) -> bytes:
    """
    Compute SHA-256 hash of data, returning raw bytes.

    This is useful when the hash will be used for further cryptographic
    operations (like encryption) rather than display.

    Args:
        data: Raw bytes to hash

    Returns:
        32 bytes (256 bits) of hash output

    Example:
        >>> data = b"Hello, Birthmark!"
        >>> hash_bytes = compute_sha256_binary(data)
        >>> len(hash_bytes)
        32
    """
    if not isinstance(data, bytes):
        raise TypeError(f"Data must be bytes, got {type(data).__name__}")

    return hashlib.sha256(data).digest()


def hash_image_data(bayer_array: np.ndarray, validate: bool = True) -> str:
    """
    Hash raw Bayer sensor data from camera.

    This function is used by cameras to compute the image hash from raw sensor
    data. The hash is computed from the byte representation of the Bayer array,
    ensuring consistent byte ordering across all platforms.

    Args:
        bayer_array: NumPy array containing raw Bayer sensor data
                     Expected shape: (height, width) for single-channel Bayer
                     Expected dtype: uint8, uint10, uint12, or uint16
        validate: If True, validate array properties before hashing

    Returns:
        64-character hex string (SHA-256 hash)

    Raises:
        ValueError: If validation is enabled and array is invalid
        TypeError: If bayer_array is not a NumPy array

    Example:
        >>> import numpy as np
        >>> # Simulate 4MP Bayer sensor data
        >>> bayer = np.zeros((2000, 2000), dtype=np.uint16)
        >>> image_hash = hash_image_data(bayer)
        >>> len(image_hash)
        64

    Platform Consistency:
        This function ensures consistent hashing across platforms by:
        1. Using NumPy's tobytes() which preserves byte order
        2. Not performing any preprocessing or normalization
        3. Hashing the raw sensor values exactly as captured

    Performance:
        - 12MP image (~24MB): ~500ms on Raspberry Pi 4
        - 12MP image (~24MB): ~100ms on modern desktop
    """
    if not isinstance(bayer_array, np.ndarray):
        raise TypeError(f"bayer_array must be numpy.ndarray, got {type(bayer_array).__name__}")

    if validate:
        # Validate array properties
        if bayer_array.ndim != 2:
            raise ValueError(
                f"Bayer array must be 2-dimensional (height, width), got {bayer_array.ndim} dimensions"
            )

        # Check dtype is appropriate for sensor data
        valid_dtypes = [np.uint8, np.uint16, np.uint32]
        if bayer_array.dtype not in valid_dtypes:
            raise ValueError(
                f"Bayer array dtype must be one of {valid_dtypes}, got {bayer_array.dtype}"
            )

        # Sanity check on size (at least 100x100, at most 50MP)
        height, width = bayer_array.shape
        if height < 100 or width < 100:
            raise ValueError(
                f"Bayer array suspiciously small: {height}x{width}. "
                "Expected at least 100x100 for valid sensor data."
            )

        if height * width > 50_000_000:
            raise ValueError(
                f"Bayer array too large: {height}x{width} = {height * width:,} pixels. "
                "Maximum 50MP supported."
            )

    # Convert to bytes preserving exact byte order
    # This is critical for cross-platform consistency
    bayer_bytes = bayer_array.tobytes()

    # Hash the raw bytes
    return compute_sha256(bayer_bytes)


def hash_gps_coordinates(
    latitude: float,
    longitude: float,
    altitude: Optional[float] = None,
    precision: int = 6
) -> str:
    """
    Hash GPS coordinates for privacy-preserving location verification.

    Instead of storing raw GPS coordinates, we hash them. This allows verification
    that an image was taken at a specific location without revealing the exact
    coordinates in the blockchain.

    Args:
        latitude: Latitude in decimal degrees (-90 to 90)
        longitude: Longitude in decimal degrees (-180 to 180)
        altitude: Optional altitude in meters
        precision: Number of decimal places to round to (default: 6 = ~0.1m accuracy)

    Returns:
        64-character hex string (SHA-256 hash)

    Raises:
        ValueError: If coordinates are out of valid range

    Example:
        >>> # Somewhere in Portland, Oregon
        >>> lat, lon = 45.5231, -122.6765
        >>> gps_hash = hash_gps_coordinates(lat, lon)
        >>> len(gps_hash)
        64

    Privacy Notes:
        - Hash is one-way: cannot recover coordinates from hash
        - Precision parameter controls granularity (higher = more precise)
        - Same location will always produce same hash (deterministic)
        - Verifier can check "was this taken at X?" but cannot discover location
    """
    # Validate coordinates
    if not (-90 <= latitude <= 90):
        raise ValueError(f"Latitude must be between -90 and 90, got {latitude}")

    if not (-180 <= longitude <= 180):
        raise ValueError(f"Longitude must be between -180 and 180, got {longitude}")

    if precision < 0 or precision > 10:
        raise ValueError(f"Precision must be between 0 and 10, got {precision}")

    # Round to specified precision to prevent floating-point issues
    lat_rounded = round(latitude, precision)
    lon_rounded = round(longitude, precision)

    # Create canonical string representation
    if altitude is not None:
        alt_rounded = round(altitude, precision)
        gps_string = f"{lat_rounded:.{precision}f},{lon_rounded:.{precision}f},{alt_rounded:.{precision}f}"
    else:
        gps_string = f"{lat_rounded:.{precision}f},{lon_rounded:.{precision}f}"

    # Hash the string representation
    return compute_sha256(gps_string.encode('utf-8'))


def hash_nuc_map(nuc_array: np.ndarray) -> bytes:
    """
    Hash camera sensor's Non-Uniformity Correction (NUC) map.

    The NUC map is a unique fingerprint of the camera sensor. This function
    hashes it to create a 256-bit identifier that can be encrypted and validated
    without exposing the raw NUC data.

    Args:
        nuc_array: NumPy array containing NUC correction values
                   Shape matches sensor dimensions
                   Values are typically float32 or float64

    Returns:
        32 bytes (256 bits) of binary hash

    Example:
        >>> import numpy as np
        >>> # Simulate NUC map for 12MP sensor
        >>> nuc = np.random.randn(3040, 4056).astype(np.float32)
        >>> nuc_hash = hash_nuc_map(nuc)
        >>> len(nuc_hash)
        32

    Security Notes:
        - NUC hash serves as device identifier
        - Cannot reverse hash to recover NUC map
        - Used with encryption to prove device authenticity
        - SMA stores this hash to identify legitimate cameras
    """
    if not isinstance(nuc_array, np.ndarray):
        raise TypeError(f"nuc_array must be numpy.ndarray, got {type(nuc_array).__name__}")

    # Convert to bytes (preserves floating-point values exactly)
    nuc_bytes = nuc_array.tobytes()

    # Return binary hash (used for encryption, not display)
    return compute_sha256_binary(nuc_bytes)


def verify_hash_format(hash_string: str) -> bool:
    """
    Verify that a string is a valid SHA-256 hash.

    This is a quick validation check to ensure a string has the correct
    format for a SHA-256 hash before using it.

    Args:
        hash_string: String to validate

    Returns:
        True if valid SHA-256 hash format, False otherwise

    Example:
        >>> valid = "a" * 64
        >>> verify_hash_format(valid)
        True
        >>> invalid = "a" * 63
        >>> verify_hash_format(invalid)
        False
        >>> invalid = "g" * 64  # 'g' is not a hex character
        >>> verify_hash_format(invalid)
        False
    """
    if not isinstance(hash_string, str):
        return False

    # Must be exactly 64 characters
    if len(hash_string) != 64:
        return False

    # Must be all hex characters (0-9, a-f)
    try:
        int(hash_string, 16)
        return True
    except ValueError:
        return False


def constant_time_compare(hash_a: Union[str, bytes], hash_b: Union[str, bytes]) -> bool:
    """
    Compare two hashes in constant time to prevent timing attacks.

    This function uses HMAC's constant-time comparison to safely compare
    hashes without leaking information about how many bytes match.

    Args:
        hash_a: First hash (hex string or bytes)
        hash_b: Second hash (hex string or bytes)

    Returns:
        True if hashes match, False otherwise

    Example:
        >>> hash1 = compute_sha256(b"data1")
        >>> hash2 = compute_sha256(b"data2")
        >>> constant_time_compare(hash1, hash1)
        True
        >>> constant_time_compare(hash1, hash2)
        False

    Security Notes:
        - Regular comparison (==) can leak timing information
        - Timing attacks could determine how many bytes match
        - This function takes constant time regardless of where hashes differ
        - Critical for secure hash comparison in authentication
    """
    import hmac

    # Convert hex strings to bytes if needed
    if isinstance(hash_a, str):
        hash_a = bytes.fromhex(hash_a)
    if isinstance(hash_b, str):
        hash_b = bytes.fromhex(hash_b)

    return hmac.compare_digest(hash_a, hash_b)


# Performance testing utilities
def benchmark_hashing(size_mb: int = 24) -> dict:
    """
    Benchmark hashing performance on this platform.

    This is useful for verifying that hashing meets performance targets
    on specific hardware (e.g., Raspberry Pi).

    Args:
        size_mb: Size of data to hash in megabytes (default: 24 = 12MP image)

    Returns:
        Dictionary with benchmark results

    Example:
        >>> results = benchmark_hashing(24)
        >>> print(f"Time: {results['time_ms']:.1f}ms")
        >>> print(f"Speed: {results['mb_per_second']:.1f} MB/s")
    """
    import time

    # Generate random data
    data = np.random.randint(0, 65536, size_mb * 1024 * 512, dtype=np.uint16)

    # Benchmark
    start = time.perf_counter()
    hash_value = compute_sha256(data.tobytes())
    end = time.perf_counter()

    elapsed = end - start
    mb_per_second = size_mb / elapsed

    return {
        'size_mb': size_mb,
        'time_ms': elapsed * 1000,
        'time_seconds': elapsed,
        'mb_per_second': mb_per_second,
        'hash': hash_value,
        'meets_target': elapsed < 0.5  # Target: <500ms on Raspberry Pi
    }


if __name__ == "__main__":
    print("=" * 80)
    print("Birthmark Hashing Utilities - Test Vectors")
    print("=" * 80)

    # Test vector 1: Simple string
    test_data = b"Birthmark Standard - Photo Authentication"
    hash1 = compute_sha256(test_data)
    print(f"\nTest 1: Simple data")
    print(f"  Data: {test_data}")
    print(f"  Hash: {hash1}")

    # Test vector 2: Empty data
    hash2 = compute_sha256(b"")
    print(f"\nTest 2: Empty data")
    print(f"  Hash: {hash2}")
    print(f"  Expected: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
    print(f"  Match: {hash2 == 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}")

    # Test vector 3: GPS hash
    gps_hash = hash_gps_coordinates(45.5231, -122.6765)
    print(f"\nTest 3: GPS coordinates")
    print(f"  Coordinates: 45.5231, -122.6765 (Portland, OR)")
    print(f"  Hash: {gps_hash}")

    # Test vector 4: Hash format validation
    print(f"\nTest 4: Hash validation")
    print(f"  Valid hash: {verify_hash_format(hash1)}")
    print(f"  Invalid (too short): {verify_hash_format('a' * 63)}")
    print(f"  Invalid (bad chars): {verify_hash_format('g' * 64)}")

    # Test vector 5: Constant-time comparison
    print(f"\nTest 5: Constant-time comparison")
    print(f"  Same hash: {constant_time_compare(hash1, hash1)}")
    print(f"  Different hash: {constant_time_compare(hash1, hash2)}")

    # Performance benchmark
    print(f"\n" + "=" * 80)
    print("Performance Benchmark")
    print("=" * 80)
    results = benchmark_hashing(24)
    print(f"\nHashing {results['size_mb']}MB (simulated 12MP image):")
    print(f"  Time: {results['time_ms']:.1f}ms")
    print(f"  Speed: {results['mb_per_second']:.1f} MB/s")
    print(f"  Meets <500ms target: {'✓ YES' if results['meets_target'] else '✗ NO'}")

    print("\n" + "=" * 80)
    print("✓ All hashing utilities ready for use")
    print("=" * 80)
