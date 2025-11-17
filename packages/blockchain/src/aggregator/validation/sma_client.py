"""SMA (Simulated Manufacturer Authority) validation client."""

import logging
from typing import Optional

import httpx

from src.shared.config import settings
from src.shared.models.schemas import SMAValidationRequest, SMAValidationResponse

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

    async def validate_token(
        self,
        encrypted_token: bytes,
        table_references: list[int],
        key_indices: list[int],
    ) -> SMAValidationResponse:
        """
        Validate camera token with SMA.

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


# Global client instance
sma_client = SMAClient()
