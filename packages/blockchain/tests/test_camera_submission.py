"""Tests for camera submission with 2-hash array format."""

import pytest
from datetime import datetime
import time

# Example test data for camera submissions
SAMPLE_CAMERA_SUBMISSION_2_HASHES = {
    "submission_type": "camera",
    "image_hashes": [
        {
            "image_hash": "a" * 64,  # Raw hash
            "modification_level": 0,
            "parent_image_hash": None,
        },
        {
            "image_hash": "b" * 64,  # Processed hash
            "modification_level": 1,
            "parent_image_hash": "a" * 64,
        },
    ],
    "camera_token": {
        "ciphertext": "c" * 128,
        "auth_tag": "d" * 32,
        "nonce": "e" * 24,
        "table_id": 42,
        "key_index": 123,
    },
    "manufacturer_cert": {
        "authority_id": "TEST_MFG_001",
        "validation_endpoint": "http://localhost:8001/validate",
    },
    "timestamp": int(time.time()),
}

SAMPLE_CAMERA_SUBMISSION_1_HASH = {
    "submission_type": "camera",
    "image_hashes": [
        {
            "image_hash": "f" * 64,  # Raw hash only
            "modification_level": 0,
            "parent_image_hash": None,
        },
    ],
    "camera_token": {
        "ciphertext": "g" * 128,
        "auth_tag": "h" * 32,
        "nonce": "i" * 24,
        "table_id": 84,
        "key_index": 456,
    },
    "manufacturer_cert": {
        "authority_id": "TEST_MFG_002",
        "validation_endpoint": "http://localhost:8001/validate",
    },
    "timestamp": int(time.time()),
}


class TestCameraSubmissionSchemas:
    """Test Pydantic validation for camera submission schemas."""

    def test_camera_token_validation(self):
        """Test CameraToken schema validation."""
        from src.shared.models.schemas import CameraToken

        # Valid token
        token = CameraToken(
            ciphertext="a" * 128,
            auth_tag="b" * 32,
            nonce="c" * 24,
            table_id=42,
            key_index=123,
        )
        assert token.table_id == 42
        assert token.key_index == 123

        # Invalid table_id (out of range)
        with pytest.raises(ValueError):
            CameraToken(
                ciphertext="a" * 128,
                auth_tag="b" * 32,
                nonce="c" * 24,
                table_id=250,  # Must be < 250
                key_index=123,
            )

        # Invalid key_index (out of range)
        with pytest.raises(ValueError):
            CameraToken(
                ciphertext="a" * 128,
                auth_tag="b" * 32,
                nonce="c" * 24,
                table_id=42,
                key_index=1000,  # Must be < 1000
            )

    def test_image_hash_entry_validation(self):
        """Test ImageHashEntry schema validation."""
        from src.shared.models.schemas import ImageHashEntry

        # Valid raw hash
        raw_entry = ImageHashEntry(
            image_hash="a" * 64,
            modification_level=0,
            parent_image_hash=None,
        )
        assert raw_entry.modification_level == 0
        assert raw_entry.parent_image_hash is None

        # Valid processed hash
        processed_entry = ImageHashEntry(
            image_hash="b" * 64,
            modification_level=1,
            parent_image_hash="a" * 64,
        )
        assert processed_entry.modification_level == 1
        assert processed_entry.parent_image_hash == "a" * 64

        # Invalid modification level
        with pytest.raises(ValueError):
            ImageHashEntry(
                image_hash="c" * 64,
                modification_level=2,  # Must be 0 or 1 for camera
                parent_image_hash=None,
            )

    def test_manufacturer_cert_validation(self):
        """Test ManufacturerCert schema validation."""
        from src.shared.models.schemas import ManufacturerCert

        # Valid cert
        cert = ManufacturerCert(
            authority_id="CANON_001",
            validation_endpoint="https://canon.birthmark.org/validate",
        )
        assert cert.authority_id == "CANON_001"

        # Invalid endpoint (not HTTP/HTTPS)
        with pytest.raises(ValueError):
            ManufacturerCert(
                authority_id="CANON_001",
                validation_endpoint="ftp://invalid.com",
            )

    def test_camera_submission_2_hashes(self):
        """Test CameraSubmission with 2 hashes (raw + processed)."""
        from src.shared.models.schemas import CameraSubmission

        submission = CameraSubmission(**SAMPLE_CAMERA_SUBMISSION_2_HASHES)
        assert len(submission.image_hashes) == 2
        assert submission.image_hashes[0].modification_level == 0
        assert submission.image_hashes[1].modification_level == 1
        assert submission.image_hashes[1].parent_image_hash == submission.image_hashes[0].image_hash

    def test_camera_submission_1_hash(self):
        """Test CameraSubmission with 1 hash (raw only)."""
        from src.shared.models.schemas import CameraSubmission

        submission = CameraSubmission(**SAMPLE_CAMERA_SUBMISSION_1_HASH)
        assert len(submission.image_hashes) == 1
        assert submission.image_hashes[0].modification_level == 0
        assert submission.image_hashes[0].parent_image_hash is None

    def test_camera_submission_invalid_order(self):
        """Test that processed hash must come after raw hash."""
        from src.shared.models.schemas import CameraSubmission

        invalid_submission = {
            "submission_type": "camera",
            "image_hashes": [
                {
                    "image_hash": "b" * 64,
                    "modification_level": 1,  # Processed first - invalid
                    "parent_image_hash": "a" * 64,
                },
                {
                    "image_hash": "a" * 64,
                    "modification_level": 0,
                    "parent_image_hash": None,
                },
            ],
            "camera_token": SAMPLE_CAMERA_SUBMISSION_2_HASHES["camera_token"],
            "manufacturer_cert": SAMPLE_CAMERA_SUBMISSION_2_HASHES["manufacturer_cert"],
            "timestamp": int(time.time()),
        }

        with pytest.raises(ValueError, match="First hash must be raw"):
            CameraSubmission(**invalid_submission)

    def test_camera_submission_missing_parent_reference(self):
        """Test that processed hash must reference raw hash as parent."""
        from src.shared.models.schemas import CameraSubmission

        invalid_submission = {
            "submission_type": "camera",
            "image_hashes": [
                {
                    "image_hash": "a" * 64,
                    "modification_level": 0,
                    "parent_image_hash": None,
                },
                {
                    "image_hash": "b" * 64,
                    "modification_level": 1,
                    "parent_image_hash": None,  # Should reference raw hash
                },
            ],
            "camera_token": SAMPLE_CAMERA_SUBMISSION_2_HASHES["camera_token"],
            "manufacturer_cert": SAMPLE_CAMERA_SUBMISSION_2_HASHES["manufacturer_cert"],
            "timestamp": int(time.time()),
        }

        with pytest.raises(ValueError, match="Processed hash must have raw hash as parent"):
            CameraSubmission(**invalid_submission)


# Integration tests (require running server and database)
@pytest.mark.integration
class TestCameraSubmissionAPI:
    """Integration tests for camera submission API endpoint."""

    @pytest.mark.asyncio
    async def test_submit_2_hashes(self, client):
        """Test submitting camera bundle with 2 hashes."""
        response = await client.post(
            "/api/v1/submit",
            json=SAMPLE_CAMERA_SUBMISSION_2_HASHES,
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "pending_validation"
        assert "receipt_id" in data
        assert "transaction" in data["message"].lower() or "hashes" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_submit_1_hash(self, client):
        """Test submitting camera bundle with 1 hash (raw only)."""
        response = await client.post(
            "/api/v1/submit",
            json=SAMPLE_CAMERA_SUBMISSION_1_HASH,
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "pending_validation"
        assert "receipt_id" in data

    @pytest.mark.asyncio
    async def test_invalid_hash_format(self, client):
        """Test that invalid hash format is rejected."""
        invalid_submission = SAMPLE_CAMERA_SUBMISSION_2_HASHES.copy()
        invalid_submission["image_hashes"][0]["image_hash"] = "invalid_not_64_chars"

        response = await client.post(
            "/api/v1/submit",
            json=invalid_submission,
        )

        assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    # Run tests with: pytest tests/test_camera_submission.py -v
    pass
