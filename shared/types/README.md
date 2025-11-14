# Shared Types

**Purpose:** Core data structures used across all Birthmark packages

## Overview

This directory contains the canonical type definitions for all data structures that flow through the Birthmark system. These types ensure consistency and type safety across packages.

## Files

### `submission.py`

Defines the `AuthenticationBundle` sent from cameras to the aggregation server:

```python
@dataclass
class AuthenticationBundle:
    image_hash: str              # SHA-256 of raw Bayer data (64 hex chars)
    encrypted_nuc_token: bytes   # AES-GCM encrypted NUC hash
    table_references: List[int]  # 3 table IDs (0-2499)
    key_indices: List[int]       # 3 key indices (0-999)
    timestamp: int               # Unix timestamp
    gps_hash: Optional[str]      # SHA-256 of GPS coordinates (optional)
    device_signature: bytes      # TPM signature over bundle
```

### `validation.py`

Defines the validation protocol between aggregator and SMA:

```python
@dataclass
class ValidationRequest:
    encrypted_token: bytes
    table_references: List[int]
    key_indices: List[int]
    # Note: NO image hash - SMA never sees image content

@dataclass
class ValidationResponse:
    valid: bool  # PASS or FAIL
    reason: Optional[str]  # Error message if FAIL
```

### `merkle.py`

Defines Merkle tree structures for batching and verification:

```python
@dataclass
class MerkleNode:
    hash: str
    left: Optional['MerkleNode']
    right: Optional['MerkleNode']

@dataclass
class MerkleProof:
    leaf_hash: str
    proof_hashes: List[str]
    leaf_index: int
    root_hash: str

@dataclass
class MerkleBatch:
    batch_id: int
    root_hash: str
    leaf_count: int
    created_at: int
```

## Design Principles

1. **Immutability:** All dataclasses use `frozen=True` where appropriate
2. **Type Safety:** Strict type hints for all fields
3. **Validation:** Use pydantic for runtime validation
4. **Serialization:** JSON-serializable for API transport
5. **Documentation:** Every field has a clear comment

## Privacy by Design

**Critical:** The `ValidationRequest` intentionally does NOT include `image_hash`. This ensures the SMA can never correlate camera authenticity with image content.

## Usage Example

```python
from shared.types import AuthenticationBundle

bundle = AuthenticationBundle(
    image_hash="a1b2c3d4...",
    encrypted_nuc_token=b"...",
    table_references=[42, 1337, 2001],
    key_indices=[7, 99, 512],
    timestamp=1732000000,
    gps_hash=None,
    device_signature=b"..."
)

# Serialize to JSON
bundle_json = bundle.to_json()

# Deserialize from JSON
bundle = AuthenticationBundle.from_json(bundle_json)
```

## Testing

```bash
cd shared/types
pytest tests/test_*.py
```

Tests cover:
- Type validation
- Serialization/deserialization
- Edge cases (empty fields, invalid data)
- Privacy invariants (ValidationRequest cannot contain image hash)
