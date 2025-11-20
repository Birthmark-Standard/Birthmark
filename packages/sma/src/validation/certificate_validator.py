"""
Certificate Validator for Bundle Validation

This module validates certificate bundles submitted by devices to the aggregator.
It verifies:
1. Certificate chain validity (signed by CA)
2. Certificate has not expired
3. Bundle signature is valid (ECDSA P-256)
4. Device is not blacklisted
5. Device secret can be extracted

The aggregator calls this to validate submissions without seeing the image hash.
"""

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature
from typing import Tuple, Optional
from datetime import datetime
import base64


class CertificateValidator:
    """
    Validate device certificates and bundle signatures.

    Used by the aggregator to validate certificate bundles from iOS devices
    without the SMA ever seeing the image hash (privacy-preserving).
    """

    def __init__(self, ca_cert_path: str):
        """
        Initialize validator with CA certificate for chain validation.

        Args:
            ca_cert_path: Path to CA certificate PEM file

        Raises:
            FileNotFoundError: If CA certificate doesn't exist
            ValueError: If CA certificate is invalid
        """
        # Load CA certificate
        with open(ca_cert_path, 'rb') as f:
            self.ca_cert = x509.load_pem_x509_certificate(f.read())

    def validate_certificate_bundle(
        self,
        camera_cert_b64: str,
        image_hash: str,
        timestamp: int,
        gps_hash: Optional[str],
        bundle_signature_b64: str,
        device_registry=None  # Optional: check blacklist
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Validate complete certificate bundle.

        This is the main validation method called by the aggregator.
        It performs all necessary checks without revealing the image hash to SMA.

        Args:
            camera_cert_b64: Base64-encoded device certificate (from iOS)
            image_hash: SHA-256 image hash (64 hex chars)
            timestamp: Unix timestamp when photo was taken
            gps_hash: Optional GPS hash (64 hex chars or None)
            bundle_signature_b64: Base64-encoded ECDSA P-256 signature
            device_registry: Optional DeviceRegistry to check blacklist

        Returns:
            Tuple of (is_valid, reason, device_secret)
            - is_valid: True if bundle is valid
            - reason: "PASS" or error message
            - device_secret: Extracted device secret (for blacklist check)

        Validation Steps:
        1. Decode certificate from base64
        2. Verify certificate chain (signed by our CA)
        3. Check certificate expiration
        4. Extract device_secret and key_table_indices from extensions
        5. Check if device is blacklisted (if registry provided)
        6. Verify bundle signature with device public key
        7. Return PASS or FAIL
        """
        try:
            # Step 1: Decode certificate
            try:
                cert_pem = base64.b64decode(camera_cert_b64)
                device_cert = x509.load_pem_x509_certificate(cert_pem)
            except Exception as e:
                return (False, f"Invalid certificate encoding: {e}", None)

            # Step 2: Verify certificate chain
            if not self._verify_certificate_chain(device_cert):
                return (False, "Certificate not signed by trusted CA", None)

            # Step 3: Check certificate expiration
            if not self._is_certificate_valid(device_cert):
                return (False, "Certificate expired or not yet valid", None)

            # Step 4: Extract device_secret from certificate extension
            device_secret = self._extract_device_secret(device_cert)
            if not device_secret:
                return (False, "Certificate missing device_secret extension", None)

            # Step 5: Check if device is blacklisted (if registry provided)
            if device_registry:
                try:
                    registration = device_registry.get_device_by_secret(device_secret)
                    if registration and registration.is_blacklisted:
                        reason = registration.blacklist_reason or "Device blacklisted"
                        return (False, f"BLACKLISTED: {reason}", device_secret)
                except Exception as e:
                    # Registry check failed, but don't block submission
                    print(f"Warning: Blacklist check failed: {e}")

            # Step 6: Verify bundle signature
            device_public_key = device_cert.public_key()
            canonical_data = self._create_canonical_data(
                image_hash, camera_cert_b64, timestamp, gps_hash
            )

            try:
                signature_bytes = base64.b64decode(bundle_signature_b64)
            except Exception as e:
                return (False, f"Invalid signature encoding: {e}", device_secret)

            if not self._verify_ecdsa_signature(
                device_public_key,
                canonical_data,
                signature_bytes
            ):
                return (False, "Invalid bundle signature", device_secret)

            # Step 7: All checks passed
            return (True, "PASS", device_secret)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return (False, f"Validation error: {str(e)}", None)

    def _verify_certificate_chain(self, device_cert: x509.Certificate) -> bool:
        """
        Verify device certificate is signed by our CA.

        Args:
            device_cert: Device certificate to verify

        Returns:
            True if certificate is signed by CA
        """
        try:
            # Get CA public key
            ca_public_key = self.ca_cert.public_key()

            # Verify device cert signature with CA public key
            ca_public_key.verify(
                device_cert.signature,
                device_cert.tbs_certificate_bytes,
                ec.ECDSA(device_cert.signature_hash_algorithm)
            )
            return True
        except InvalidSignature:
            return False
        except Exception as e:
            print(f"Certificate chain verification error: {e}")
            return False

    def _is_certificate_valid(self, cert: x509.Certificate) -> bool:
        """
        Check if certificate is within its validity period.

        Args:
            cert: Certificate to check

        Returns:
            True if certificate is currently valid
        """
        try:
            now = datetime.utcnow()
            return cert.not_valid_before_utc <= now <= cert.not_valid_after_utc
        except Exception:
            # Fall back to deprecated properties if utc versions don't exist
            try:
                now = datetime.utcnow()
                return cert.not_valid_before <= now <= cert.not_valid_after
            except Exception as e:
                print(f"Certificate validity check error: {e}")
                return False

    def _extract_device_secret(self, cert: x509.Certificate) -> Optional[str]:
        """
        Extract device_secret from certificate extension.

        Args:
            cert: Device certificate

        Returns:
            Hex-encoded device secret (64 chars) or None if not found
        """
        try:
            # Custom OID for device_secret (must match CertificateGenerator)
            OID_DEVICE_SECRET = x509.ObjectIdentifier("1.3.6.1.4.1.99999.1")

            ext = cert.extensions.get_extension_for_oid(OID_DEVICE_SECRET)
            device_secret = ext.value.value.decode('utf-8')
            return device_secret
        except x509.ExtensionNotFound:
            return None
        except Exception as e:
            print(f"Error extracting device_secret: {e}")
            return None

    def _create_canonical_data(
        self,
        image_hash: str,
        camera_cert: str,
        timestamp: int,
        gps_hash: Optional[str]
    ) -> bytes:
        """
        Create canonical bundle data for signature verification.

        Must match EXACTLY the format used by iOS CryptoService.swift:
        - image_hash (lowercase) + newline
        - camera_cert (base64 string) + newline
        - timestamp (string) + newline
        - gps_hash (lowercase or empty) + newline

        Args:
            image_hash: SHA-256 hash (64 hex chars)
            camera_cert: Base64-encoded certificate
            timestamp: Unix timestamp
            gps_hash: Optional GPS hash

        Returns:
            Canonical data as bytes
        """
        canonical = ""
        canonical += image_hash.lower() + "\n"
        canonical += camera_cert + "\n"
        canonical += str(timestamp) + "\n"
        canonical += (gps_hash.lower() if gps_hash else "") + "\n"

        return canonical.encode('utf-8')

    def _verify_ecdsa_signature(
        self,
        public_key: ec.EllipticCurvePublicKey,
        data: bytes,
        signature: bytes
    ) -> bool:
        """
        Verify ECDSA P-256 signature.

        Args:
            public_key: Device public key from certificate
            data: Canonical data that was signed
            signature: Raw signature bytes

        Returns:
            True if signature is valid
        """
        try:
            # Create ECDSA signature object from raw bytes
            ecdsa_signature = ec.ECDSA(signature)

            # Verify signature
            public_key.verify(
                signature,
                data,
                ec.ECDSA(hashes.SHA256())
            )
            return True
        except InvalidSignature:
            return False
        except Exception as e:
            print(f"Signature verification error: {e}")
            return False

    def extract_key_table_indices(self, camera_cert_b64: str) -> Optional[list[int]]:
        """
        Extract key_table_indices from certificate for debugging.

        Args:
            camera_cert_b64: Base64-encoded certificate

        Returns:
            List of 3 key table indices or None
        """
        try:
            cert_pem = base64.b64decode(camera_cert_b64)
            cert = x509.load_pem_x509_certificate(cert_pem)

            # Custom OID for key_tables (must match CertificateGenerator)
            OID_KEY_TABLES = x509.ObjectIdentifier("1.3.6.1.4.1.99999.2")

            ext = cert.extensions.get_extension_for_oid(OID_KEY_TABLES)
            key_tables_str = ext.value.value.decode('utf-8')
            indices = [int(x) for x in key_tables_str.split(',')]

            if len(indices) != 3:
                return None

            return indices
        except Exception as e:
            print(f"Error extracting key_table_indices: {e}")
            return None
