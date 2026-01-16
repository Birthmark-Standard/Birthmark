# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""Pydantic schemas for API request/response validation."""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator
import re
import base64


class ImageHashEntry(BaseModel):
    """Single image hash with modification level and parent reference."""

    image_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 hash (64 hex chars)")
    modification_level: int = Field(..., ge=0, le=1, description="0=raw, 1=processed")
    parent_image_hash: Optional[str] = Field(None, min_length=64, max_length=64, description="Parent hash for provenance")

    @field_validator("image_hash", "parent_image_hash")
    @classmethod
    def validate_hash(cls, v: Optional[str]) -> Optional[str]:
        """Validate SHA-256 hash format."""
        if v is None:
            return v
        if not re.match(r'^[a-f0-9]{64}$', v, re.IGNORECASE):
            raise ValueError("Hash must be 64 hexadecimal characters")
        return v.lower()


class CameraToken(BaseModel):
    """Structured camera token with AES-GCM components."""

    ciphertext: str = Field(..., description="Hex-encoded AES-GCM ciphertext")
    auth_tag: str = Field(..., min_length=32, max_length=32, description="AES-GCM auth tag (32 hex chars)")
    nonce: str = Field(..., min_length=24, max_length=24, description="AES-GCM nonce (24 hex chars)")
    table_id: int = Field(..., ge=0, lt=250, description="Key table ID (0-249)")
    key_index: int = Field(..., ge=0, lt=1000, description="Key index within table (0-999)")

    @field_validator("ciphertext", "auth_tag", "nonce")
    @classmethod
    def validate_hex(cls, v: str) -> str:
        """Validate hexadecimal encoding."""
        if not re.match(r'^[a-f0-9]+$', v, re.IGNORECASE):
            raise ValueError("Must be hexadecimal string")
        return v.lower()


class ManufacturerCert(BaseModel):
    """Manufacturer certificate with authority identification."""

    authority_id: str = Field(..., description="Manufacturer authority ID (e.g., 'CANON_001')")
    validation_endpoint: str = Field(..., description="URL to manufacturer's validation server")

    @field_validator("validation_endpoint")
    @classmethod
    def validate_endpoint(cls, v: str) -> str:
        """Validate endpoint is a URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Validation endpoint must be HTTP(S) URL")
        return v


class CameraSubmission(BaseModel):
    """Camera submission with 2-hash array (raw + processed) - Phase 1."""

    submission_type: Literal["camera"] = "camera"
    image_hashes: List[ImageHashEntry] = Field(
        ...,
        min_length=1,
        max_length=2,
        description="1-2 image hashes (raw, processed)"
    )
    camera_token: CameraToken = Field(..., description="Structured camera authentication token")
    manufacturer_cert: ManufacturerCert = Field(..., description="Manufacturer certificate")
    timestamp: int = Field(..., gt=0, description="Unix timestamp when image was captured")

    @field_validator("image_hashes")
    @classmethod
    def validate_hash_consistency(cls, v: List[ImageHashEntry]) -> List[ImageHashEntry]:
        """Validate modification levels and parent references are consistent."""
        if len(v) == 2:
            # First should be raw (level 0), second should be processed (level 1)
            if v[0].modification_level != 0:
                raise ValueError("First hash must be raw (modification_level=0)")
            if v[1].modification_level != 1:
                raise ValueError("Second hash must be processed (modification_level=1)")
            # Processed must reference raw as parent
            if v[1].parent_image_hash != v[0].image_hash:
                raise ValueError("Processed hash must have raw hash as parent")
            # Raw cannot have parent
            if v[0].parent_image_hash is not None:
                raise ValueError("Raw hash cannot have parent")
        elif len(v) == 1:
            # Single hash must be raw
            if v[0].modification_level != 0:
                raise ValueError("Single hash submission must be raw (modification_level=0)")
            if v[0].parent_image_hash is not None:
                raise ValueError("Raw hash cannot have parent")
        return v


# DEPRECATED: Old Phase 1 format (kept for backward compatibility)
class AuthenticationBundle(BaseModel):
    """Camera submission bundle (DEPRECATED - use CameraSubmission instead)."""

    image_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 hash (64 hex chars)")
    encrypted_nuc_token: bytes = Field(..., description="AES-GCM encrypted NUC hash")
    table_references: List[int] = Field(..., min_length=3, max_length=3, description="3 table IDs (0-2499)")
    key_indices: List[int] = Field(..., min_length=3, max_length=3, description="3 key indices (0-999)")
    timestamp: int = Field(..., gt=0, description="Unix timestamp")
    gps_hash: Optional[str] = Field(None, min_length=64, max_length=64, description="Optional GPS hash")
    owner_hash: Optional[str] = Field(None, min_length=64, max_length=64, description="Optional SHA-256 hash of (owner_name + owner_salt)")
    device_signature: bytes = Field(..., description="TPM signature over bundle")

    @field_validator("image_hash", "gps_hash", "owner_hash")
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
    owner_hash: Optional[str] = Field(None, min_length=64, max_length=64, description="Optional SHA-256 hash of (owner_name + owner_salt)")
    bundle_signature: str = Field(..., description="Base64-encoded ECDSA signature over bundle")

    @field_validator("image_hash", "gps_hash", "owner_hash")
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
    modification_level: Optional[int] = None
    software_version: Optional[str] = None


class ProvenanceChain(BaseModel):
    """Complete provenance chain for an image."""

    image_hash: str
    verified: bool
    chain: List[ProvenanceItem]
    chain_length: int
