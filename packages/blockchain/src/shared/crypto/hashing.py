"""Cryptographic hashing utilities for blockchain."""

import hashlib
import json
from typing import Any, Dict


def sha256_hex(data: bytes) -> str:
    """Compute SHA-256 hash and return as hex string."""
    return hashlib.sha256(data).hexdigest()


def compute_block_hash(
    block_height: int,
    previous_hash: str,
    timestamp: int,
    transaction_hashes: list[str],
    validator_id: str,
) -> str:
    """
    Compute deterministic hash for a block.

    Args:
        block_height: Block number
        previous_hash: Hash of previous block
        timestamp: Unix timestamp
        transaction_hashes: List of transaction hashes in block
        validator_id: Node ID that created block

    Returns:
        SHA-256 hash (64 hex chars)
    """
    # Create canonical representation
    block_data = {
        "block_height": block_height,
        "previous_hash": previous_hash,
        "timestamp": timestamp,
        "transaction_hashes": sorted(transaction_hashes),  # Sort for determinism
        "validator_id": validator_id,
    }

    # JSON with sorted keys for determinism
    canonical_json = json.dumps(block_data, sort_keys=True, separators=(',', ':'))
    return sha256_hex(canonical_json.encode('utf-8'))


def compute_transaction_hash(
    image_hashes: list[str],
    timestamps: list[int],
    aggregator_id: str,
) -> str:
    """
    Compute deterministic hash for a transaction (batch).

    Args:
        image_hashes: List of image SHA-256 hashes
        timestamps: Corresponding timestamps
        aggregator_id: Node ID that submitted batch

    Returns:
        SHA-256 hash (64 hex chars)
    """
    tx_data = {
        "image_hashes": sorted(image_hashes),  # Sort for determinism
        "timestamps": timestamps,
        "aggregator_id": aggregator_id,
    }

    canonical_json = json.dumps(tx_data, sort_keys=True, separators=(',', ':'))
    return sha256_hex(canonical_json.encode('utf-8'))


def verify_hash_format(hash_str: str) -> bool:
    """
    Verify that a string is a valid SHA-256 hash.

    Args:
        hash_str: String to validate

    Returns:
        True if valid 64-character hex string
    """
    if not isinstance(hash_str, str):
        return False
    if len(hash_str) != 64:
        return False
    try:
        int(hash_str, 16)  # Check if valid hex
        return True
    except ValueError:
        return False
