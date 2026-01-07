#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Merkle tree data structures

This module defines the data structures for Merkle trees and proofs used
in blockchain batching.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MerkleProof:
    """
    Merkle proof for verifying an image hash is included in a batch.

    A Merkle proof allows anyone to verify that a specific image hash was
    included in a batch without downloading the entire batch. The proof
    consists of sibling hashes along the path from leaf to root.

    Attributes:
        image_hash: The image hash being proven (64 hex chars)
        batch_id: ID of the batch containing this image
        leaf_index: Position of image in the batch (0-indexed)
        proof_hashes: List of sibling hashes from leaf to root (each 64 hex chars)
        merkle_root: Root hash of the Merkle tree (64 hex chars)

    Example:
        >>> proof = MerkleProof(
        ...     image_hash="a" * 64,
        ...     batch_id=42,
        ...     leaf_index=7,
        ...     proof_hashes=["b" * 64, "c" * 64, "d" * 64],
        ...     merkle_root="e" * 64
        ... )
    """

    image_hash: str  # 64 hex chars (SHA-256)
    batch_id: int
    leaf_index: int
    proof_hashes: List[str]  # List of 64-char hex strings
    merkle_root: str  # 64 hex chars (SHA-256)

    def __post_init__(self):
        """Validate proof after initialization."""
        # Validate image_hash
        if not isinstance(self.image_hash, str) or len(self.image_hash) != 64:
            raise ValueError(f"image_hash must be 64-character hex string, got {len(self.image_hash)}")

        # Validate batch_id
        if not isinstance(self.batch_id, int) or self.batch_id < 0:
            raise ValueError(f"batch_id must be non-negative integer, got {self.batch_id}")

        # Validate leaf_index
        if not isinstance(self.leaf_index, int) or self.leaf_index < 0:
            raise ValueError(f"leaf_index must be non-negative integer, got {self.leaf_index}")

        # Validate proof_hashes
        if not isinstance(self.proof_hashes, list):
            raise ValueError(f"proof_hashes must be a list, got {type(self.proof_hashes)}")

        for i, proof_hash in enumerate(self.proof_hashes):
            if not isinstance(proof_hash, str) or len(proof_hash) != 64:
                raise ValueError(
                    f"proof_hashes[{i}] must be 64-character hex string, got {len(proof_hash)}"
                )

        # Validate merkle_root
        if not isinstance(self.merkle_root, str) or len(self.merkle_root) != 64:
            raise ValueError(f"merkle_root must be 64-character hex string, got {len(self.merkle_root)}")

    @property
    def proof_depth(self) -> int:
        """Get the depth of the Merkle tree (number of levels)."""
        return len(self.proof_hashes)


@dataclass
class BatchInfo:
    """
    Information about a batch posted to the blockchain.

    Attributes:
        batch_id: Unique identifier for this batch
        merkle_root: Root hash of the Merkle tree (64 hex chars)
        image_count: Number of images in this batch
        created_at: ISO 8601 timestamp when batch was created
        blockchain_tx: Transaction hash on blockchain (66 chars for Ethereum)
        confirmed: Whether transaction is confirmed on blockchain
        confirmation_time: Optional ISO 8601 timestamp when confirmed

    Example:
        >>> batch = BatchInfo(
        ...     batch_id=42,
        ...     merkle_root="a" * 64,
        ...     image_count=1000,
        ...     created_at="2024-11-13T10:00:00Z",
        ...     blockchain_tx="0x" + "b" * 64,
        ...     confirmed=True,
        ...     confirmation_time="2024-11-13T10:05:00Z"
        ... )
    """

    batch_id: int
    merkle_root: str  # 64 hex chars
    image_count: int
    created_at: str  # ISO 8601
    blockchain_tx: Optional[str] = None  # Ethereum tx hash (0x + 64 hex)
    confirmed: bool = False
    confirmation_time: Optional[str] = None  # ISO 8601

    def __post_init__(self):
        """Validate batch info after initialization."""
        # Validate batch_id
        if not isinstance(self.batch_id, int) or self.batch_id < 0:
            raise ValueError(f"batch_id must be non-negative integer, got {self.batch_id}")

        # Validate merkle_root
        if not isinstance(self.merkle_root, str) or len(self.merkle_root) != 64:
            raise ValueError(f"merkle_root must be 64-character hex string, got {len(self.merkle_root)}")

        # Validate image_count
        if not isinstance(self.image_count, int) or self.image_count <= 0:
            raise ValueError(f"image_count must be positive integer, got {self.image_count}")

        # Validate blockchain_tx if present
        if self.blockchain_tx is not None:
            if not self.blockchain_tx.startswith("0x") or len(self.blockchain_tx) != 66:
                raise ValueError(
                    f"blockchain_tx must be 66 chars (0x + 64 hex), got {len(self.blockchain_tx)}"
                )


@dataclass
class VerificationResult:
    """
    Result of verifying an image hash against the blockchain.

    Attributes:
        verified: Whether the image hash was found and verified
        image_hash: The image hash that was queried (64 hex chars)
        batch_id: Optional batch ID if verified
        timestamp: Optional timestamp when image was batched
        merkle_proof: Optional Merkle proof for verification
        blockchain_tx: Optional transaction hash
        error: Optional error message if verification failed

    Example:
        >>> result = VerificationResult(
        ...     verified=True,
        ...     image_hash="a" * 64,
        ...     batch_id=42,
        ...     timestamp="2024-11-13T10:00:00Z",
        ...     merkle_proof=MerkleProof(...),
        ...     blockchain_tx="0x" + "b" * 64
        ... )
    """

    verified: bool
    image_hash: str  # 64 hex chars
    batch_id: Optional[int] = None
    timestamp: Optional[str] = None  # ISO 8601
    merkle_proof: Optional[MerkleProof] = None
    blockchain_tx: Optional[str] = None
    error: Optional[str] = None

    def __post_init__(self):
        """Validate verification result after initialization."""
        # Validate image_hash
        if not isinstance(self.image_hash, str) or len(self.image_hash) != 64:
            raise ValueError(f"image_hash must be 64-character hex string, got {len(self.image_hash)}")

        # If verified, batch_id should be present
        if self.verified and self.batch_id is None:
            raise ValueError("batch_id must be provided if verified=True")


if __name__ == "__main__":
    print("=" * 80)
    print("Testing Merkle Data Structures")
    print("=" * 80)

    # Test 1: Valid Merkle proof
    print("\nTest 1: Valid Merkle Proof")
    try:
        proof = MerkleProof(
            image_hash="a" * 64,
            batch_id=42,
            leaf_index=7,
            proof_hashes=["b" * 64, "c" * 64, "d" * 64],
            merkle_root="e" * 64
        )
        print(f"  ✓ Created valid proof")
        print(f"    Image hash: {proof.image_hash[:16]}...")
        print(f"    Batch ID: {proof.batch_id}")
        print(f"    Leaf index: {proof.leaf_index}")
        print(f"    Proof depth: {proof.proof_depth}")
        print(f"    Merkle root: {proof.merkle_root[:16]}...")
    except Exception as e:
        print(f"  ✗ Failed: {e}")

    # Test 2: Invalid image hash
    print("\nTest 2: Invalid Image Hash (wrong length)")
    try:
        proof = MerkleProof(
            image_hash="short",
            batch_id=42,
            leaf_index=7,
            proof_hashes=["b" * 64],
            merkle_root="e" * 64
        )
        print(f"  ✗ Should have failed")
    except ValueError as e:
        print(f"  ✓ Correctly rejected: {str(e)[:60]}...")

    # Test 3: Valid batch info
    print("\nTest 3: Valid Batch Info")
    try:
        batch = BatchInfo(
            batch_id=42,
            merkle_root="a" * 64,
            image_count=1000,
            created_at="2024-11-13T10:00:00Z",
            blockchain_tx="0x" + "b" * 64,
            confirmed=True,
            confirmation_time="2024-11-13T10:05:00Z"
        )
        print(f"  ✓ Created valid batch info")
        print(f"    Batch ID: {batch.batch_id}")
        print(f"    Image count: {batch.image_count}")
        print(f"    Merkle root: {batch.merkle_root[:16]}...")
        print(f"    TX: {batch.blockchain_tx[:18]}...")
        print(f"    Confirmed: {batch.confirmed}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")

    # Test 4: Invalid blockchain tx
    print("\nTest 4: Invalid Blockchain TX (wrong format)")
    try:
        batch = BatchInfo(
            batch_id=42,
            merkle_root="a" * 64,
            image_count=1000,
            created_at="2024-11-13T10:00:00Z",
            blockchain_tx="not-a-valid-tx"  # Wrong format
        )
        print(f"  ✗ Should have failed")
    except ValueError as e:
        print(f"  ✓ Correctly rejected: {str(e)[:60]}...")

    # Test 5: Verified result
    print("\nTest 5: Verified Result")
    try:
        result = VerificationResult(
            verified=True,
            image_hash="a" * 64,
            batch_id=42,
            timestamp="2024-11-13T10:00:00Z",
            blockchain_tx="0x" + "b" * 64
        )
        print(f"  ✓ Created verified result")
        print(f"    Verified: {result.verified}")
        print(f"    Batch ID: {result.batch_id}")
        print(f"    Timestamp: {result.timestamp}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")

    # Test 6: Unverified result
    print("\nTest 6: Unverified Result")
    try:
        result = VerificationResult(
            verified=False,
            image_hash="a" * 64,
            error="Image hash not found in any batch"
        )
        print(f"  ✓ Created unverified result")
        print(f"    Verified: {result.verified}")
        print(f"    Error: {result.error}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")

    print("\n" + "=" * 80)
    print("✓ All tests passed")
    print("=" * 80)
