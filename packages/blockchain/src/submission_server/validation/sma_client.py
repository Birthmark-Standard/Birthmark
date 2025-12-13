"""SMA (Simulated Manufacturer Authority) validation client."""

import logging
from typing import Optional, TYPE_CHECKING

import httpx

from src.shared.config import settings
from src.shared.models.schemas import SMAValidationRequest, SMAValidationResponse

if TYPE_CHECKING:
    from src.shared.models.schemas import CameraToken

logger = logging.getLogger(__name__)


class SMAClient:
    """Client for validating camera tokens with SMA."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """
        Initialize SMA client.

        Args:
            endpoint: SMA validation endpoint URL (defaults to config)
            timeout: Request timeout in seconds (defaults to config)
        """
        self.endpoint = endpoint or settings.sma_validation_endpoint
        self.timeout = timeout or settings.sma_request_timeout

    async def validate_camera_token(
        self,
        camera_token: "CameraToken",
        manufacturer_authority_id: str,
    ) -> SMAValidationResponse:
        """
        Validate structured camera token with SMA (Phase 1 - NEW FORMAT).

        IMPORTANT: SMA never sees the image hash. Only the camera token
        is sent for validation.

        Args:
            camera_token: Structured CameraToken object with ciphertext, auth_tag, nonce, table_id, key_index
            manufacturer_authority_id: Manufacturer ID (e.g., "CANON_001")

        Returns:
            Validation response with PASS/FAIL
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.endpoint,
                    json={
                        "camera_token": {
                            "ciphertext": camera_token.ciphertext,
                            "auth_tag": camera_token.auth_tag,
                            "nonce": camera_token.nonce,
                            "table_id": camera_token.table_id,
                            "key_index": camera_token.key_index,
                        },
                        "manufacturer_authority_id": manufacturer_authority_id,
                    },
                )
                response.raise_for_status()

                data = response.json()
                return SMAValidationResponse(
                    valid=data.get("valid", False),
                    message=data.get("message"),
                )

        except httpx.TimeoutException:
            logger.error(f"SMA camera token validation timeout after {self.timeout}s")
            return SMAValidationResponse(
                valid=False,
                message="SMA validation timeout",
            )

        except httpx.HTTPError as e:
            logger.error(f"SMA camera token validation HTTP error: {e}")
            return SMAValidationResponse(
                valid=False,
                message=f"SMA HTTP error: {str(e)}",
            )

        except Exception as e:
            logger.error(f"SMA camera token validation unexpected error: {e}")
            return SMAValidationResponse(
                valid=False,
                message=f"Unexpected error: {str(e)}",
            )

    async def validate_token(
        self,
        encrypted_token: bytes,
        table_references: list[int],
        key_indices: list[int],
    ) -> SMAValidationResponse:
        """
        Validate camera token with SMA (LEGACY FORMAT - DEPRECATED).

        IMPORTANT: SMA never sees the image hash. Only the encrypted NUC token
        is sent for validation.

        Args:
            encrypted_token: AES-GCM encrypted NUC hash
            table_references: 3 table IDs (0-2499)
            key_indices: 3 key indices (0-999)

        Returns:
            Validation response with PASS/FAIL

        Raises:
            httpx.HTTPError: If SMA request fails
        """
        request = SMAValidationRequest(
            encrypted_token=encrypted_token,
            table_references=table_references,
            key_indices=key_indices,
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.endpoint,
                    json={
                        "ciphertext": request.encrypted_token.hex(),
                        "table_references": request.table_references,
                        "key_indices": request.key_indices,
                    },
                )
                response.raise_for_status()

                data = response.json()
                return SMAValidationResponse(
                    valid=data.get("valid", False),
                    message=data.get("message"),
                )

        except httpx.TimeoutException:
            logger.error(f"SMA validation timeout after {self.timeout}s")
            return SMAValidationResponse(
                valid=False,
                message="SMA validation timeout",
            )

        except httpx.HTTPError as e:
            logger.error(f"SMA validation HTTP error: {e}")
            return SMAValidationResponse(
                valid=False,
                message=f"SMA HTTP error: {str(e)}",
            )

        except Exception as e:
            logger.error(f"SMA validation unexpected error: {e}")
            return SMAValidationResponse(
                valid=False,
                message=f"Unexpected error: {str(e)}",
            )

    async def validate_certificate_bundle(
        self,
        camera_cert: str,
        image_hash: str,
        timestamp: int,
        gps_hash: Optional[str],
        bundle_signature: str,
    ) -> SMAValidationResponse:
        """
        Validate certificate bundle with SMA (Phase 2).

        This validates the complete certificate bundle including ECDSA signature.
        The SMA verifies:
        1. Certificate chain (signed by CA)
        2. Certificate expiration
        3. Device not blacklisted
        4. Bundle signature (ECDSA P-256)

        PRIVACY: SMA uses image_hash only for signature verification, not content inspection.

        Args:
            camera_cert: Base64-encoded PEM certificate
            image_hash: SHA-256 image hash
            timestamp: Unix timestamp when photo was taken
            gps_hash: Optional SHA-256 GPS hash
            bundle_signature: Base64-encoded ECDSA signature

        Returns:
            Validation response with PASS/FAIL
        """
        # Build SMA certificate validation endpoint
        # If endpoint is http://localhost:8001/validate, use http://localhost:8001/validate-cert
        cert_endpoint = self.endpoint.replace("/validate", "/validate-cert")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    cert_endpoint,
                    json={
                        "camera_cert": camera_cert,
                        "image_hash": image_hash,
                        "timestamp": timestamp,
                        "gps_hash": gps_hash,
                        "bundle_signature": bundle_signature,
                    },
                )
                response.raise_for_status()

                data = response.json()
                return SMAValidationResponse(
                    valid=data.get("valid", False),
                    message=data.get("message"),
                )

        except httpx.TimeoutException:
            logger.error(f"SMA certificate validation timeout after {self.timeout}s")
            return SMAValidationResponse(
                valid=False,
                message="SMA certificate validation timeout",
            )

        except httpx.HTTPError as e:
            logger.error(f"SMA certificate validation HTTP error: {e}")
            return SMAValidationResponse(
                valid=False,
                message=f"SMA HTTP error: {str(e)}",
            )

        except Exception as e:
            logger.error(f"SMA certificate validation unexpected error: {e}")
            return SMAValidationResponse(
                valid=False,
                message=f"Unexpected error: {str(e)}",
            )


# Global client instance
sma_client = SMAClient()
