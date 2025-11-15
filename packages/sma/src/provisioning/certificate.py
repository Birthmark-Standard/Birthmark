"""
Certificate generation utilities for device provisioning.

Generates X.509 device certificates signed by manufacturer CA.
Uses ECDSA P-256 as specified in Birthmark architecture.
"""

from datetime import datetime, timedelta
from typing import Tuple, Optional
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend


class CertificateAuthority:
    """
    Manages CA certificates for device provisioning.

    In Phase 1: Uses simulated local CA
    In Phase 2: Uses manufacturer-issued CA
    """

    def __init__(self, ca_cert_path: Optional[Path] = None, ca_key_path: Optional[Path] = None):
        """
        Initialize CA with existing certificates or generate new ones.

        Args:
            ca_cert_path: Path to intermediate CA certificate (PEM)
            ca_key_path: Path to intermediate CA private key (PEM)
        """
        self.ca_cert_path = ca_cert_path
        self.ca_key_path = ca_key_path
        self._ca_cert: Optional[x509.Certificate] = None
        self._ca_key: Optional[ec.EllipticCurvePrivateKey] = None

        if ca_cert_path and ca_key_path:
            self._load_ca_credentials()

    def _load_ca_credentials(self) -> None:
        """Load existing CA certificate and private key from files."""
        if not self.ca_cert_path or not self.ca_key_path:
            raise ValueError("CA certificate and key paths must be provided")

        # Load CA certificate
        with open(self.ca_cert_path, "rb") as f:
            self._ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())

        # Load CA private key
        with open(self.ca_key_path, "rb") as f:
            self._ca_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )

    @classmethod
    def generate_root_ca(
        cls,
        common_name: str = "Birthmark Simulated Root CA",
        validity_days: int = 3650
    ) -> Tuple[x509.Certificate, ec.EllipticCurvePrivateKey]:
        """
        Generate a self-signed root CA certificate.

        Args:
            common_name: CN for root CA
            validity_days: Certificate validity period (default 10 years)

        Returns:
            Tuple of (certificate, private_key)
        """
        # Generate private key (ECDSA P-256)
        private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())

        # Build certificate subject
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Birthmark Standard Foundation"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])

        # Create certificate builder
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=validity_days))
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=1),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_cert_sign=True,
                    crl_sign=True,
                    key_encipherment=False,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
                critical=False,
            )
            .sign(private_key, hashes.SHA256(), default_backend())
        )

        return cert, private_key

    @classmethod
    def generate_intermediate_ca(
        cls,
        root_cert: x509.Certificate,
        root_key: ec.EllipticCurvePrivateKey,
        common_name: str = "Birthmark Simulated Intermediate CA",
        validity_days: int = 1825
    ) -> Tuple[x509.Certificate, ec.EllipticCurvePrivateKey]:
        """
        Generate an intermediate CA certificate signed by root CA.

        Args:
            root_cert: Root CA certificate
            root_key: Root CA private key
            common_name: CN for intermediate CA
            validity_days: Certificate validity period (default 5 years)

        Returns:
            Tuple of (certificate, private_key)
        """
        # Generate private key (ECDSA P-256)
        private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())

        # Build certificate subject
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Birthmark Standard Foundation"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])

        # Create certificate builder
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(root_cert.subject)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=validity_days))
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=0),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_cert_sign=True,
                    crl_sign=True,
                    key_encipherment=False,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
                critical=False,
            )
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(root_key.public_key()),
                critical=False,
            )
            .sign(root_key, hashes.SHA256(), default_backend())
        )

        return cert, private_key

    def generate_device_certificate(
        self,
        device_serial: str,
        device_public_key: ec.EllipticCurvePublicKey,
        device_family: str = "Raspberry Pi",
        validity_days: int = 730
    ) -> x509.Certificate:
        """
        Generate a device certificate signed by the intermediate CA.

        Args:
            device_serial: Unique device serial number
            device_public_key: Device's public key
            device_family: Device type (e.g., "Raspberry Pi", "iOS")
            validity_days: Certificate validity period (default 2 years)

        Returns:
            Signed X.509 device certificate
        """
        if not self._ca_cert or not self._ca_key:
            raise ValueError("CA credentials not loaded. Call _load_ca_credentials() first.")

        # Build certificate subject
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Birthmark Standard Foundation"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, device_family),
            x509.NameAttribute(NameOID.COMMON_NAME, f"Birthmark Device {device_serial}"),
            x509.NameAttribute(NameOID.SERIAL_NUMBER, device_serial),
        ])

        # Create certificate builder
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(self._ca_cert.subject)
            .public_key(device_public_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=validity_days))
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=False,
                    content_commitment=False,
                    data_encipherment=False,
                    crl_sign=False,
                    key_cert_sign=False,
                    key_agreement=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
                critical=True,
            )
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(device_public_key),
                critical=False,
            )
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(
                    self._ca_key.public_key()
                ),
                critical=False,
            )
            .sign(self._ca_key, hashes.SHA256(), default_backend())
        )

        return cert


def save_certificate(cert: x509.Certificate, path: Path) -> None:
    """Save certificate to PEM file."""
    with open(path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))


def save_private_key(
    key: ec.EllipticCurvePrivateKey,
    path: Path,
    password: Optional[bytes] = None
) -> None:
    """
    Save private key to PEM file.

    Args:
        key: Private key to save
        path: Output file path
        password: Optional password for encryption
    """
    encryption = (
        serialization.BestAvailableEncryption(password)
        if password
        else serialization.NoEncryption()
    )

    with open(path, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=encryption,
            )
        )


def load_private_key(path: Path, password: Optional[bytes] = None) -> ec.EllipticCurvePrivateKey:
    """Load private key from PEM file."""
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(
            f.read(),
            password=password,
            backend=default_backend()
        )


def certificate_to_pem_string(cert: x509.Certificate) -> str:
    """Convert certificate to PEM-encoded string."""
    return cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')


def public_key_to_pem_string(key: ec.EllipticCurvePublicKey) -> str:
    """Convert public key to PEM-encoded string."""
    return key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
