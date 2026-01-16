# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Blockchain client for submitting validated hashes to the Birthmark blockchain.

This client handles direct submission of individual image hashes to the blockchain
after SMA/SSA validation. No batching is used since the custom Birthmark blockchain
has no gas fees.
"""

import logging
import httpx
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def round_timestamp_to_minute(timestamp: int) -> int:
    """
    Round Unix timestamp up to the nearest minute.

    This obfuscates exact capture timing by grouping all submissions
    from the same minute under an identical timestamp.

    Args:
        timestamp: Unix timestamp in seconds

    Returns:
        Timestamp rounded up to the nearest minute (60-second boundary)

    Example:
        1699564813 -> 1699564860 (rounds up 13 seconds to next minute)
        1699564800 -> 1699564800 (already on minute boundary)
    """
    # Round up to next minute: divide by 60, add 1 if remainder, multiply by 60
    remainder = timestamp % 60
    if remainder == 0:
        return timestamp
    return timestamp + (60 - remainder)


@dataclass
class BlockchainSubmissionResponse:
    """Response from blockchain submission."""
    success: bool
    tx_id: Optional[int] = None
    block_height: Optional[int] = None
    message: Optional[str] = None


class BlockchainClient:
    """
    Client for submitting validated image hashes to the Birthmark blockchain.

    Architecture:
    - Direct submission: Each hash submitted individually (no batching)
    - No gas fees: Custom blockchain operated by institutions
    - Simple verification: Users can hash their image and query directly
    """

    def __init__(
        self,
        blockchain_endpoint: str = "http://localhost:8545",
        timeout: float = 10.0,
    ):
        """
        Initialize blockchain client.

        Args:
            blockchain_endpoint: URL of blockchain node API
            timeout: Request timeout in seconds
        """
        self.endpoint = blockchain_endpoint
        self.timeout = timeout

    async def submit_hash(
        self,
        image_hash: str,
        timestamp: int,
        submission_server_id: str,
        modification_level: int = 0,
        parent_image_hash: Optional[str] = None,
        gps_hash: Optional[str] = None,
    ) -> BlockchainSubmissionResponse:
        """
        Submit a single validated image hash to the blockchain.

        Args:
            image_hash: SHA-256 hash of image (64 hex chars)
            timestamp: Unix timestamp when server received submission
            submission_server_id: ID of this submission server node
            modification_level: 0=raw, 1=processed
            parent_image_hash: Parent hash for provenance chain (if processed)
            gps_hash: Optional SHA-256 GPS location hash

        Returns:
            Blockchain submission response with tx_id and block_height

        Note:
            Timestamp is rounded up to the nearest minute for privacy.
            All submissions in the same minute receive identical timestamps.
        """
        # Round timestamp to nearest minute for privacy
        rounded_timestamp = round_timestamp_to_minute(timestamp)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.endpoint}/api/v1/blockchain/submit",
                    json={
                        "image_hash": image_hash,
                        "timestamp": rounded_timestamp,
                        "submission_server_id": submission_server_id,
                        "modification_level": modification_level,
                        "parent_image_hash": parent_image_hash,
                        "gps_hash": gps_hash,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.info(
                        f"Hash {image_hash[:16]}... submitted to blockchain: "
                        f"tx_id={data.get('tx_id')}, block_height={data.get('block_height')}"
                    )
                    return BlockchainSubmissionResponse(
                        success=True,
                        tx_id=data.get("tx_id"),
                        block_height=data.get("block_height"),
                        message=data.get("message"),
                    )
                else:
                    logger.error(
                        f"Blockchain submission failed for {image_hash[:16]}...: "
                        f"{response.status_code} - {response.text}"
                    )
                    return BlockchainSubmissionResponse(
                        success=False,
                        message=f"HTTP {response.status_code}: {response.text}",
                    )

        except httpx.TimeoutException:
            logger.error(f"Blockchain submission timeout for {image_hash[:16]}...")
            return BlockchainSubmissionResponse(
                success=False,
                message="Blockchain node timeout",
            )

        except httpx.ConnectError:
            logger.error(
                f"Cannot connect to blockchain node at {self.endpoint} "
                f"for {image_hash[:16]}..."
            )
            return BlockchainSubmissionResponse(
                success=False,
                message=f"Cannot connect to blockchain node at {self.endpoint}",
            )

        except Exception as e:
            logger.error(f"Blockchain submission error for {image_hash[:16]}...: {e}")
            return BlockchainSubmissionResponse(
                success=False,
                message=str(e),
            )


# Global blockchain client instance
blockchain_client = BlockchainClient()
