# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Tests for owner attribution system.

Tests the generation and verification of owner metadata for Birthmark photos.
"""

import pytest
import hashlib
from camera_pi.owner_attribution import (
    generate_owner_metadata,
    verify_owner_metadata,
    encode_salt_for_exif,
    decode_salt_from_exif
)


def test_generate_owner_metadata():
    """Test generation of owner metadata."""
    owner_name = "Jane Smith"
    metadata = generate_owner_metadata(owner_name)

    # Check fields
    assert metadata.owner_name == owner_name
    assert len(metadata.owner_salt) == 32  # 32 bytes
    assert len(metadata.owner_hash) == 64  # SHA-256 hex = 64 chars

    # Hash should be valid hex
    int(metadata.owner_hash, 16)


def test_owner_metadata_uniqueness():
    """Test that each photo gets a unique owner hash."""
    owner_name = "Jane Smith"

    # Generate 10 metadata instances
    hashes = set()
    for _ in range(10):
        metadata = generate_owner_metadata(owner_name)
        hashes.add(metadata.owner_hash)

    # All hashes should be unique (different salts)
    assert len(hashes) == 10


def test_verify_owner_metadata_valid():
    """Test verification of valid owner metadata."""
    owner_name = "Jane Smith - Reuters"
    metadata = generate_owner_metadata(owner_name)

    # Verification should pass
    valid = verify_owner_metadata(
        metadata.owner_name,
        metadata.owner_salt,
        metadata.owner_hash
    )
    assert valid is True


def test_verify_owner_metadata_tampered_name():
    """Test verification fails with tampered owner name."""
    metadata = generate_owner_metadata("Jane Smith")

    # Try to verify with different name
    valid = verify_owner_metadata(
        "John Doe",  # Wrong name
        metadata.owner_salt,
        metadata.owner_hash
    )
    assert valid is False


def test_verify_owner_metadata_tampered_salt():
    """Test verification fails with tampered salt."""
    import secrets

    metadata = generate_owner_metadata("Jane Smith")

    # Try to verify with different salt
    fake_salt = secrets.token_bytes(32)
    valid = verify_owner_metadata(
        metadata.owner_name,
        fake_salt,  # Wrong salt
        metadata.owner_hash
    )
    assert valid is False


def test_verify_owner_metadata_tampered_hash():
    """Test verification fails with tampered hash."""
    metadata = generate_owner_metadata("Jane Smith")

    # Try to verify with different hash
    fake_hash = "a" * 64
    valid = verify_owner_metadata(
        metadata.owner_name,
        metadata.owner_salt,
        fake_hash  # Wrong hash
    )
    assert valid is False


def test_encode_decode_salt():
    """Test encoding and decoding of salt for EXIF."""
    import secrets

    original_salt = secrets.token_bytes(32)

    # Encode to base64
    salt_b64 = encode_salt_for_exif(original_salt)
    assert isinstance(salt_b64, str)

    # Decode back
    decoded_salt = decode_salt_from_exif(salt_b64)
    assert decoded_salt == original_salt


def test_decode_invalid_salt():
    """Test decoding invalid salt raises error."""
    # Invalid base64
    with pytest.raises(ValueError):
        decode_salt_from_exif("not-valid-base64!@#$")

    # Valid base64 but wrong length
    import base64
    short_salt = base64.b64encode(b"tooshort").decode('utf-8')
    with pytest.raises(ValueError):
        decode_salt_from_exif(short_salt)


def test_empty_owner_name():
    """Test that empty owner name raises error."""
    with pytest.raises(ValueError):
        generate_owner_metadata("")

    with pytest.raises(ValueError):
        generate_owner_metadata("   ")  # Only whitespace


def test_owner_hash_deterministic():
    """Test that hash is deterministic for same name + salt."""
    owner_name = "Jane Smith"
    import secrets
    salt = secrets.token_bytes(32)

    # Compute hash manually
    hash_input = owner_name.encode('utf-8') + salt
    expected_hash = hashlib.sha256(hash_input).hexdigest()

    # Verify should match
    valid = verify_owner_metadata(owner_name, salt, expected_hash)
    assert valid is True


def test_owner_metadata_privacy():
    """Test that different images from same owner have different hashes."""
    owner_name = "Jane Smith - Reuters"

    # Simulate 3 photos from same photographer
    photo1 = generate_owner_metadata(owner_name)
    photo2 = generate_owner_metadata(owner_name)
    photo3 = generate_owner_metadata(owner_name)

    # All should have same name
    assert photo1.owner_name == photo2.owner_name == photo3.owner_name

    # But different salts and hashes (privacy)
    assert photo1.owner_salt != photo2.owner_salt != photo3.owner_salt
    assert photo1.owner_hash != photo2.owner_hash != photo3.owner_hash


def test_special_characters_in_name():
    """Test owner names with special characters."""
    test_names = [
        "José García",
        "李明",  # Chinese characters
        "Müller",  # German umlaut
        "O'Brien",  # Apostrophe
        "Smith & Jones",  # Ampersand
        "test@email.com",  # Email
    ]

    for name in test_names:
        metadata = generate_owner_metadata(name)
        assert metadata.owner_name == name

        # Verification should work
        valid = verify_owner_metadata(
            metadata.owner_name,
            metadata.owner_salt,
            metadata.owner_hash
        )
        assert valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
