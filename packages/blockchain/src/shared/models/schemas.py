"""Pydantic schemas for API request/response validation."""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
import re
import base64


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


class CertificateBundle(BaseModel):
    """
    Certificate-based submission bundle (NEW format).

    Replaces AuthenticationBundle with self-contained certificate documents.
    Camera certificate includes encrypted NUC, key table/index, and MA endpoint.
    Software certificate includes version info and SA endpoint (Phase 2).
    """

    image_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 hash (64 hex chars)")
    camera_cert: str = Field(..., description="Base64-encoded DER camera certificate")
    software_cert: Optional[str] = Field(None, description="Base64-encoded DER software cert (Phase 2)")
    timestamp: int = Field(..., gt=0, description="Unix timestamp")
    gps_hash: Optional[str] = Field(None, min_length=64, max_length=64, description="Optional GPS hash")
    bundle_signature: str = Field(..., description="Base64-encoded ECDSA signature over bundle")

    @field_validator("image_hash", "gps_hash")
    @classmethod
    def validate_hash(cls, v: Optional[str]) -> Optional[str]:
        """Validate SHA-256 hash format."""
        if v is None:
            return v
        if not re.match(r'^[a-f0-9]{64}$', v, re.IGNORECASE):
            raise ValueError("Hash must be 64 hexadecimal characters")
        return v.lower()

    @field_validator("camera_cert", "software_cert", "bundle_signature")
    @classmethod
    def validate_base64(cls, v: Optional[str]) -> Optional[str]:
        """Validate base64 encoding."""
        if v is None:
            return v
        try:
            base64.b64decode(v)
            return v
        except Exception as e:
            raise ValueError(f"Invalid base64 encoding: {e}")

    def get_camera_cert_bytes(self) -> bytes:
        """Decode and return camera certificate bytes."""
        return base64.b64decode(self.camera_cert)

    def get_software_cert_bytes(self) -> Optional[bytes]:
        """Decode and return software certificate bytes."""
        if self.software_cert:
            return base64.b64decode(self.software_cert)
        return None

    def get_signature_bytes(self) -> bytes:
        """Decode and return signature bytes."""
        return base64.b64decode(self.bundle_signature)


class SubmissionResponse(BaseModel):
    """Response after camera submission."""

    receipt_id: str
    status: str  # pending_validation, validated, batched, confirmed
    message: str


class SMAValidationRequest(BaseModel):
    """Request to SMA for token validation (DEPRECATED - use CertificateValidationRequest)."""

    encrypted_token: bytes
    table_references: List[int]
    key_indices: List[int]


class CertificateValidationRequest(BaseModel):
    """Request to MA/SA for certificate-based validation (NEW format)."""

    camera_cert: str = Field(..., description="Base64-encoded DER camera certificate")
    image_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 image hash")

    @field_validator("image_hash")
    @classmethod
    def validate_hash(cls, v: str) -> str:
        """Validate SHA-256 hash format."""
        if not re.match(r'^[a-f0-9]{64}$', v, re.IGNORECASE):
            raise ValueError("Hash must be 64 hexadecimal characters")
        return v.lower()

    @field_validator("camera_cert")
    @classmethod
    def validate_base64(cls, v: str) -> str:
        """Validate base64 encoding."""
        try:
            base64.b64decode(v)
            return v
        except Exception as e:
            raise ValueError(f"Invalid base64 encoding: {e}")

    def get_cert_bytes(self) -> bytes:
        """Decode and return certificate bytes."""
        return base64.b64decode(self.camera_cert)


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


class ModificationRecord(BaseModel):
    """Modification record from editing software (Phase 3)."""

    original_image_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 of original image")
    final_image_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 of modified image")
    modification_level: int = Field(..., ge=0, le=2, description="0=unmodified, 1=minor, 2=heavy")
    authenticated: bool = Field(..., description="Whether original was authenticated")
    original_dimensions: Optional[List[int]] = Field(None, min_length=2, max_length=2)
    final_dimensions: Optional[List[int]] = Field(None, min_length=2, max_length=2)
    software_id: str = Field(..., description="Certified software ID")
    plugin_version: str = Field(..., description="Software version")
    initialized_at: str = Field(..., description="ISO timestamp when tracking started")
    exported_at: str = Field(..., description="ISO timestamp when record exported")
    authority_type: str = Field(default="software", description="Always 'software' for editing")

    @field_validator("original_image_hash", "final_image_hash")
    @classmethod
    def validate_hash(cls, v: str) -> str:
        """Validate SHA-256 hash format."""
        if not re.match(r'^[a-f0-9]{64}$', v, re.IGNORECASE):
            raise ValueError("Hash must be 64 hexadecimal characters")
        return v.lower()


class ModificationResponse(BaseModel):
    """Response after modification record submission."""

    status: str  # recorded, pending, error
    final_image_hash: str
    modification_level: int
    chain_id: Optional[str] = None
    verification_url: Optional[str] = None
    message: Optional[str] = None


class ProvenanceItem(BaseModel):
    """Single item in provenance chain."""

    hash: str
    type: str  # capture, modification
    timestamp: str
    authority_type: str  # manufacturer, software
    authority_id: Optional[str] = None
    modification_level: Optional[int] = None
    software_version: Optional[str] = None


class ProvenanceChain(BaseModel):
    """Complete provenance chain for an image."""

    image_hash: str
    verified: bool
    chain: List[ProvenanceItem]
    chain_length: int
