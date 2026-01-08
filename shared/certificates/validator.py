# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Certificate validation utilities for Birthmark protocol.
"""

import datetime
from dataclasses import dataclass
from typing import Optional

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

from .parser import CertificateParser, CameraExtensions, SoftwareExtensions


@dataclass
class ValidationResult:
    """Result of certificate validation."""

    valid: bool
    error_message: Optional[str] = None
    certificate: Optional[x509.Certificate] = None
    extensions: Optional[CameraExtensions | SoftwareExtensions] = None


class CertificateValidator:
    """Validate X.509 certificates and Birthmark extensions."""

    def __init__(self, trusted_ca_certs: Optional[list[x509.Certificate]] = None):
        """
        Initialize certificate validator.

        Args:
            trusted_ca_certs: List of trusted CA certificates for chain validation
        """
        self.trusted_ca_certs = trusted_ca_certs or []

    def add_trusted_ca(self, ca_cert: x509.Certificate) -> None:
        """Add a trusted CA certificate."""
        self.trusted_ca_certs.append(ca_cert)

    def add_trusted_ca_from_bytes(self, ca_cert_bytes: bytes) -> None:
        """Add a trusted CA certificate from DER bytes."""
        ca_cert = x509.load_der_x509_certificate(ca_cert_bytes, default_backend())
        self.add_trusted_ca(ca_cert)

    def validate_camera_certificate(
        self,
        cert_bytes: bytes,
        check_expiration: bool = True,
        check_signature: bool = True,
    ) -> ValidationResult:
        """
        Validate camera certificate.

        Args:
            cert_bytes: DER-encoded certificate
            check_expiration: Check if certificate is expired
            check_signature: Verify certificate signature against trusted CAs

        Returns:
            ValidationResult with parsed certificate and extensions if valid
        """
        try:
            # Parse certificate
            cert, extensions = CertificateParser.parse_camera_cert_bytes(cert_bytes)

            # Check expiration
            if check_expiration:
                now = datetime.datetime.utcnow()
                if cert.not_valid_before > now:
                    return ValidationResult(
                        valid=False,
                        error_message=f"Certificate not yet valid (valid from {cert.not_valid_before})"
                    )
                if cert.not_valid_after < now:
                    return ValidationResult(
                        valid=False,
                        error_message=f"Certificate expired (expired {cert.not_valid_after})"
                    )

            # Verify signature against trusted CAs
            if check_signature:
                if not self.trusted_ca_certs:
                    return ValidationResult(
                        valid=False,
                        error_message="No trusted CA certificates configured"
                    )

                signature_valid = False
                for ca_cert in self.trusted_ca_certs:
                    if self._verify_signature(cert, ca_cert):
                        signature_valid = True
                        break

                if not signature_valid:
                    return ValidationResult(
                        valid=False,
                        error_message="Certificate signature verification failed"
                    )

            # Validate extension values
            validation_error = self._validate_camera_extension_values(extensions)
            if validation_error:
                return ValidationResult(
                    valid=False,
                    error_message=validation_error
                )

            return ValidationResult(
                valid=True,
                certificate=cert,
                extensions=extensions
            )

        except ValueError as e:
            return ValidationResult(
                valid=False,
                error_message=f"Certificate parsing failed: {e}"
            )
        except Exception as e:
            return ValidationResult(
                valid=False,
                error_message=f"Certificate validation failed: {e}"
            )

    def validate_software_certificate(
        self,
        cert_bytes: bytes,
        check_expiration: bool = True,
        check_signature: bool = True,
    ) -> ValidationResult:
        """
        Validate software certificate (Phase 2).

        Args:
            cert_bytes: DER-encoded certificate
            check_expiration: Check if certificate is expired
            check_signature: Verify certificate signature against trusted CAs

        Returns:
            ValidationResult with parsed certificate and extensions if valid
        """
        try:
            # Parse certificate
            cert, extensions = CertificateParser.parse_software_cert_bytes(cert_bytes)

            # Check expiration
            if check_expiration:
                now = datetime.datetime.utcnow()
                if cert.not_valid_before > now:
                    return ValidationResult(
                        valid=False,
                        error_message=f"Certificate not yet valid (valid from {cert.not_valid_before})"
                    )
                if cert.not_valid_after < now:
                    return ValidationResult(
                        valid=False,
                        error_message=f"Certificate expired (expired {cert.not_valid_after})"
                    )

            # Verify signature against trusted CAs
            if check_signature:
                if not self.trusted_ca_certs:
                    return ValidationResult(
                        valid=False,
                        error_message="No trusted CA certificates configured"
                    )

                signature_valid = False
                for ca_cert in self.trusted_ca_certs:
                    if self._verify_signature(cert, ca_cert):
                        signature_valid = True
                        break

                if not signature_valid:
                    return ValidationResult(
                        valid=False,
                        error_message="Certificate signature verification failed"
                    )

            # Validate extension values
            validation_error = self._validate_software_extension_values(extensions)
            if validation_error:
                return ValidationResult(
                    valid=False,
                    error_message=validation_error
                )

            return ValidationResult(
                valid=True,
                certificate=cert,
                extensions=extensions
            )

        except ValueError as e:
            return ValidationResult(
                valid=False,
                error_message=f"Certificate parsing failed: {e}"
            )
        except Exception as e:
            return ValidationResult(
                valid=False,
                error_message=f"Certificate validation failed: {e}"
            )

    def _verify_signature(self, cert: x509.Certificate, ca_cert: x509.Certificate) -> bool:
        """
        Verify certificate signature using CA public key.

        Args:
            cert: Certificate to verify
            ca_cert: CA certificate containing public key

        Returns:
            True if signature is valid
        """
        try:
            ca_public_key = ca_cert.public_key()
            if isinstance(ca_public_key, ec.EllipticCurvePublicKey):
                # Verify ECDSA signature
                ca_public_key.verify(
                    cert.signature,
                    cert.tbs_certificate_bytes,
                    ec.ECDSA(cert.signature_hash_algorithm)
                )
                return True
            else:
                # Unsupported key type
                return False
        except InvalidSignature:
            return False
        except Exception:
            return False

    def _validate_camera_extension_values(self, ext: CameraExtensions) -> Optional[str]:
        """
        Validate camera extension values.

        Returns:
            Error message if invalid, None if valid
        """
        # Validate manufacturer_id format
        if not ext.manufacturer_id or len(ext.manufacturer_id) > 255:
            return f"Invalid manufacturer_id: {ext.manufacturer_id}"

        # Validate MA endpoint URL
        if not ext.ma_endpoint.startswith(('http://', 'https://')):
            return f"Invalid MA endpoint URL: {ext.ma_endpoint}"

        # Validate encrypted NUC length (already checked in parser, but double-check)
        if len(ext.encrypted_nuc) != 60:
            return f"Invalid encrypted NUC length: {len(ext.encrypted_nuc)}"

        # Validate key table ID range (already checked in parser)
        if not (0 <= ext.key_table_id < 2500):
            return f"Invalid key_table_id: {ext.key_table_id}"

        # Validate key index range (already checked in parser)
        if not (0 <= ext.key_index < 1000):
            return f"Invalid key_index: {ext.key_index}"

        # Validate device family
        if not ext.device_family or len(ext.device_family) > 255:
            return f"Invalid device_family: {ext.device_family}"

        return None

    def _validate_software_extension_values(self, ext: SoftwareExtensions) -> Optional[str]:
        """
        Validate software extension values.

        Returns:
            Error message if invalid, None if valid
        """
        # Validate developer_id format
        if not ext.developer_id or len(ext.developer_id) > 255:
            return f"Invalid developer_id: {ext.developer_id}"

        # Validate SA endpoint URL
        if not ext.sa_endpoint.startswith(('http://', 'https://')):
            return f"Invalid SA endpoint URL: {ext.sa_endpoint}"

        # Validate app identifier (reverse domain notation)
        if not ext.app_identifier or '.' not in ext.app_identifier:
            return f"Invalid app_identifier: {ext.app_identifier}"

        # Validate version string (semantic versioning)
        if not ext.version_string:
            return "Missing version_string"

        # Validate allowed versions list
        if not ext.allowed_versions or not isinstance(ext.allowed_versions, list):
            return "Invalid allowed_versions"

        return None
