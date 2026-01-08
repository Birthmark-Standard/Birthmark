# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Integration tests for camera token validation.

Tests the complete validation flow:
1. Generate encrypted token with camera-side crypto
2. Validate token with SMA-side crypto
3. Verify PASS/FAIL outcomes
"""

import secrets
import pytest
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.key_tables.key_derivation import derive_encryption_key
from src.key_tables.table_manager import KeyTableManager
from src.identity.device_registry import DeviceRegistry, DeviceRegistration
from src.validation.token_validator import (
    TokenValidator,
    validate_camera_token,
    TokenValidationResult
)


class TestTokenValidation:
    """Test suite for token validation."""

    @pytest.fixture
    def setup_test_environment(self, tmp_path):
        """
        Set up test environment with key tables and registered devices.

        Returns:
            Tuple of (table_manager, device_registry, test_device_data)
        """
        # Create key table manager with 3 tables for testing
        key_tables_path = tmp_path / "key_tables.json"
        table_manager = KeyTableManager(
            total_tables=10,
            tables_per_device=3,
            storage_path=key_tables_path
        )

        # Generate master keys for tables
        table_manager.generate_all_tables()

        # Create device registry
        registry_path = tmp_path / "device_registry.json"
        device_registry = DeviceRegistry(storage_path=registry_path)

        # Create test device with known NUC hash
        test_nuc_hash = secrets.token_bytes(32)
        test_device = DeviceRegistration(
            device_serial="TEST-CAMERA-123",
            table_assignments=[3, 5, 7],
            device_family="Raspberry Pi",
            provisioned_at="2025-12-15T00:00:00",
            nuc_hash=test_nuc_hash.hex(),
            device_secret=test_nuc_hash.hex()
        )

        # Register device
        device_registry.register_device(test_device)
        device_registry.save_to_file()

        return (table_manager, device_registry, {
            'device': test_device,
            'nuc_hash': test_nuc_hash,
            'table_assignments': [3, 5, 7]
        })

    def test_valid_token_authentication(self, setup_test_environment):
        """Test that a valid token authenticates successfully."""
        table_manager, device_registry, test_data = setup_test_environment

        # Select a table assigned to the device
        table_id = test_data['table_assignments'][0]  # Table 3
        key_index = 42  # Random key index

        # Derive encryption key (camera side)
        master_key = table_manager.key_tables[table_id]
        encryption_key = derive_encryption_key(master_key, key_index)

        # Encrypt NUC hash (camera side)
        nuc_hash = test_data['nuc_hash']
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(encryption_key)
        ciphertext_with_tag = aesgcm.encrypt(nonce, nuc_hash, None)

        # Split ciphertext and auth tag
        ciphertext = ciphertext_with_tag[:-16]
        auth_tag = ciphertext_with_tag[-16:]

        # Validate token (SMA side)
        valid, message, device = validate_camera_token(
            table_manager=table_manager,
            device_registry=device_registry,
            ciphertext=ciphertext.hex(),
            auth_tag=auth_tag.hex(),
            nonce=nonce.hex(),
            table_id=table_id,
            key_index=key_index
        )

        # Assert validation succeeded
        assert valid is True, f"Token validation failed: {message}"
        assert device is not None, "Device not found"
        assert device.device_serial == "TEST-CAMERA-123"
        assert "validated successfully" in message.lower()

    def test_wrong_table_id(self, setup_test_environment):
        """Test that token with wrong table ID fails validation."""
        table_manager, device_registry, test_data = setup_test_environment

        # Use a table NOT assigned to the device
        table_id = 1  # Device has tables [3, 5, 7]
        key_index = 42

        # Derive encryption key
        master_key = table_manager.key_tables[table_id]
        encryption_key = derive_encryption_key(master_key, key_index)

        # Encrypt NUC hash
        nuc_hash = test_data['nuc_hash']
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(encryption_key)
        ciphertext_with_tag = aesgcm.encrypt(nonce, nuc_hash, None)

        ciphertext = ciphertext_with_tag[:-16]
        auth_tag = ciphertext_with_tag[-16:]

        # Validate token
        valid, message, device = validate_camera_token(
            table_manager=table_manager,
            device_registry=device_registry,
            ciphertext=ciphertext.hex(),
            auth_tag=auth_tag.hex(),
            nonce=nonce.hex(),
            table_id=table_id,
            key_index=key_index
        )

        # Assert validation failed
        assert valid is False
        assert "not assigned to table" in message.lower()

    def test_wrong_key_index(self, setup_test_environment):
        """Test that token encrypted with wrong key fails validation."""
        table_manager, device_registry, test_data = setup_test_environment

        # Use correct table but wrong key index
        table_id = test_data['table_assignments'][0]
        encrypt_key_index = 42
        decrypt_key_index = 99  # Different from encrypt

        # Derive encryption key with one index
        master_key = table_manager.key_tables[table_id]
        encryption_key = derive_encryption_key(master_key, encrypt_key_index)

        # Encrypt NUC hash
        nuc_hash = test_data['nuc_hash']
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(encryption_key)
        ciphertext_with_tag = aesgcm.encrypt(nonce, nuc_hash, None)

        ciphertext = ciphertext_with_tag[:-16]
        auth_tag = ciphertext_with_tag[-16:]

        # Try to validate with different key index
        valid, message, device = validate_camera_token(
            table_manager=table_manager,
            device_registry=device_registry,
            ciphertext=ciphertext.hex(),
            auth_tag=auth_tag.hex(),
            nonce=nonce.hex(),
            table_id=table_id,
            key_index=decrypt_key_index  # Wrong index!
        )

        # Assert validation failed
        assert valid is False
        assert "authentication failed" in message.lower()

    def test_tampered_ciphertext(self, setup_test_environment):
        """Test that tampered ciphertext fails validation."""
        table_manager, device_registry, test_data = setup_test_environment

        table_id = test_data['table_assignments'][0]
        key_index = 42

        # Encrypt valid token
        master_key = table_manager.key_tables[table_id]
        encryption_key = derive_encryption_key(master_key, key_index)
        nuc_hash = test_data['nuc_hash']
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(encryption_key)
        ciphertext_with_tag = aesgcm.encrypt(nonce, nuc_hash, None)

        ciphertext = bytearray(ciphertext_with_tag[:-16])
        auth_tag = ciphertext_with_tag[-16:]

        # Tamper with ciphertext
        ciphertext[0] ^= 0x01  # Flip one bit

        # Validate tampered token
        valid, message, device = validate_camera_token(
            table_manager=table_manager,
            device_registry=device_registry,
            ciphertext=bytes(ciphertext).hex(),
            auth_tag=auth_tag.hex(),
            nonce=nonce.hex(),
            table_id=table_id,
            key_index=key_index
        )

        # Assert validation failed
        assert valid is False
        assert "authentication failed" in message.lower()

    def test_unknown_device(self, setup_test_environment):
        """Test that token from unregistered device fails validation."""
        table_manager, device_registry, test_data = setup_test_environment

        table_id = test_data['table_assignments'][0]
        key_index = 42

        # Encrypt with a DIFFERENT NUC hash (not registered)
        master_key = table_manager.key_tables[table_id]
        encryption_key = derive_encryption_key(master_key, key_index)
        unknown_nuc_hash = secrets.token_bytes(32)  # Different from registered device
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(encryption_key)
        ciphertext_with_tag = aesgcm.encrypt(nonce, unknown_nuc_hash, None)

        ciphertext = ciphertext_with_tag[:-16]
        auth_tag = ciphertext_with_tag[-16:]

        # Validate token
        valid, message, device = validate_camera_token(
            table_manager=table_manager,
            device_registry=device_registry,
            ciphertext=ciphertext.hex(),
            auth_tag=auth_tag.hex(),
            nonce=nonce.hex(),
            table_id=table_id,
            key_index=key_index
        )

        # Assert validation failed
        assert valid is False
        assert "unknown device" in message.lower()

    def test_blacklisted_device(self, setup_test_environment):
        """Test that token from blacklisted device fails validation."""
        table_manager, device_registry, test_data = setup_test_environment

        # Blacklist the test device
        device = test_data['device']
        device_registry.blacklist_device(
            device.device_serial,
            reason="Test blacklist"
        )

        table_id = test_data['table_assignments'][0]
        key_index = 42

        # Encrypt valid token
        master_key = table_manager.key_tables[table_id]
        encryption_key = derive_encryption_key(master_key, key_index)
        nuc_hash = test_data['nuc_hash']
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(encryption_key)
        ciphertext_with_tag = aesgcm.encrypt(nonce, nuc_hash, None)

        ciphertext = ciphertext_with_tag[:-16]
        auth_tag = ciphertext_with_tag[-16:]

        # Validate token
        valid, message, device_result = validate_camera_token(
            table_manager=table_manager,
            device_registry=device_registry,
            ciphertext=ciphertext.hex(),
            auth_tag=auth_tag.hex(),
            nonce=nonce.hex(),
            table_id=table_id,
            key_index=key_index
        )

        # Assert validation failed due to blacklist
        assert valid is False
        assert "blacklisted" in message.lower()

    def test_multiple_table_assignments(self, setup_test_environment):
        """Test that device can use any of its assigned tables."""
        table_manager, device_registry, test_data = setup_test_environment

        # Test each assigned table
        for table_id in test_data['table_assignments']:
            key_index = 42

            # Encrypt token
            master_key = table_manager.key_tables[table_id]
            encryption_key = derive_encryption_key(master_key, key_index)
            nuc_hash = test_data['nuc_hash']
            nonce = secrets.token_bytes(12)
            aesgcm = AESGCM(encryption_key)
            ciphertext_with_tag = aesgcm.encrypt(nonce, nuc_hash, None)

            ciphertext = ciphertext_with_tag[:-16]
            auth_tag = ciphertext_with_tag[-16:]

            # Validate token
            valid, message, device = validate_camera_token(
                table_manager=table_manager,
                device_registry=device_registry,
                ciphertext=ciphertext.hex(),
                auth_tag=auth_tag.hex(),
                nonce=nonce.hex(),
                table_id=table_id,
                key_index=key_index
            )

            # Assert validation succeeded for this table
            assert valid is True, f"Table {table_id} failed: {message}"
            assert device.device_serial == "TEST-CAMERA-123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
