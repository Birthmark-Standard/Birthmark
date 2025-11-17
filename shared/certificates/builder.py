"""
Certificate generation utilities for Birthmark protocol.
"""

import datetime
from typing import Optional

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend

from .oids import CameraCertOIDs, SoftwareCertOIDs


class CameraCertificateBuilder:
    """Build camera certificates with Birthmark extensions."""

    def __init__(
        self,
        device_serial: str,
        manufacturer_name: str,
        device_public_key: ec.EllipticCurvePublicKey,
    ):
        """
        Initialize camera certificate builder.

        Args:
            device_serial: Unique device serial number
            manufacturer_name: Manufacturer organization name
            device_public_key: Device's ECDSA P-256 public key
        """
        self.device_serial = device_serial
        self.manufacturer_name = manufacturer_name
        self.device_public_key = device_public_key
        self.extensions: dict = {}

    def set_manufacturer_id(self, manufacturer_id: str) -> "CameraCertificateBuilder":
        """Set manufacturer identifier."""
        self.extensions['manufacturer_id'] = manufacturer_id
        return self

    def set_ma_endpoint(self, ma_endpoint: str) -> "CameraCertificateBuilder":
        """Set MA validation endpoint URL."""
        self.extensions['ma_endpoint'] = ma_endpoint
        return self

    def set_encrypted_nuc(self, encrypted_nuc: bytes) -> "CameraCertificateBuilder":
        """
        Set encrypted NUC hash.

        Args:
            encrypted_nuc: 60 bytes (32 ciphertext + 12 nonce + 16 tag)
        """
        if len(encrypted_nuc) != 60:
            raise ValueError(f"Invalid encrypted_nuc length: {len(encrypted_nuc)} (expected 60)")
        self.extensions['encrypted_nuc'] = encrypted_nuc
        return self

    def set_key_table_id(self, key_table_id: int) -> "CameraCertificateBuilder":
        """Set key table ID (0-2499)."""
        if not (0 <= key_table_id < 2500):
            raise ValueError(f"Invalid key_table_id: {key_table_id} (must be 0-2499)")
        self.extensions['key_table_id'] = key_table_id
        return self

    def set_key_index(self, key_index: int) -> "CameraCertificateBuilder":
        """Set key index within table (0-999)."""
        if not (0 <= key_index < 1000):
            raise ValueError(f"Invalid key_index: {key_index} (must be 0-999)")
        self.extensions['key_index'] = key_index
        return self

    def set_device_family(self, device_family: str) -> "CameraCertificateBuilder":
        """Set device family string."""
        self.extensions['device_family'] = device_family
        return self

    def build(
        self,
        ca_private_key: ec.EllipticCurvePrivateKey,
        ca_name: str = "Birthmark Manufacturer CA",
        validity_years: int = 10,
    ) -> x509.Certificate:
        """
        Build and sign the camera certificate.

        Args:
            ca_private_key: Manufacturer CA's private key for signing
            ca_name: CA common name (default: "Birthmark Manufacturer CA")
            validity_years: Certificate validity in years (default: 10)

        Returns:
            Signed X.509 certificate

        Raises:
            ValueError: If required extensions are missing
        """
        # Verify all required extensions are set
        required = [
            'manufacturer_id', 'ma_endpoint', 'encrypted_nuc',
            'key_table_id', 'key_index', 'device_family'
        ]
        missing = [field for field in required if field not in self.extensions]
        if missing:
            raise ValueError(f"Missing required extensions: {missing}")

        # Build subject (device)
        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, self.device_serial),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.manufacturer_name),
        ])

        # Build issuer (CA)
        issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, ca_name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.manufacturer_name),
        ])

        # Certificate validity
        now = datetime.datetime.utcnow()
        not_valid_before = now
        not_valid_after = now + datetime.timedelta(days=validity_years * 365)

        # Build certificate
        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(self.device_public_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(not_valid_before)
            .not_valid_after(not_valid_after)
        )

        # Add standard extensions
        builder = builder.add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )

        builder = builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )

        # Add Birthmark custom extensions
        builder = self._add_camera_extensions(builder)

        # Sign certificate
        certificate = builder.sign(ca_private_key, hashes.SHA256(), default_backend())

        return certificate

    def _add_camera_extensions(self, builder: x509.CertificateBuilder) -> x509.CertificateBuilder:
        """Add camera-specific custom extensions to builder."""

        # Manufacturer ID (UTF8String)
        builder = builder.add_extension(
            x509.UnrecognizedExtension(
                CameraCertOIDs.MANUFACTURER_ID,
                self.extensions['manufacturer_id'].encode('utf-8')
            ),
            critical=False,
        )

        # MA Endpoint (UTF8String)
        builder = builder.add_extension(
            x509.UnrecognizedExtension(
                CameraCertOIDs.MA_ENDPOINT,
                self.extensions['ma_endpoint'].encode('utf-8')
            ),
            critical=False,
        )

        # Encrypted NUC (OCTET STRING - raw bytes)
        builder = builder.add_extension(
            x509.UnrecognizedExtension(
                CameraCertOIDs.ENCRYPTED_NUC,
                self.extensions['encrypted_nuc']
            ),
            critical=False,
        )

        # Key Table ID (INTEGER as bytes)
        key_table_bytes = self.extensions['key_table_id'].to_bytes(2, 'big')
        builder = builder.add_extension(
            x509.UnrecognizedExtension(
                CameraCertOIDs.KEY_TABLE_ID,
                key_table_bytes
            ),
            critical=False,
        )

        # Key Index (INTEGER as bytes)
        key_index_bytes = self.extensions['key_index'].to_bytes(2, 'big')
        builder = builder.add_extension(
            x509.UnrecognizedExtension(
                CameraCertOIDs.KEY_INDEX,
                key_index_bytes
            ),
            critical=False,
        )

        # Device Family (UTF8String)
        builder = builder.add_extension(
            x509.UnrecognizedExtension(
                CameraCertOIDs.DEVICE_FAMILY,
                self.extensions['device_family'].encode('utf-8')
            ),
            critical=False,
        )

        return builder

    def to_der(self, ca_private_key: ec.EllipticCurvePrivateKey, **kwargs) -> bytes:
        """
        Build certificate and return DER-encoded bytes.

        Args:
            ca_private_key: CA private key for signing
            **kwargs: Additional arguments for build()

        Returns:
            DER-encoded certificate bytes
        """
        cert = self.build(ca_private_key, **kwargs)
        return cert.public_bytes(serialization.Encoding.DER)


class SoftwareCertificateBuilder:
    """Build software certificates with Birthmark extensions (Phase 2)."""

    def __init__(
        self,
        app_bundle_id: str,
        developer_name: str,
        app_public_key: ec.EllipticCurvePublicKey,
    ):
        """
        Initialize software certificate builder.

        Args:
            app_bundle_id: App bundle identifier (e.g., "com.instagram.ios")
            developer_name: Developer organization name
            app_public_key: App's ECDSA P-256 public key
        """
        self.app_bundle_id = app_bundle_id
        self.developer_name = developer_name
        self.app_public_key = app_public_key
        self.extensions: dict = {}

    def set_developer_id(self, developer_id: str) -> "SoftwareCertificateBuilder":
        """Set developer identifier."""
        self.extensions['developer_id'] = developer_id
        return self

    def set_sa_endpoint(self, sa_endpoint: str) -> "SoftwareCertificateBuilder":
        """Set SA validation endpoint URL."""
        self.extensions['sa_endpoint'] = sa_endpoint
        return self

    def set_app_identifier(self, app_identifier: str) -> "SoftwareCertificateBuilder":
        """Set app bundle identifier."""
        self.extensions['app_identifier'] = app_identifier
        return self

    def set_version_string(self, version_string: str) -> "SoftwareCertificateBuilder":
        """Set version string."""
        self.extensions['version_string'] = version_string
        return self

    def set_allowed_versions(self, allowed_versions: list[str]) -> "SoftwareCertificateBuilder":
        """Set list of allowed version strings."""
        self.extensions['allowed_versions'] = allowed_versions
        return self

    def build(
        self,
        ca_private_key: ec.EllipticCurvePrivateKey,
        ca_name: str = "Birthmark Software CA",
        validity_years: int = 1,
    ) -> x509.Certificate:
        """
        Build and sign the software certificate.

        Args:
            ca_private_key: Software CA's private key for signing
            ca_name: CA common name
            validity_years: Certificate validity in years (default: 1)

        Returns:
            Signed X.509 certificate
        """
        # Verify all required extensions are set
        required = [
            'developer_id', 'sa_endpoint', 'app_identifier',
            'version_string', 'allowed_versions'
        ]
        missing = [field for field in required if field not in self.extensions]
        if missing:
            raise ValueError(f"Missing required extensions: {missing}")

        # Build subject (app)
        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, self.app_bundle_id),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.developer_name),
        ])

        # Build issuer (CA)
        issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, ca_name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.developer_name),
        ])

        # Certificate validity
        now = datetime.datetime.utcnow()
        not_valid_before = now
        not_valid_after = now + datetime.timedelta(days=validity_years * 365)

        # Build certificate
        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(self.app_public_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(not_valid_before)
            .not_valid_after(not_valid_after)
        )

        # Add standard extensions
        builder = builder.add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )

        builder = builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )

        # Add Birthmark custom extensions
        builder = self._add_software_extensions(builder)

        # Sign certificate
        certificate = builder.sign(ca_private_key, hashes.SHA256(), default_backend())

        return certificate

    def _add_software_extensions(self, builder: x509.CertificateBuilder) -> x509.CertificateBuilder:
        """Add software-specific custom extensions to builder."""

        # Developer ID
        builder = builder.add_extension(
            x509.UnrecognizedExtension(
                SoftwareCertOIDs.DEVELOPER_ID,
                self.extensions['developer_id'].encode('utf-8')
            ),
            critical=False,
        )

        # SA Endpoint
        builder = builder.add_extension(
            x509.UnrecognizedExtension(
                SoftwareCertOIDs.SA_ENDPOINT,
                self.extensions['sa_endpoint'].encode('utf-8')
            ),
            critical=False,
        )

        # App Identifier
        builder = builder.add_extension(
            x509.UnrecognizedExtension(
                SoftwareCertOIDs.APP_IDENTIFIER,
                self.extensions['app_identifier'].encode('utf-8')
            ),
            critical=False,
        )

        # Version String
        builder = builder.add_extension(
            x509.UnrecognizedExtension(
                SoftwareCertOIDs.VERSION_STRING,
                self.extensions['version_string'].encode('utf-8')
            ),
            critical=False,
        )

        # Allowed Versions (comma-separated for now)
        # TODO: Proper ASN.1 SEQUENCE encoding
        allowed_versions_str = ','.join(self.extensions['allowed_versions'])
        builder = builder.add_extension(
            x509.UnrecognizedExtension(
                SoftwareCertOIDs.ALLOWED_VERSIONS,
                allowed_versions_str.encode('utf-8')
            ),
            critical=False,
        )

        return builder

    def to_der(self, ca_private_key: ec.EllipticCurvePrivateKey, **kwargs) -> bytes:
        """
        Build certificate and return DER-encoded bytes.

        Args:
            ca_private_key: CA private key for signing
            **kwargs: Additional arguments for build()

        Returns:
            DER-encoded certificate bytes
        """
        cert = self.build(ca_private_key, **kwargs)
        return cert.public_bytes(serialization.Encoding.DER)
