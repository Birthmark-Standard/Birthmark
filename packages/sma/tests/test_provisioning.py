# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Unit tests for device provisioning.

Tests:
- Certificate generation
- Device keypair generation
- Complete provisioning workflow
- Error handling
"""

import pytest
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.provisioning.certificate import (
    CertificateAuthority,
    certificate_to_pem_string,
    public_key_to_pem_string
)
from src.provisioning.provisioner import (
    DeviceProvisioner,
    ProvisioningRequest,
    ProvisioningResponse
)
from src.key_tables.table_manager import KeyTableManager


class TestCertificateGeneration:
    """Test certificate generation functionality."""

    def test_generate_root_ca(self):
        """Test root CA certificate generation."""
        root_cert, root_key = CertificateAuthority.generate_root_ca()

        # Verify certificate properties
        assert isinstance(root_cert, x509.Certificate)
        assert isinstance(root_key, ec.EllipticCurvePrivateKey)

        # Check it's a CA certificate
        basic_constraints = root_cert.extensions.get_extension_for_oid(
            x509.oid.ExtensionOID.BASIC_CONSTRAINTS
        )
        assert basic_constraints.value.ca is True

        # Check common name
        cn = root_cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0]
        assert "Birthmark" in cn.value

    def test_generate_intermediate_ca(self):
        """Test intermediate CA certificate generation."""
        # Generate root CA
        root_cert, root_key = CertificateAuthority.generate_root_ca()

        # Generate intermediate CA
        intermediate_cert, intermediate_key = CertificateAuthority.generate_intermediate_ca(
            root_cert, root_key
        )

        # Verify certificate properties
        assert isinstance(intermediate_cert, x509.Certificate)
        assert isinstance(intermediate_key, ec.EllipticCurvePrivateKey)

        # Check it's a CA certificate
        basic_constraints = intermediate_cert.extensions.get_extension_for_oid(
            x509.oid.ExtensionOID.BASIC_CONSTRAINTS
        )
        assert basic_constraints.value.ca is True

        # Check issuer matches root subject
        assert intermediate_cert.issuer == root_cert.subject

    def test_generate_device_certificate(self, tmp_path):
        """Test device certificate generation."""
        # Setup CA
        root_cert, root_key = CertificateAuthority.generate_root_ca()
        intermediate_cert, intermediate_key = CertificateAuthority.generate_intermediate_ca(
            root_cert, root_key
        )

        # Save intermediate CA to temp files
        ca_cert_path = tmp_path / "intermediate-ca.crt"
        ca_key_path = tmp_path / "intermediate-ca.key"

        from src.provisioning.certificate import save_certificate, save_private_key
        save_certificate(intermediate_cert, ca_cert_path)
        save_private_key(intermediate_key, ca_key_path)

        # Create CA instance
        ca = CertificateAuthority(ca_cert_path, ca_key_path)

        # Generate device keypair
        device_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        device_public_key = device_key.public_key()

        # Generate device certificate
        device_cert = ca.generate_device_certificate(
            device_serial="TEST001",
            device_public_key=device_public_key,
            device_family="Test Device"
        )

        # Verify certificate properties
        assert isinstance(device_cert, x509.Certificate)

        # Check it's NOT a CA certificate
        basic_constraints = device_cert.extensions.get_extension_for_oid(
            x509.oid.ExtensionOID.BASIC_CONSTRAINTS
        )
        assert basic_constraints.value.ca is False

        # Check serial number in subject
        serial_attr = device_cert.subject.get_attributes_for_oid(
            x509.oid.NameOID.SERIAL_NUMBER
        )[0]
        assert serial_attr.value == "TEST001"

        # Check issuer matches intermediate CA
        assert device_cert.issuer == intermediate_cert.subject


class TestDeviceProvisioning:
    """Test complete device provisioning workflow."""

    @pytest.fixture
    def setup_ca(self, tmp_path):
        """Setup CA for testing."""
        root_cert, root_key = CertificateAuthority.generate_root_ca()
        intermediate_cert, intermediate_key = CertificateAuthority.generate_intermediate_ca(
            root_cert, root_key
        )

        ca_cert_path = tmp_path / "intermediate-ca.crt"
        ca_key_path = tmp_path / "intermediate-ca.key"

        from src.provisioning.certificate import save_certificate, save_private_key
        save_certificate(intermediate_cert, ca_cert_path)
        save_private_key(intermediate_key, ca_key_path)

        return CertificateAuthority(ca_cert_path, ca_key_path)

    @pytest.fixture
    def setup_table_manager(self):
        """Setup key table manager for testing."""
        table_manager = KeyTableManager(total_tables=10, tables_per_device=3)
        table_manager.generate_all_tables()
        return table_manager

    def test_provision_device(self, setup_ca, setup_table_manager):
        """Test complete device provisioning."""
        provisioner = DeviceProvisioner(setup_ca, setup_table_manager)

        request = ProvisioningRequest(
            device_serial="TEST001",
            device_family="Test Device"
        )

        response = provisioner.provision_device(request)

        # Verify response
        assert isinstance(response, ProvisioningResponse)
        assert response.device_serial == "TEST001"
        assert response.device_family == "Test Device"

        # Verify table assignments
        assert len(response.table_assignments) == 3
        assert all(0 <= tid < 10 for tid in response.table_assignments)
        assert len(set(response.table_assignments)) == 3  # No duplicates

        # Verify NUC hash
        assert len(response.nuc_hash) == 64  # 32 bytes = 64 hex chars

        # Verify certificates and keys are present
        assert "BEGIN CERTIFICATE" in response.device_certificate
        assert "BEGIN CERTIFICATE" in response.certificate_chain
        assert "BEGIN PRIVATE KEY" in response.device_private_key
        assert "BEGIN PUBLIC KEY" in response.device_public_key

    def test_provision_duplicate_device(self, setup_ca, setup_table_manager):
        """Test that provisioning same device twice raises error."""
        provisioner = DeviceProvisioner(setup_ca, setup_table_manager)

        request = ProvisioningRequest(
            device_serial="TEST001",
            device_family="Test Device"
        )

        # First provisioning should succeed
        provisioner.provision_device(request)

        # Second provisioning should fail
        with pytest.raises(ValueError, match="already provisioned"):
            provisioner.provision_device(request)

    def test_provision_with_custom_nuc_hash(self, setup_ca, setup_table_manager):
        """Test provisioning with custom NUC hash."""
        provisioner = DeviceProvisioner(setup_ca, setup_table_manager)

        # Generate custom NUC hash
        import hashlib
        custom_nuc = hashlib.sha256(b"test data").digest()

        request = ProvisioningRequest(
            device_serial="TEST002",
            device_family="Test Device",
            nuc_hash=custom_nuc
        )

        response = provisioner.provision_device(request)

        # Verify NUC hash matches
        assert response.nuc_hash == custom_nuc.hex()

    def test_provision_invalid_nuc_hash(self, setup_ca, setup_table_manager):
        """Test that invalid NUC hash raises error."""
        provisioner = DeviceProvisioner(setup_ca, setup_table_manager)

        # Invalid NUC hash (wrong length)
        request = ProvisioningRequest(
            device_serial="TEST003",
            device_family="Test Device",
            nuc_hash=b"too short"
        )

        with pytest.raises(ValueError, match="32 bytes"):
            provisioner.provision_device(request)

    def test_bulk_provisioning(self, setup_ca, setup_table_manager):
        """Test bulk device provisioning."""
        provisioner = DeviceProvisioner(setup_ca, setup_table_manager)

        device_serials = ["BULK001", "BULK002", "BULK003"]
        responses = provisioner.bulk_provision_devices(device_serials)

        assert len(responses) == 3

        # Verify all devices provisioned
        for i, response in enumerate(responses):
            assert response.device_serial == device_serials[i]
            assert len(response.table_assignments) == 3

        # Verify different table assignments
        all_assignments = [r.table_assignments for r in responses]
        # At least some should be different (very unlikely to be all identical)
        assert len(set(tuple(a) for a in all_assignments)) > 1


class TestProvisioningStatistics:
    """Test provisioning statistics."""

    @pytest.fixture
    def provisioner_with_devices(self, tmp_path):
        """Setup provisioner with some devices."""
        # Setup CA
        root_cert, root_key = CertificateAuthority.generate_root_ca()
        intermediate_cert, intermediate_key = CertificateAuthority.generate_intermediate_ca(
            root_cert, root_key
        )

        ca_cert_path = tmp_path / "intermediate-ca.crt"
        ca_key_path = tmp_path / "intermediate-ca.key"

        from src.provisioning.certificate import save_certificate, save_private_key
        save_certificate(intermediate_cert, ca_cert_path)
        save_private_key(intermediate_key, ca_key_path)

        ca = CertificateAuthority(ca_cert_path, ca_key_path)

        # Setup table manager
        table_manager = KeyTableManager(total_tables=10, tables_per_device=3)
        table_manager.generate_all_tables()

        # Create provisioner
        provisioner = DeviceProvisioner(ca, table_manager)

        # Provision some devices
        for i in range(5):
            request = ProvisioningRequest(
                device_serial=f"STATS{i:03d}",
                device_family="Test Device"
            )
            provisioner.provision_device(request)

        return provisioner

    def test_provisioning_statistics(self, provisioner_with_devices):
        """Test getting provisioning statistics."""
        stats = provisioner_with_devices.get_provisioning_statistics()

        assert stats["total_tables"] == 10
        assert stats["tables_per_device"] == 3
        assert stats["total_devices"] == 5
        assert stats["total_assignments"] == 15  # 5 devices × 3 tables

        # Verify table usage
        table_usage = stats["table_usage"]
        assert len(table_usage) == 10  # All tables tracked
        assert sum(table_usage.values()) == 15  # Total assignments


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
