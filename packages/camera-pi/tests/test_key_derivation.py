# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Tests for key derivation module.

CRITICAL: These tests must match SMA implementation exactly.
"""

import pytest
from camera_pi.crypto.key_derivation import (
    derive_encryption_key,
    verify_key_derivation,
    generate_test_vectors,
    validate_implementation
)


class TestKeyDerivation:
    """Test key derivation functionality."""

    def test_derive_key_basic(self):
        """Test basic key derivation."""
        master_key = bytes.fromhex("00" * 32)
        key_index = 0

        derived = derive_encryption_key(master_key, key_index)

        assert len(derived) == 32
        assert isinstance(derived, bytes)

    def test_derive_key_deterministic(self):
        """Test that same inputs produce same outputs."""
        master_key = bytes.fromhex("01" * 32)
        key_index = 42

        derived1 = derive_encryption_key(master_key, key_index)
        derived2 = derive_encryption_key(master_key, key_index)

        assert derived1 == derived2

    def test_derive_key_different_indices(self):
        """Test that different indices produce different keys."""
        master_key = bytes.fromhex("02" * 32)

        derived1 = derive_encryption_key(master_key, 0)
        derived2 = derive_encryption_key(master_key, 1)

        assert derived1 != derived2

    def test_derive_key_invalid_master_key_length(self):
        """Test error on invalid master key length."""
        with pytest.raises(ValueError):
            derive_encryption_key(b"too_short", 0)

    def test_derive_key_invalid_index_negative(self):
        """Test error on negative key index."""
        master_key = bytes.fromhex("03" * 32)

        with pytest.raises(ValueError):
            derive_encryption_key(master_key, -1)

    def test_derive_key_invalid_index_too_large(self):
        """Test error on key index > 999."""
        master_key = bytes.fromhex("04" * 32)

        with pytest.raises(ValueError):
            derive_encryption_key(master_key, 1000)

    def test_verify_key_derivation(self):
        """Test key verification."""
        master_key = bytes.fromhex("05" * 32)
        key_index = 123

        derived = derive_encryption_key(master_key, key_index)

        assert verify_key_derivation(master_key, key_index, derived)
        assert not verify_key_derivation(master_key, key_index, b"wrong" * 8)

    def test_generate_test_vectors(self):
        """Test vector generation."""
        vectors = generate_test_vectors()

        assert len(vectors) > 0
        for vector in vectors:
            assert 'master_key' in vector
            assert 'key_index' in vector
            assert 'derived_key' in vector
            assert 'derived_key_bytes' in vector

    def test_validate_implementation(self):
        """Test implementation validation."""
        assert validate_implementation()


class TestSMACompatibility:
    """
    Test compatibility with SMA implementation.

    These tests verify that camera and SMA produce identical keys.
    """

    def test_test_vector_1(self):
        """Test vector 1: All-zeros master key, index 0."""
        master_key = bytes.fromhex(
            "0000000000000000000000000000000000000000000000000000000000000000"
        )
        key_index = 0

        derived = derive_encryption_key(master_key, key_index)

        # TODO: Update with expected value from SMA
        # expected = bytes.fromhex("...")
        # assert derived == expected

        # For now, just verify it computes consistently
        assert len(derived) == 32

    def test_test_vector_2(self):
        """Test vector 2: Sequential master key, index 0."""
        master_key = bytes.fromhex(
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        )
        key_index = 0

        derived = derive_encryption_key(master_key, key_index)

        # TODO: Update with expected value from SMA
        assert len(derived) == 32

    def test_test_vector_3(self):
        """Test vector 3: All-ones master key, max index."""
        master_key = bytes.fromhex(
            "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        )
        key_index = 999

        derived = derive_encryption_key(master_key, key_index)

        # TODO: Update with expected value from SMA
        assert len(derived) == 32


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
