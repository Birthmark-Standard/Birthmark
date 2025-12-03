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
        aggregator_id: str,
        modification_level: int = 0,
        parent_image_hash: Optional[str] = None,
        manufacturer_authority_id: Optional[str] = None,
    ) -> BlockchainSubmissionResponse:
        """
        Submit a single validated image hash to the blockchain.

        Args:
            image_hash: SHA-256 hash of image (64 hex chars)
            timestamp: Unix timestamp when photo was taken
            aggregator_id: ID of this aggregator node
            modification_level: 0=raw, 1=processed
            parent_image_hash: Parent hash for provenance chain (if processed)
            manufacturer_authority_id: Manufacturer ID (e.g., "CANON_001")

        Returns:
            Blockchain submission response with tx_id and block_height
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.endpoint}/api/v1/blockchain/submit",
                    json={
                        "image_hash": image_hash,
                        "timestamp": timestamp,
                        "aggregator_id": aggregator_id,
                        "modification_level": modification_level,
                        "parent_image_hash": parent_image_hash,
                        "manufacturer_authority_id": manufacturer_authority_id,
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
