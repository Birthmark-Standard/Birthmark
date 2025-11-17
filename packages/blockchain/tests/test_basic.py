"""Basic tests for Birthmark blockchain components."""

import pytest
from src.shared.crypto.hashing import (
    sha256_hex,
    compute_block_hash,
    compute_transaction_hash,
    verify_hash_format,
)
from src.shared.crypto.signatures import ValidatorKeys


class TestHashing:
    """Test cryptographic hashing functions."""

    def test_sha256_hex(self):
        """Test SHA-256 hashing."""
        data = b"Hello, Birthmark!"
        hash_result = sha256_hex(data)

        assert isinstance(hash_result, str)
        assert len(hash_result) == 64
        assert verify_hash_format(hash_result)

    def test_compute_block_hash_deterministic(self):
        """Test block hash is deterministic."""
        hash1 = compute_block_hash(
            block_height=1,
            previous_hash="0" * 64,
            timestamp=1700000000,
            transaction_hashes=["abc123", "def456"],
            validator_id="test_validator",
        )

        hash2 = compute_block_hash(
            block_height=1,
            previous_hash="0" * 64,
            timestamp=1700000000,
            transaction_hashes=["abc123", "def456"],
            validator_id="test_validator",
        )

        assert hash1 == hash2
        assert len(hash1) == 64

    def test_compute_transaction_hash(self):
        """Test transaction hash computation."""
        tx_hash = compute_transaction_hash(
            image_hashes=["hash1", "hash2", "hash3"],
            timestamps=[1700000000, 1700000001, 1700000002],
            aggregator_id="test_agg",
        )

        assert isinstance(tx_hash, str)
        assert len(tx_hash) == 64
        assert verify_hash_format(tx_hash)

    def test_verify_hash_format(self):
        """Test hash format validation."""
        assert verify_hash_format("a" * 64)
        assert verify_hash_format("1234567890abcdef" * 4)
        assert not verify_hash_format("z" * 64)  # Invalid hex
        assert not verify_hash_format("a" * 63)  # Too short
        assert not verify_hash_format("a" * 65)  # Too long
        assert not verify_hash_format(123)  # Not a string


class TestSignatures:
    """Test cryptographic signatures."""

    def test_generate_keys(self):
        """Test key generation."""
        keys = ValidatorKeys.generate()
        assert keys.private_key is not None
        assert keys.public_key is not None

    def test_sign_and_verify(self):
        """Test signing and verification."""
        keys = ValidatorKeys.generate()
        data = b"Test message for signing"

        signature = keys.sign(data)
        assert isinstance(signature, str)
        assert len(signature) > 0

        # Verify with same keys
        assert keys.verify(data, signature)

        # Verify fails with different data
        assert not keys.verify(b"Different data", signature)

    def test_public_key_export(self):
        """Test public key export."""
        keys = ValidatorKeys.generate()
        pem = keys.get_public_key_pem()

        assert isinstance(pem, str)
        assert "BEGIN PUBLIC KEY" in pem
        assert "END PUBLIC KEY" in pem


@pytest.mark.asyncio
class TestModels:
    """Test Pydantic models."""

    def test_authentication_bundle_validation(self):
        """Test AuthenticationBundle validation."""
        from src.shared.models.schemas import AuthenticationBundle

        # Valid bundle
        bundle = AuthenticationBundle(
            image_hash="a" * 64,
            encrypted_nuc_token=b"encrypted_data",
            table_references=[0, 100, 2499],
            key_indices=[0, 500, 999],
            timestamp=1700000000,
            device_signature=b"signature",
        )

        assert bundle.image_hash == "a" * 64
        assert len(bundle.table_references) == 3
        assert len(bundle.key_indices) == 3

    def test_authentication_bundle_invalid_hash(self):
        """Test invalid hash format."""
        from src.shared.models.schemas import AuthenticationBundle
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AuthenticationBundle(
                image_hash="invalid",  # Too short
                encrypted_nuc_token=b"encrypted_data",
                table_references=[0, 100, 200],
                key_indices=[0, 500, 999],
                timestamp=1700000000,
                device_signature=b"signature",
            )

    def test_verification_response(self):
        """Test VerificationResponse model."""
        from src.shared.models.schemas import VerificationResponse

        # Verified response
        response = VerificationResponse(
            verified=True,
            image_hash="a" * 64,
            timestamp=1700000000,
            block_height=123,
            aggregator="test_agg",
        )

        assert response.verified is True
        assert response.block_height == 123

        # Not verified
        response = VerificationResponse(
            verified=False,
            image_hash="b" * 64,
        )

        assert response.verified is False
        assert response.timestamp is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
