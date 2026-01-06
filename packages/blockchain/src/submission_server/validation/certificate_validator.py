"""
Certificate validation for Birthmark blockchain aggregator.

Phase 1: Simplified validation - just passes certificates to SMA.
Phase 2+: Will add certificate parsing and signature verification.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from src.shared.models.schemas import CertificateBundle, SMAValidationResponse


logger = logging.getLogger(__name__)


@dataclass
class CertValidationResult:
    """Result of certificate validation."""

    valid: bool
    error: Optional[str] = None
    ma_endpoint: Optional[str] = None


@dataclass
class MAValidationResult:
    """Result of MA validation."""

    valid: bool
    message: Optional[str] = None


class CertificateValidatorService:
    """
    Service for validating camera certificates and coordinating MA validation.

    Phase 1: Simple pass-through to SMA
    Phase 2+: Full certificate parsing and signature verification
    """

    def __init__(self):
        """Initialize certificate validator."""
        logger.info("Certificate validator initialized (Phase 1: simplified mode)")

    async def validate_camera_certificate(
        self,
        bundle: CertificateBundle,
    ) -> CertValidationResult:
        """
        Validate camera certificate structure.

        Phase 1: Basic validation - checks certificate exists
        Phase 2+: Full parsing and signature verification

        Args:
            bundle: Certificate bundle from camera

        Returns:
            Validation result
        """
        try:
            # Basic check: certificate exists
            cert_b64 = bundle.camera_cert
            if not cert_b64 or len(cert_b64) == 0:
                return CertValidationResult(
                    valid=False,
                    error="Certificate is empty"
                )

            # Phase 1: No parsing, assume certificate is valid
            # Phase 2: Would parse DER/PEM and extract MA endpoint from extensions

            # For now, use default SMA endpoint from config
            # In Phase 2, this would come from certificate extensions
            ma_endpoint = "http://host.docker.internal:8001/validate"

            return CertValidationResult(
                valid=True,
                ma_endpoint=ma_endpoint
            )

        except Exception as e:
            logger.error(f"Certificate validation error: {e}")
            return CertValidationResult(
                valid=False,
                error=str(e)
            )

    async def validate_with_ma(
        self,
        ma_endpoint: str,
        bundle: CertificateBundle,
    ) -> MAValidationResult:
        """
        Validate with Manufacturer Authority using certificate.

        Args:
            ma_endpoint: MA validation endpoint URL
            bundle: Certificate bundle to validate

        Returns:
            MA validation result
        """
        try:
            # Prepare validation request
            payload = {
                "camera_cert": bundle.camera_cert,
                "image_hash": bundle.image_hash,
                "timestamp": bundle.timestamp,
                "bundle_signature": bundle.bundle_signature
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    ma_endpoint,
                    json=payload,
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    # Handle both formats: {"valid": bool, "message": str} or {"authority_validation": "PASS/FAIL"}
                    if "authority_validation" in data:
                        is_valid = data["authority_validation"] == "PASS"
                        message = data.get("message") or data.get("authority_validation")
                    else:
                        is_valid = data.get("valid", False)
                        message = data.get("message", "Unknown")

                    return MAValidationResult(
                        valid=is_valid,
                        message=message
                    )
                else:
                    logger.error(
                        f"MA validation failed: HTTP {response.status_code} - {response.text}"
                    )
                    return MAValidationResult(
                        valid=False,
                        message=f"MA returned HTTP {response.status_code}"
                    )

        except httpx.TimeoutException:
            logger.error(f"MA validation timeout: {ma_endpoint}")
            return MAValidationResult(
                valid=False,
                message="MA validation timeout"
            )
        except Exception as e:
            logger.error(f"MA validation error: {e}")
            return MAValidationResult(
                valid=False,
                message=f"MA validation error: {str(e)}"
            )


# Singleton instance
certificate_validator = CertificateValidatorService()
