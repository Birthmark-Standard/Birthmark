"""
Validation types for Aggregator ↔ SMA communication.

These types define the interface between the aggregation server and the
Simulated Manufacturer Authority (SMA) for validating camera authenticity.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class ValidationRequest:
    """
    Request from aggregator to SMA for validating a camera's authenticity.

    CRITICAL: This request never contains the image hash. The SMA validates
    that the camera is legitimate, not the image content.

    Attributes:
        encrypted_token: AES-GCM encrypted NUC hash (bytes)
        table_references: List of 3 key table IDs (0-2499)
        key_indices: List of 3 key indices within each table (0-999)
    """

    encrypted_token: bytes
    table_references: List[int]
    key_indices: List[int]

    def __post_init__(self) -> None:
        """Validate field constraints."""
        if len(self.table_references) != 3:
            raise ValueError(
                f"Expected 3 table references, got {len(self.table_references)}"
            )
        if len(self.key_indices) != 3:
            raise ValueError(f"Expected 3 key indices, got {len(self.key_indices)}")

        # Validate table references are in range [0, 2499]
        for table_id in self.table_references:
            if not (0 <= table_id < 2500):
                raise ValueError(
                    f"Table reference {table_id} out of range [0, 2499]"
                )

        # Validate key indices are in range [0, 999]
        for key_idx in self.key_indices:
            if not (0 <= key_idx < 1000):
                raise ValueError(f"Key index {key_idx} out of range [0, 999]")


@dataclass
class ValidationResponse:
    """
    Response from SMA to aggregator after validating a camera.

    Simple PASS/FAIL response. The SMA never reveals why validation failed
    to prevent information leakage.

    Attributes:
        valid: True if the camera is legitimate, False otherwise
    """

    valid: bool
