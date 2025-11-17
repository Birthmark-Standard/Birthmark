"""
Certificate parsing utilities for extracting Birthmark extensions.
"""

from dataclasses import dataclass
from typing import Optional

from cryptography import x509
from cryptography.hazmat.backends import default_backend

from .oids import CameraCertOIDs, SoftwareCertOIDs


@dataclass
class CameraExtensions:
    """Parsed camera certificate extensions."""

    manufacturer_id: str
    ma_endpoint: str
    encrypted_nuc: bytes  # 60 bytes: 32 ciphertext + 12 nonce + 16 tag
    key_table_id: int     # 0-2499
    key_index: int        # 0-999
    device_family: str


@dataclass
class SoftwareExtensions:
    """Parsed software certificate extensions (Phase 2)."""

    developer_id: str
    sa_endpoint: str
    app_identifier: str
    version_string: str
    allowed_versions: list[str]


class CertificateParser:
    """Parse X.509 certificates and extract Birthmark extensions."""

    @staticmethod
    def load_certificate(cert_bytes: bytes) -> x509.Certificate:
        """
        Load DER-encoded certificate.

        Args:
            cert_bytes: DER-encoded certificate bytes

        Returns:
            Parsed X.509 certificate

        Raises:
            ValueError: If certificate cannot be parsed
        """
        try:
            return x509.load_der_x509_certificate(cert_bytes, default_backend())
        except Exception as e:
            raise ValueError(f"Failed to parse certificate: {e}")

    @staticmethod
    def parse_camera_extensions(cert: x509.Certificate) -> CameraExtensions:
        """
        Extract camera certificate extensions.

        Args:
            cert: Parsed X.509 certificate

        Returns:
            Parsed camera extensions

        Raises:
            ValueError: If required extensions are missing or invalid
        """
        extensions = {}

        for ext in cert.extensions:
            try:
                if ext.oid == CameraCertOIDs.MANUFACTURER_ID:
                    # UTF8String
                    extensions['manufacturer_id'] = ext.value.value.decode('utf-8')

                elif ext.oid == CameraCertOIDs.MA_ENDPOINT:
                    # UTF8String
                    extensions['ma_endpoint'] = ext.value.value.decode('utf-8')

                elif ext.oid == CameraCertOIDs.ENCRYPTED_NUC:
                    # OCTET STRING - 60 bytes
                    encrypted_nuc = ext.value.value
                    if len(encrypted_nuc) != 60:
                        raise ValueError(
                            f"Invalid encrypted NUC length: {len(encrypted_nuc)} (expected 60)"
                        )
                    extensions['encrypted_nuc'] = encrypted_nuc

                elif ext.oid == CameraCertOIDs.KEY_TABLE_ID:
                    # INTEGER - 0-2499
                    key_table_id = int.from_bytes(ext.value.value, 'big')
                    if not (0 <= key_table_id < 2500):
                        raise ValueError(f"Invalid key_table_id: {key_table_id}")
                    extensions['key_table_id'] = key_table_id

                elif ext.oid == CameraCertOIDs.KEY_INDEX:
                    # INTEGER - 0-999
                    key_index = int.from_bytes(ext.value.value, 'big')
                    if not (0 <= key_index < 1000):
                        raise ValueError(f"Invalid key_index: {key_index}")
                    extensions['key_index'] = key_index

                elif ext.oid == CameraCertOIDs.DEVICE_FAMILY:
                    # UTF8String
                    extensions['device_family'] = ext.value.value.decode('utf-8')

            except Exception as e:
                raise ValueError(f"Failed to parse extension {ext.oid}: {e}")

        # Verify all required extensions are present
        required = [
            'manufacturer_id', 'ma_endpoint', 'encrypted_nuc',
            'key_table_id', 'key_index', 'device_family'
        ]
        missing = [field for field in required if field not in extensions]
        if missing:
            raise ValueError(f"Missing required extensions: {missing}")

        return CameraExtensions(**extensions)

    @staticmethod
    def parse_software_extensions(cert: x509.Certificate) -> SoftwareExtensions:
        """
        Extract software certificate extensions (Phase 2).

        Args:
            cert: Parsed X.509 certificate

        Returns:
            Parsed software extensions

        Raises:
            ValueError: If required extensions are missing or invalid
        """
        extensions = {}

        for ext in cert.extensions:
            try:
                if ext.oid == SoftwareCertOIDs.DEVELOPER_ID:
                    extensions['developer_id'] = ext.value.value.decode('utf-8')

                elif ext.oid == SoftwareCertOIDs.SA_ENDPOINT:
                    extensions['sa_endpoint'] = ext.value.value.decode('utf-8')

                elif ext.oid == SoftwareCertOIDs.APP_IDENTIFIER:
                    extensions['app_identifier'] = ext.value.value.decode('utf-8')

                elif ext.oid == SoftwareCertOIDs.VERSION_STRING:
                    extensions['version_string'] = ext.value.value.decode('utf-8')

                elif ext.oid == SoftwareCertOIDs.ALLOWED_VERSIONS:
                    # SEQUENCE OF UTF8String - parse ASN.1 sequence
                    # For now, store as comma-separated string and split
                    # TODO: Proper ASN.1 sequence parsing
                    allowed = ext.value.value.decode('utf-8').split(',')
                    extensions['allowed_versions'] = [v.strip() for v in allowed]

            except Exception as e:
                raise ValueError(f"Failed to parse extension {ext.oid}: {e}")

        # Verify all required extensions are present
        required = [
            'developer_id', 'sa_endpoint', 'app_identifier',
            'version_string', 'allowed_versions'
        ]
        missing = [field for field in required if field not in extensions]
        if missing:
            raise ValueError(f"Missing required extensions: {missing}")

        return SoftwareExtensions(**extensions)

    @classmethod
    def parse_camera_cert_bytes(cls, cert_bytes: bytes) -> tuple[x509.Certificate, CameraExtensions]:
        """
        Parse camera certificate from DER bytes.

        Args:
            cert_bytes: DER-encoded certificate

        Returns:
            Tuple of (certificate, parsed extensions)
        """
        cert = cls.load_certificate(cert_bytes)
        extensions = cls.parse_camera_extensions(cert)
        return cert, extensions

    @classmethod
    def parse_software_cert_bytes(cls, cert_bytes: bytes) -> tuple[x509.Certificate, SoftwareExtensions]:
        """
        Parse software certificate from DER bytes.

        Args:
            cert_bytes: DER-encoded certificate

        Returns:
            Tuple of (certificate, parsed extensions)
        """
        cert = cls.load_certificate(cert_bytes)
        extensions = cls.parse_software_extensions(cert)
        return cert, extensions

    @staticmethod
    def get_subject_field(cert: x509.Certificate, oid: x509.ObjectIdentifier) -> Optional[str]:
        """
        Extract subject field from certificate.

        Args:
            cert: Parsed certificate
            oid: OID to extract (e.g., NameOID.COMMON_NAME)

        Returns:
            Field value or None if not present
        """
        try:
            return cert.subject.get_attributes_for_oid(oid)[0].value
        except (IndexError, AttributeError):
            return None

    @staticmethod
    def get_issuer_field(cert: x509.Certificate, oid: x509.ObjectIdentifier) -> Optional[str]:
        """
        Extract issuer field from certificate.

        Args:
            cert: Parsed certificate
            oid: OID to extract (e.g., NameOID.ORGANIZATION_NAME)

        Returns:
            Field value or None if not present
        """
        try:
            return cert.issuer.get_attributes_for_oid(oid)[0].value
        except (IndexError, AttributeError):
            return None
