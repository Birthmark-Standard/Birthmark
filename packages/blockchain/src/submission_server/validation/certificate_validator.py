"""
Certificate validation for Birthmark blockchain aggregator.

Wraps the shared certificates package for use in blockchain aggregation.
"""

import logging
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import httpx

# Add shared package to path
shared_path = Path(__file__).resolve().parents[5] / "shared"
sys.path.insert(0, str(shared_path))

from certificates.parser import CertificateParser, CameraExtensions
from certificates.validator import CertificateValidator as BaseCertValidator
from src.shared.models.schemas import CertificateBundle, SMAValidationResponse


logger = logging.getLogger(__name__)


@dataclass
class CertValidationResult:
    """Result of certificate validation."""

    valid: bool
    error: Optional[str] = None
    cert_data: Optional[CameraExtensions] = None


@dataclass
class MAValidationResult:
    """Result of MA validation."""

    valid: bool
    message: Optional[str] = None


class CertificateValidatorService:
    """
    Service for validating camera certificates and coordinating MA validation.
    """

    def __init__(self):
        """Initialize certificate validator."""
        self.parser = CertificateParser()
        self.validator = BaseCertValidator()
        # TODO: Load trusted CA certificates from config

    async def validate_camera_certificate(
        self,
        bundle: CertificateBundle,
    ) -> CertValidationResult:
        """
        Validate camera certificate structure and signature.

        Args:
            bundle: Certificate bundle from camera

        Returns:
            Validation result with parsed certificate data
        """
        try:
            # Decode certificate
            cert_bytes = bundle.get_camera_cert_bytes()

            # Parse certificate and extract extensions
            cert, extensions = self.parser.parse_camera_cert_bytes(cert_bytes)

            logger.info(
                f"Certificate parsed: manufacturer={extensions.manufacturer_id}, "
                f"device_family={extensions.device_family}, "
                f"ma_endpoint={extensions.ma_endpoint}"
            )

            # Validate certificate structure
            # Note: For Phase 1, we skip signature verification (no CA infrastructure yet)
            # In Phase 2+, this would verify against trusted MA CA certificates
            validation_result = self.validator.validate_camera_certificate(
                cert_bytes,
                check_expiration=True,
                check_signature=False,  # Skip for Phase 1
            )

            if not validation_result.valid:
                return CertValidationResult(
                    valid=False,
                    error=validation_result.error_message
                )

            return CertValidationResult(
                valid=True,
                cert_data=extensions
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
        camera_cert: str,
        image_hash: str,
    ) -> MAValidationResult:
        """
        Validate with Manufacturer Authority using certificate.

        Args:
            ma_endpoint: MA validation endpoint URL
            camera_cert: Base64-encoded camera certificate
            image_hash: SHA-256 image hash

        Returns:
            MA validation result
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    ma_endpoint,
                    json={
                        "camera_cert": camera_cert,
                        "image_hash": image_hash,
                    },
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    validation = SMAValidationResponse(**data)
                    return MAValidationResult(
                        valid=validation.valid,
                        message=validation.message
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
