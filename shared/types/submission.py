"""
Submission types for Camera → Aggregator communication.

These types define what cameras send to the aggregation server for
authentication and batching to the blockchain.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class AuthenticationBundle:
    """
    Complete authentication data sent from camera to aggregation server.

    This bundle contains everything needed to validate and record an image's
    authenticity on the blockchain.

    Attributes:
        image_hash: SHA-256 hash of raw Bayer sensor data (64 hex chars)
        encrypted_nuc_token: AES-GCM encrypted NUC hash for SMA validation
        table_references: 3 key table IDs assigned to this device (0-2499)
        key_indices: 3 key indices used for encryption (0-999)
        timestamp: Unix timestamp when image was captured
        gps_hash: Optional SHA-256 hash of GPS coordinates
        device_signature: TPM/Secure Element signature over the bundle
    """

    image_hash: str
    encrypted_nuc_token: bytes
    table_references: List[int]
    key_indices: List[int]
    timestamp: int
    gps_hash: Optional[str] = None
    device_signature: bytes = b""

    def __post_init__(self) -> None:
        """Validate field constraints."""
        # Validate image hash format
        if len(self.image_hash) != 64:
            raise ValueError(
                f"Image hash must be 64 hex chars, got {len(self.image_hash)}"
            )
        try:
            int(self.image_hash, 16)
        except ValueError:
            raise ValueError(f"Image hash must be valid hex string")

        # Validate table references
        if len(self.table_references) != 3:
            raise ValueError(
                f"Expected 3 table references, got {len(self.table_references)}"
            )

        # Validate key indices
        if len(self.key_indices) != 3:
            raise ValueError(f"Expected 3 key indices, got {len(self.key_indices)}")

        # Validate table references range
        for table_id in self.table_references:
            if not (0 <= table_id < 2500):
                raise ValueError(
                    f"Table reference {table_id} out of range [0, 2499]"
                )

        # Validate key indices range
        for key_idx in self.key_indices:
            if not (0 <= key_idx < 1000):
                raise ValueError(f"Key index {key_idx} out of range [0, 999]")

        # Validate timestamp
        if self.timestamp < 0:
            raise ValueError(f"Timestamp must be non-negative, got {self.timestamp}")

        # Validate GPS hash if provided
        if self.gps_hash is not None:
            if len(self.gps_hash) != 64:
                raise ValueError(
                    f"GPS hash must be 64 hex chars, got {len(self.gps_hash)}"
                )
            try:
                int(self.gps_hash, 16)
            except ValueError:
                raise ValueError(f"GPS hash must be valid hex string")
