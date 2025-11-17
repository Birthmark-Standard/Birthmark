"""Pydantic schemas for API request/response validation."""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
import re


class AuthenticationBundle(BaseModel):
    """Camera submission bundle (from camera to aggregator)."""

    image_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 hash (64 hex chars)")
    encrypted_nuc_token: bytes = Field(..., description="AES-GCM encrypted NUC hash")
    table_references: List[int] = Field(..., min_length=3, max_length=3, description="3 table IDs (0-2499)")
    key_indices: List[int] = Field(..., min_length=3, max_length=3, description="3 key indices (0-999)")
    timestamp: int = Field(..., gt=0, description="Unix timestamp")
    gps_hash: Optional[str] = Field(None, min_length=64, max_length=64, description="Optional GPS hash")
    device_signature: bytes = Field(..., description="TPM signature over bundle")

    @field_validator("image_hash", "gps_hash")
    @classmethod
    def validate_hash(cls, v: Optional[str]) -> Optional[str]:
        """Validate SHA-256 hash format."""
        if v is None:
            return v
        if not re.match(r'^[a-f0-9]{64}$', v, re.IGNORECASE):
            raise ValueError("Hash must be 64 hexadecimal characters")
        return v.lower()

    @field_validator("table_references")
    @classmethod
    def validate_table_refs(cls, v: List[int]) -> List[int]:
        """Validate table references are in valid range."""
        for ref in v:
            if not 0 <= ref < 2500:
                raise ValueError(f"Table reference {ref} must be between 0-2499")
        return v

    @field_validator("key_indices")
    @classmethod
    def validate_key_indices(cls, v: List[int]) -> List[int]:
        """Validate key indices are in valid range."""
        for idx in v:
            if not 0 <= idx < 1000:
                raise ValueError(f"Key index {idx} must be between 0-999")
        return v


class SubmissionResponse(BaseModel):
    """Response after camera submission."""

    receipt_id: str
    status: str  # pending_validation, validated, batched, confirmed
    message: str


class SMAValidationRequest(BaseModel):
    """Request to SMA for token validation."""

    encrypted_token: bytes
    table_references: List[int]
    key_indices: List[int]


class SMAValidationResponse(BaseModel):
    """Response from SMA validation."""

    valid: bool
    message: Optional[str] = None


class BatchTransaction(BaseModel):
    """Batch of image hashes for blockchain transaction."""

    image_hashes: List[str] = Field(..., min_length=1, description="Array of SHA-256 hashes")
    timestamps: List[int] = Field(..., min_length=1, description="Unix timestamps for each hash")
    gps_hashes: Optional[List[Optional[str]]] = Field(None, description="Optional GPS hashes")
    aggregator_id: str = Field(..., description="Aggregator node ID")
    signature: str = Field(..., description="Aggregator signature over batch")

    @field_validator("image_hashes")
    @classmethod
    def validate_hashes(cls, v: List[str]) -> List[str]:
        """Validate all hashes are valid SHA-256."""
        for h in v:
            if not re.match(r'^[a-f0-9]{64}$', h, re.IGNORECASE):
                raise ValueError(f"Invalid hash format: {h}")
        return [h.lower() for h in v]

    @field_validator("timestamps")
    @classmethod
    def validate_timestamps_length(cls, v: List[int], info) -> List[int]:
        """Ensure timestamps match hashes length."""
        if 'image_hashes' in info.data and len(v) != len(info.data['image_hashes']):
            raise ValueError("Timestamps must match image_hashes length")
        return v


class BlockProposal(BaseModel):
    """Proposed block for consensus voting."""

    block_height: int
    previous_hash: str
    timestamp: int
    transactions: List[BatchTransaction]
    validator_id: str
    signature: str


class VerificationRequest(BaseModel):
    """Request to verify image authenticity."""

    image_hash: str = Field(..., min_length=64, max_length=64)

    @field_validator("image_hash")
    @classmethod
    def validate_hash(cls, v: str) -> str:
        """Validate SHA-256 hash format."""
        if not re.match(r'^[a-f0-9]{64}$', v, re.IGNORECASE):
            raise ValueError("Hash must be 64 hexadecimal characters")
        return v.lower()


class VerificationResponse(BaseModel):
    """Response from verification query."""

    verified: bool
    image_hash: str
    timestamp: Optional[int] = None
    block_height: Optional[int] = None
    aggregator: Optional[str] = None
    tx_hash: Optional[str] = None
    gps_hash: Optional[str] = None


class NodeStatus(BaseModel):
    """Node health and statistics."""

    node_id: str
    block_height: int
    total_hashes: int
    pending_submissions: int
    last_block_time: Optional[str] = None
    validator_nodes: int
    consensus_mode: str
    uptime: Optional[str] = None


class BlockInfo(BaseModel):
    """Block information for queries."""

    block_height: int
    block_hash: str
    previous_hash: str
    timestamp: int
    validator_id: str
    transaction_count: int
    created_at: str


class TransactionInfo(BaseModel):
    """Transaction information for queries."""

    tx_id: int
    tx_hash: str
    block_height: int
    aggregator_id: str
    batch_size: int
    created_at: str
