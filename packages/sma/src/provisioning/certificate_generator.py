"""
Certificate Generator for Device Provisioning

This module handles generation of ECDSA P-256 device certificates
signed by the SMA root CA certificate.
"""

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography import x509
from cryptography.x509.oid import NameOID
from datetime import datetime, timedelta
import base64
from typing import Tuple


class CertificateGenerator:
    """
    Generate ECDSA P-256 device certificates for provisioning.

    The device certificate contains:
    - Device serial number in the subject CN
    - Device secret encoded in a custom extension
    - Key table indices in another custom extension
    - Validity period of 1 year
    - Signed by the SMA root CA
    """

    # Custom OIDs for Birthmark extensions
    OID_DEVICE_SECRET = x509.ObjectIdentifier("1.3.6.1.4.1.99999.1")  # Birthmark device_secret
    OID_KEY_TABLES = x509.ObjectIdentifier("1.3.6.1.4.1.99999.2")     # Birthmark key_table_indices

    def __init__(self, ca_private_key_path: str, ca_cert_path: str):
        """
        Initialize certificate generator with CA credentials.

        Args:
            ca_private_key_path: Path to CA private key PEM file
            ca_cert_path: Path to CA certificate PEM file

        Raises:
            FileNotFoundError: If CA files don't exist
            ValueError: If CA files are invalid
        """
        # Load CA private key
        with open(ca_private_key_path, 'rb') as f:
            self.ca_private_key = serialization.load_pem_private_key(
                f.read(),
                password=None
            )

        # Load CA certificate
        with open(ca_cert_path, 'rb') as f:
            self.ca_cert = x509.load_pem_x509_certificate(f.read())

        # Verify CA key matches CA cert
        ca_public_key = self.ca_cert.public_key()
        derived_public_key = self.ca_private_key.public_key()

        # Compare public keys by encoding them
        if (ca_public_key.public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ) != derived_public_key.public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )):
            raise ValueError("CA private key does not match CA certificate")

    def generate_device_certificate(
        self,
        device_serial: str,
        device_secret: str,
        key_table_indices: list[int],
        device_family: str = "iOS"
    ) -> Tuple[str, str, str]:
        """
        Generate device certificate, private key, and chain.

        This creates a complete set of credentials for a device:
        1. Generate new ECDSA P-256 key pair for device
        2. Create X.509 certificate with device info in extensions
        3. Sign certificate with CA private key
        4. Return PEM-encoded cert, key, and chain

        Args:
            device_serial: Unique device identifier (e.g., iOS UDID)
            device_secret: Hex-encoded SHA-256 device secret
            key_table_indices: List of 3 global key table indices
            device_family: Device type (e.g., "iOS", "Raspberry Pi")

        Returns:
            Tuple of (device_cert_pem, device_private_key_pem, cert_chain_pem)

        Raises:
            ValueError: If inputs are invalid
        """
        # Validate inputs
        if not device_serial or len(device_serial) > 255:
            raise ValueError(f"Invalid device_serial: {device_serial}")

        if not device_secret or len(device_secret) != 64:
            raise ValueError(f"device_secret must be 64 hex characters, got: {len(device_secret)}")

        if len(key_table_indices) != 3:
            raise ValueError(f"key_table_indices must have 3 elements, got: {len(key_table_indices)}")

        for idx in key_table_indices:
            if not 0 <= idx < 2500:
                raise ValueError(f"Invalid key table index: {idx} (must be 0-2499)")

        # 1. Generate device private key (ECDSA P-256)
        device_private_key = ec.generate_private_key(ec.SECP256R1())

        # 2. Get device public key
        device_public_key = device_private_key.public_key()

        # 3. Create certificate subject
        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, device_serial),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Birthmark Standard"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, f"{device_family} Device"),
        ])

        # 4. Create certificate extensions
        # Store device_secret and key_table_indices as custom extensions
        extensions = []

        # Extension 1: Device secret (critical=False, so can be ignored by standard validators)
        device_secret_bytes = device_secret.encode('utf-8')
        extensions.append(x509.Extension(
            self.OID_DEVICE_SECRET,
            critical=False,
            value=device_secret_bytes
        ))

        # Extension 2: Key table indices (encoded as comma-separated string)
        key_tables_str = ','.join(str(idx) for idx in key_table_indices)
        key_tables_bytes = key_tables_str.encode('utf-8')
        extensions.append(x509.Extension(
            self.OID_KEY_TABLES,
            critical=False,
            value=key_tables_bytes
        ))

        # Extension 3: Basic Constraints (not a CA)
        extensions.append(x509.Extension(
            x509.oid.ExtensionOID.BASIC_CONSTRAINTS,
            critical=True,
            value=x509.BasicConstraints(ca=False, path_length=None)
        ))

        # Extension 4: Key Usage (digital signature only)
        extensions.append(x509.Extension(
            x509.oid.ExtensionOID.KEY_USAGE,
            critical=True,
            value=x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False
            )
        ))

        # 5. Build certificate
        cert_builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(self.ca_cert.subject)
            .public_key(device_public_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=365))  # 1 year validity
        )

        # Add all extensions
        for ext in extensions:
            cert_builder = cert_builder.add_extension(ext.oid, ext.value, ext.critical)

        # 6. Sign certificate with CA private key
        device_cert = cert_builder.sign(self.ca_private_key, hashes.SHA256())

        # 7. Serialize to PEM format

        # Device certificate
        device_cert_pem = device_cert.public_bytes(
            serialization.Encoding.PEM
        ).decode('utf-8')

        # Device private key (unencrypted PEM for simplicity)
        device_private_key_pem = device_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        # Certificate chain (just the CA cert for now, could include intermediates)
        cert_chain_pem = self.ca_cert.public_bytes(
            serialization.Encoding.PEM
        ).decode('utf-8')

        return (device_cert_pem, device_private_key_pem, cert_chain_pem)

    def extract_device_secret_from_cert(self, cert_pem: str) -> str:
        """
        Extract device_secret from a device certificate.

        This is used by the validation endpoint to retrieve the device secret
        without storing it separately.

        Args:
            cert_pem: PEM-encoded device certificate

        Returns:
            Hex-encoded device secret (64 characters)

        Raises:
            ValueError: If certificate doesn't contain device_secret extension
        """
        cert = x509.load_pem_x509_certificate(cert_pem.encode('utf-8'))

        try:
            ext = cert.extensions.get_extension_for_oid(self.OID_DEVICE_SECRET)
            device_secret = ext.value.value.decode('utf-8')
            return device_secret
        except x509.ExtensionNotFound:
            raise ValueError("Certificate does not contain device_secret extension")

    def extract_key_table_indices_from_cert(self, cert_pem: str) -> list[int]:
        """
        Extract key_table_indices from a device certificate.

        Args:
            cert_pem: PEM-encoded device certificate

        Returns:
            List of 3 key table indices

        Raises:
            ValueError: If certificate doesn't contain key_tables extension
        """
        cert = x509.load_pem_x509_certificate(cert_pem.encode('utf-8'))

        try:
            ext = cert.extensions.get_extension_for_oid(self.OID_KEY_TABLES)
            key_tables_str = ext.value.value.decode('utf-8')
            indices = [int(x) for x in key_tables_str.split(',')]

            if len(indices) != 3:
                raise ValueError(f"Expected 3 key table indices, got {len(indices)}")

            return indices
        except x509.ExtensionNotFound:
            raise ValueError("Certificate does not contain key_tables extension")
