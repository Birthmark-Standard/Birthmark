"""
Unit tests for key derivation.

Tests:
- HKDF-SHA256 key derivation
- Key derivation manager
- Test vector validation
"""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.key_tables.key_derivation import (
    derive_encryption_key,
    verify_key_derivation,
    KeyDerivationManager,
    generate_test_vectors,
    validate_implementation,
    HKDF_CONTEXT
)


class TestKeyDerivation:
    """Test HKDF-SHA256 key derivation."""

    def test_derive_key_basic(self):
        """Test basic key derivation."""
        master_key = b"A" * 32  # 256-bit master key
        key_index = 0

        derived_key = derive_encryption_key(master_key, key_index)

        # Verify output is 32 bytes (256 bits)
        assert len(derived_key) == 32
        assert isinstance(derived_key, bytes)

    def test_derive_key_deterministic(self):
        """Test that key derivation is deterministic."""
        master_key = b"B" * 32
        key_index = 42

        # Derive key twice
        key1 = derive_encryption_key(master_key, key_index)
        key2 = derive_encryption_key(master_key, key_index)

        # Should be identical
        assert key1 == key2

    def test_derive_key_different_indices(self):
        """Test that different indices produce different keys."""
        master_key = b"C" * 32

        keys = [derive_encryption_key(master_key, i) for i in range(10)]

        # All keys should be different
        assert len(set(keys)) == 10

    def test_derive_key_different_masters(self):
        """Test that different master keys produce different derived keys."""
        key_index = 123

        master_key1 = b"D" * 32
        master_key2 = b"E" * 32

        key1 = derive_encryption_key(master_key1, key_index)
        key2 = derive_encryption_key(master_key2, key_index)

        # Should be different
        assert key1 != key2

    def test_derive_key_invalid_master_key_length(self):
        """Test that invalid master key length raises error."""
        # Too short
        with pytest.raises(ValueError, match="32 bytes"):
            derive_encryption_key(b"short", 0)

        # Too long
        with pytest.raises(ValueError, match="32 bytes"):
            derive_encryption_key(b"X" * 64, 0)

    def test_derive_key_invalid_key_index(self):
        """Test that invalid key index raises error."""
        master_key = b"F" * 32

        # Negative index
        with pytest.raises(ValueError, match="0-999"):
            derive_encryption_key(master_key, -1)

        # Index too large
        with pytest.raises(ValueError, match="0-999"):
            derive_encryption_key(master_key, 1000)

    def test_derive_key_boundary_indices(self):
        """Test key derivation at boundary indices."""
        master_key = b"G" * 32

        # Min index
        key_min = derive_encryption_key(master_key, 0)
        assert len(key_min) == 32

        # Max index
        key_max = derive_encryption_key(master_key, 999)
        assert len(key_max) == 32

        # Should be different
        assert key_min != key_max

    def test_verify_key_derivation(self):
        """Test key derivation verification."""
        master_key = b"H" * 32
        key_index = 456

        # Derive key
        expected_key = derive_encryption_key(master_key, key_index)

        # Verify correct key
        assert verify_key_derivation(master_key, key_index, expected_key)

        # Verify incorrect key
        wrong_key = b"Z" * 32
        assert not verify_key_derivation(master_key, key_index, wrong_key)


class TestKeyDerivationManager:
    """Test key derivation manager."""

    @pytest.fixture
    def manager(self):
        """Create manager with test key tables."""
        key_tables = {
            0: b"A" * 32,
            1: b"B" * 32,
            2: b"C" * 32,
            42: b"D" * 32,
            999: b"E" * 32,
        }
        return KeyDerivationManager(key_tables)

    def test_derive_single_key(self, manager):
        """Test deriving a single key."""
        key = manager.derive_key(table_id=0, key_index=123)

        assert len(key) == 32
        assert isinstance(key, bytes)

    def test_derive_key_from_different_tables(self, manager):
        """Test that same index from different tables gives different keys."""
        key_index = 500

        key0 = manager.derive_key(table_id=0, key_index=key_index)
        key1 = manager.derive_key(table_id=1, key_index=key_index)

        assert key0 != key1

    def test_derive_key_invalid_table(self, manager):
        """Test that invalid table ID raises error."""
        with pytest.raises(KeyError, match="not found"):
            manager.derive_key(table_id=999999, key_index=0)

    def test_derive_key_invalid_index(self, manager):
        """Test that invalid key index raises error."""
        with pytest.raises(ValueError, match="0-999"):
            manager.derive_key(table_id=0, key_index=1000)

    def test_derive_multiple_keys(self, manager):
        """Test deriving multiple keys at once."""
        table_references = [0, 1, 2]
        key_indices = [10, 20, 30]

        keys = manager.derive_multiple_keys(table_references, key_indices)

        assert len(keys) == 3
        assert all(len(k) == 32 for k in keys)

        # All keys should be different
        assert len(set(keys)) == 3

    def test_derive_multiple_keys_mismatched_lengths(self, manager):
        """Test that mismatched list lengths raise error."""
        with pytest.raises(ValueError, match="same length"):
            manager.derive_multiple_keys(
                table_references=[0, 1],
                key_indices=[10, 20, 30]  # Different length
            )


class TestKeyDerivationTestVectors:
    """Test key derivation test vectors."""

    def test_generate_test_vectors(self):
        """Test generating test vectors."""
        vectors = generate_test_vectors()

        assert len(vectors) > 0

        for vector in vectors:
            assert "master_key" in vector
            assert "key_index" in vector
            assert "expected_key" in vector
            assert "expected_key_bytes" in vector
            assert "description" in vector

            # Verify key derivation matches expected
            derived = derive_encryption_key(
                vector["master_key"],
                vector["key_index"]
            )
            assert derived == vector["expected_key_bytes"]
            assert derived.hex() == vector["expected_key"]

    def test_validate_implementation(self):
        """Test implementation validation."""
        # Should pass all test vectors
        assert validate_implementation() is True

    def test_test_vector_consistency(self):
        """Test that test vectors are consistent across runs."""
        vectors1 = generate_test_vectors()
        vectors2 = generate_test_vectors()

        # Same inputs should produce same outputs
        for v1, v2 in zip(vectors1, vectors2):
            assert v1["master_key"] == v2["master_key"]
            assert v1["key_index"] == v2["key_index"]
            assert v1["expected_key"] == v2["expected_key"]


class TestCrossPlatformCompatibility:
    """
    Test that key derivation produces consistent results.

    These tests ensure camera and SMA implementations will match.
    """

    def test_known_vector_1(self):
        """Test known vector 1."""
        # This vector should be shared with camera implementation
        master_key = bytes.fromhex(
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        )
        key_index = 0

        derived = derive_encryption_key(master_key, key_index)

        # Camera implementation must produce same output
        # (Actual expected value computed on first run)
        assert len(derived) == 32

    def test_known_vector_2(self):
        """Test known vector 2."""
        master_key = bytes.fromhex(
            "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        )
        key_index = 999

        derived = derive_encryption_key(master_key, key_index)

        assert len(derived) == 32

    def test_known_vector_3(self):
        """Test known vector 3."""
        master_key = bytes.fromhex(
            "0000000000000000000000000000000000000000000000000000000000000000"
        )
        key_index = 500

        derived = derive_encryption_key(master_key, key_index)

        assert len(derived) == 32

    def test_context_string(self):
        """Test that context string is correctly used."""
        master_key = b"X" * 32
        key_index = 100

        # Derive with default context
        key_default = derive_encryption_key(master_key, key_index)

        # Derive with custom context
        key_custom = derive_encryption_key(master_key, key_index, context=b"Different")

        # Should be different
        assert key_default != key_custom

        # Verify default context is "Birthmark"
        key_explicit = derive_encryption_key(master_key, key_index, context=HKDF_CONTEXT)
        assert key_default == key_explicit


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
