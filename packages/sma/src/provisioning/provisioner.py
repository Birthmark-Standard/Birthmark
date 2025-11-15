"""
Device provisioning module.

Handles complete device provisioning workflow:
1. Generate device keypair
2. Assign random key tables
3. Generate device certificate
4. Generate simulated NUC hash
5. Store device registration
6. Return provisioning data to device
"""

import hashlib
import secrets
from dataclasses import dataclass
from typing import Optional, List
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography import x509

from .certificate import (
    CertificateAuthority,
    certificate_to_pem_string,
    public_key_to_pem_string
)
from ..key_tables.table_manager import KeyTableManager


@dataclass
class ProvisioningRequest:
    """
    Request for device provisioning.

    In Phase 1: Manual provisioning via script
    In Phase 2: API endpoint receives this from device
    """
    device_serial: str
    device_family: str = "Raspberry Pi"  # "Raspberry Pi", "iOS", etc.
    nuc_hash: Optional[bytes] = None  # If None, will be simulated


@dataclass
class ProvisioningResponse:
    """
    Complete provisioning data returned to device.

    Device stores:
    - device_certificate and certificate_chain for authentication
    - table_assignments for NUC token encryption
    - device_private_key (securely in TPM/Secure Element)
    """
    device_serial: str
    device_certificate: str  # PEM-encoded X.509 certificate
    certificate_chain: str  # PEM-encoded intermediate CA cert
    device_private_key: str  # PEM-encoded private key (ECDSA P-256)
    device_public_key: str  # PEM-encoded public key
    table_assignments: List[int]  # 3 random table IDs
    nuc_hash: str  # Hex-encoded SHA-256 (for verification only)
    device_family: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "device_serial": self.device_serial,
            "device_certificate": self.device_certificate,
            "certificate_chain": self.certificate_chain,
            "device_private_key": self.device_private_key,
            "device_public_key": self.device_public_key,
            "table_assignments": self.table_assignments,
            "nuc_hash": self.nuc_hash,
            "device_family": self.device_family
        }


class DeviceProvisioner:
    """
    Main device provisioning service.

    Orchestrates certificate generation, table assignment, and registration.
    """

    def __init__(
        self,
        ca: CertificateAuthority,
        table_manager: KeyTableManager
    ):
        """
        Initialize provisioner with CA and table manager.

        Args:
            ca: Certificate authority for signing device certificates
            table_manager: Key table manager for table assignments
        """
        self.ca = ca
        self.table_manager = table_manager

    def generate_device_keypair(self) -> tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
        """
        Generate ECDSA P-256 keypair for device.

        Returns:
            Tuple of (private_key, public_key)
        """
        private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        public_key = private_key.public_key()
        return private_key, public_key

    def generate_simulated_nuc_hash(self) -> bytes:
        """
        Generate simulated NUC (Non-Uniformity Correction) hash.

        In Phase 1: Random 32-byte hash simulating sensor fingerprint
        In production: Actual NUC derived from camera sensor characteristics

        Returns:
            32-byte SHA-256 hash
        """
        # Generate 24MB of random data (simulating 12MP Bayer raw)
        # In reality, this would be actual sensor non-uniformity data
        simulated_sensor_data = secrets.token_bytes(24 * 1024 * 1024)

        # Compute SHA-256 hash
        nuc_hash = hashlib.sha256(simulated_sensor_data).digest()
        return nuc_hash

    def provision_device(
        self,
        request: ProvisioningRequest
    ) -> ProvisioningResponse:
        """
        Complete device provisioning workflow.

        Steps:
        1. Generate device keypair (ECDSA P-256)
        2. Assign 3 random key tables
        3. Generate device certificate signed by CA
        4. Generate/validate NUC hash
        5. Return provisioning data

        Args:
            request: Provisioning request with device details

        Returns:
            ProvisioningResponse with all provisioning data

        Raises:
            ValueError: If device already provisioned or invalid request
        """
        # Check if device already provisioned
        existing_assignment = self.table_manager.get_table_assignments(request.device_serial)
        if existing_assignment is not None:
            raise ValueError(f"Device {request.device_serial} already provisioned")

        # Step 1: Generate device keypair
        private_key, public_key = self.generate_device_keypair()

        # Step 2: Assign 3 random key tables
        table_assignments = self.table_manager.assign_random_tables(request.device_serial)

        # Step 3: Generate device certificate
        device_cert = self.ca.generate_device_certificate(
            device_serial=request.device_serial,
            device_public_key=public_key,
            device_family=request.device_family
        )

        # Step 4: Generate or use provided NUC hash
        if request.nuc_hash is None:
            nuc_hash = self.generate_simulated_nuc_hash()
        else:
            # Validate provided NUC hash
            if len(request.nuc_hash) != 32:
                raise ValueError(f"NUC hash must be 32 bytes, got {len(request.nuc_hash)}")
            nuc_hash = request.nuc_hash

        # Step 5: Build provisioning response
        response = ProvisioningResponse(
            device_serial=request.device_serial,
            device_certificate=certificate_to_pem_string(device_cert),
            certificate_chain=certificate_to_pem_string(self.ca._ca_cert),
            device_private_key=self._private_key_to_pem(private_key),
            device_public_key=public_key_to_pem_string(public_key),
            table_assignments=table_assignments,
            nuc_hash=nuc_hash.hex(),
            device_family=request.device_family
        )

        return response

    def _private_key_to_pem(self, key: ec.EllipticCurvePrivateKey) -> str:
        """Convert private key to PEM-encoded string."""
        from cryptography.hazmat.primitives import serialization

        return key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

    def bulk_provision_devices(
        self,
        device_serials: List[str],
        device_family: str = "Raspberry Pi"
    ) -> List[ProvisioningResponse]:
        """
        Provision multiple devices in bulk.

        Useful for Phase 1 photography club deployment.

        Args:
            device_serials: List of device serial numbers
            device_family: Device type (default: Raspberry Pi)

        Returns:
            List of provisioning responses
        """
        responses = []
        for serial in device_serials:
            request = ProvisioningRequest(
                device_serial=serial,
                device_family=device_family
            )
            response = self.provision_device(request)
            responses.append(response)

        return responses

    def get_provisioning_statistics(self) -> dict:
        """
        Get statistics about provisioned devices.

        Returns:
            Dictionary with provisioning statistics
        """
        return self.table_manager.get_statistics()


def provision_single_device(
    device_serial: str,
    ca: CertificateAuthority,
    table_manager: KeyTableManager,
    device_family: str = "Raspberry Pi",
    nuc_hash: Optional[bytes] = None
) -> ProvisioningResponse:
    """
    Convenience function to provision a single device.

    Args:
        device_serial: Unique device serial number
        ca: Certificate authority
        table_manager: Key table manager
        device_family: Device type (default: Raspberry Pi)
        nuc_hash: Optional NUC hash (simulated if None)

    Returns:
        ProvisioningResponse with provisioning data
    """
    provisioner = DeviceProvisioner(ca, table_manager)
    request = ProvisioningRequest(
        device_serial=device_serial,
        device_family=device_family,
        nuc_hash=nuc_hash
    )
    return provisioner.provision_device(request)
