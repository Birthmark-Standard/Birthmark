# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Device provisioning module.

Handles complete device provisioning workflow:
1. Generate device keypair
2. Assign random key tables
3. Generate device certificate (with Birthmark extensions)
4. Generate simulated NUC hash
5. Encrypt NUC hash with table key
6. Store device registration
7. Return provisioning data to device
"""

import hashlib
import secrets
from dataclasses import dataclass
from typing import Optional, List
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
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

    Phase 2 updates:
    - device_secret: Replaces nuc_hash (iOS uses device secret, not NUC)
    - key_tables: Actual key data (3 arrays of 1000 keys each)
    - key_table_indices: Global table IDs (e.g., [42, 157, 891])

    Device stores:
    - device_certificate and certificate_chain for authentication
    - device_secret and key_tables for encryption
    - key_table_indices to map local (0-2) to global indices
    - device_private_key (securely in TPM/Secure Element)
    """
    device_serial: str
    device_certificate: str  # PEM-encoded X.509 certificate
    certificate_chain: str  # PEM-encoded intermediate CA cert
    device_private_key: str  # PEM-encoded private key (ECDSA P-256)
    device_public_key: str  # PEM-encoded public key
    table_assignments: List[int]  # 3 local references (backward compat)
    device_secret: str  # Hex-encoded SHA-256 device secret (Phase 2)
    device_family: str
    # Phase 2 additions
    key_tables: Optional[List[List[str]]] = None  # 3 arrays of 1000 hex keys
    key_table_indices: Optional[List[int]] = None  # Global indices [42, 157, 891]
    # Backward compatibility
    nuc_hash: Optional[str] = None  # Phase 1 compatibility

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "device_serial": self.device_serial,
            "device_certificate": self.device_certificate,
            "certificate_chain": self.certificate_chain,
            "device_private_key": self.device_private_key,
            "device_public_key": self.device_public_key,
            "table_assignments": self.table_assignments,
            "device_secret": self.device_secret,
            "device_family": self.device_family
        }

        # Include Phase 2 fields if present
        if self.key_tables is not None:
            result["key_tables"] = self.key_tables
        if self.key_table_indices is not None:
            result["key_table_indices"] = self.key_table_indices
        if self.nuc_hash is not None:
            result["nuc_hash"] = self.nuc_hash

        return result


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

    def encrypt_nuc_for_certificate(
        self,
        nuc_hash: bytes,
        table_id: int,
        key_index: int
    ) -> bytes:
        """
        Encrypt NUC hash for embedding in certificate.

        Uses AES-256-GCM with the master key from the assigned table.
        This creates a 60-byte encrypted token: 32 (ciphertext) + 12 (nonce) + 16 (tag).

        Args:
            nuc_hash: 32-byte NUC hash to encrypt
            table_id: Key table ID (0-2499)
            key_index: Key index within table (0-999) - used for key derivation

        Returns:
            60 bytes: ciphertext (32) || nonce (12) || auth_tag (16)
        """
        # Get master key for table
        master_key = self.table_manager.get_master_key(table_id)
        if master_key is None:
            raise ValueError(f"No master key found for table {table_id}")

        # For Phase 1, use master key directly
        # Phase 2 TODO: Derive key from master_key + key_index using HKDF
        encryption_key = master_key

        # Generate random nonce
        nonce = secrets.token_bytes(12)

        # Encrypt NUC hash with AES-256-GCM
        aesgcm = AESGCM(encryption_key)
        ciphertext = aesgcm.encrypt(nonce, nuc_hash, None)

        # ciphertext includes auth_tag (16 bytes) appended to encrypted data
        # Format: 32 bytes encrypted + 16 bytes tag = 48 bytes total
        # Pack as: ciphertext (48 bytes) + nonce (12 bytes) = 60 bytes
        encrypted_token = ciphertext + nonce

        if len(encrypted_token) != 60:
            raise ValueError(f"Encrypted token must be 60 bytes, got {len(encrypted_token)}")

        return encrypted_token

    def provision_device(
        self,
        request: ProvisioningRequest
    ) -> ProvisioningResponse:
        """
        Complete device provisioning workflow.

        Steps:
        1. Generate device keypair (ECDSA P-256)
        2. Assign 3 random key tables (keep for backward compatibility)
        3. Generate/validate NUC hash
        4. Encrypt NUC with first table's key
        5. Generate device certificate with Birthmark extensions
        6. Return provisioning data

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

        # Step 2: Assign 3 random key tables (for backward compatibility)
        table_assignments = self.table_manager.assign_random_tables(request.device_serial)

        # Step 3: Generate or use provided NUC hash
        if request.nuc_hash is None:
            nuc_hash = self.generate_simulated_nuc_hash()
        else:
            # Validate provided NUC hash
            if len(request.nuc_hash) != 32:
                raise ValueError(f"NUC hash must be 32 bytes, got {len(request.nuc_hash)}")
            nuc_hash = request.nuc_hash

        # Step 4: Encrypt NUC for certificate
        # Use first table assignment for certificate extension
        cert_table_id = table_assignments[0]
        cert_key_index = secrets.randbelow(1000)  # Random key index (0-999)

        encrypted_nuc = self.encrypt_nuc_for_certificate(
            nuc_hash=nuc_hash,
            table_id=cert_table_id,
            key_index=cert_key_index
        )

        # Step 5: Generate device certificate with Birthmark extensions
        device_cert = self.ca.generate_device_certificate(
            device_serial=request.device_serial,
            device_public_key=public_key,
            device_family=request.device_family,
            encrypted_nuc=encrypted_nuc,
            key_table_id=cert_table_id,
            key_index=cert_key_index,
            ma_endpoint="http://localhost:8001/validate-cert"
        )

        # Step 6: Build provisioning response
        # Check if Phase 2 key table manager (has get_multiple_table_keys method)
        key_tables_data = None
        key_table_indices = None

        if hasattr(self.table_manager, 'get_multiple_table_keys'):
            # Phase 2: Return actual key data
            try:
                key_arrays = self.table_manager.get_multiple_table_keys(table_assignments)
                # Convert to hex strings for JSON serialization
                key_tables_data = [
                    [key.hex() for key in table_keys]
                    for table_keys in key_arrays
                ]
                key_table_indices = table_assignments  # Global indices
            except Exception as e:
                print(f"Warning: Could not retrieve key tables: {e}")
                # Fall back to Phase 1 behavior

        response = ProvisioningResponse(
            device_serial=request.device_serial,
            device_certificate=certificate_to_pem_string(device_cert),
            certificate_chain=certificate_to_pem_string(self.ca._ca_cert),
            device_private_key=self._private_key_to_pem(private_key),
            device_public_key=public_key_to_pem_string(public_key),
            table_assignments=table_assignments,
            device_secret=nuc_hash.hex(),  # Use device_secret (Phase 2)
            device_family=request.device_family,
            key_tables=key_tables_data,  # Phase 2: Actual key data
            key_table_indices=key_table_indices,  # Phase 2: Global indices
            nuc_hash=nuc_hash.hex()  # Backward compatibility
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
