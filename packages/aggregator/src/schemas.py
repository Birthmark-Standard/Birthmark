"""Pydantic schemas for API requests and responses."""

import re
from typing import List, Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


# Camera Submission Models


class ImageHashEntry(BaseModel):
    """Individual image hash entry in camera submission."""

    image_hash: str = Field(..., min_length=64, max_length=64)
    modification_level: int = Field(..., ge=0, le=1)
    parent_image_hash: Optional[str] = Field(None, min_length=64, max_length=64)

    @field_validator("image_hash", "parent_image_hash")
    @classmethod
    def validate_hex_hash(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r"^[0-9a-fA-F]{64}$", v):
            raise ValueError("Hash must be 64 hexadecimal characters")
        return v.lower()


class CameraToken(BaseModel):
    """Camera authentication token."""

    ciphertext: str
    auth_tag: str = Field(..., min_length=32, max_length=32)
    nonce: str = Field(..., min_length=24, max_length=24)
    table_id: int = Field(..., ge=0, lt=250)
    key_index: int = Field(..., ge=0, lt=1000)

    @field_validator("auth_tag", "nonce")
    @classmethod
    def validate_hex_string(cls, v: str) -> str:
        if not re.match(r"^[0-9a-fA-F]+$", v):
            raise ValueError("Must be hexadecimal string")
        return v.lower()


class ManufacturerCert(BaseModel):
    """Manufacturer certificate for camera validation."""

    authority_id: str = Field(..., min_length=1, max_length=100)
    validation_endpoint: str


class CameraSubmissionRequest(BaseModel):
    """Camera submission request (4 hashes: raw, processed, raw+GPS, processed+GPS)."""

    submission_type: Literal["camera"] = "camera"
    image_hashes: List[ImageHashEntry] = Field(..., min_length=1, max_length=4)
    camera_token: CameraToken
    manufacturer_cert: ManufacturerCert
    timestamp: int = Field(..., gt=0)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: int) -> int:
        import time

        current_time = int(time.time())
        # Allow ±24 hours
        if abs(v - current_time) > 86400:
            raise ValueError("Timestamp must be within ±24 hours of server time")
        return v


# Software Submission Models


class DeveloperCert(BaseModel):
    """Developer certificate for software validation."""

    authority_id: str = Field(..., min_length=1, max_length=100)
    version_string: str = Field(..., min_length=1, max_length=200)
    validation_endpoint: str


class SoftwareSubmissionRequest(BaseModel):
    """Software submission request (single edited hash with parent reference)."""

    submission_type: Literal["software"] = "software"
    image_hash: str = Field(..., min_length=64, max_length=64)
    modification_level: int = Field(..., ge=1, le=2)
    parent_image_hash: str = Field(..., min_length=64, max_length=64)
    program_token: str = Field(..., min_length=64, max_length=64)
    developer_cert: DeveloperCert

    @field_validator("image_hash", "parent_image_hash", "program_token")
    @classmethod
    def validate_hex_hash(cls, v: str) -> str:
        if not re.match(r"^[0-9a-fA-F]{64}$", v):
            raise ValueError("Hash must be 64 hexadecimal characters")
        return v.lower()


# Response Models


class SubmissionResponse(BaseModel):
    """Response after submitting authentication bundle."""

    status: Literal["accepted"] = "accepted"
    submission_ids: List[UUID]
    queue_position: int
    estimated_batch_time: str


class ErrorResponse(BaseModel):
    """Error response."""

    status: Literal["error"] = "error"
    error_code: str
    message: str
    field: Optional[str] = None


# Verification Models


class AuthorityInfo(BaseModel):
    """Authority information for verified image."""

    type: Literal["manufacturer", "developer"]
    authority_id: str
    name: Optional[str] = None  # For manufacturer
    version_string: Optional[str] = None  # For developer


class BlockchainInfo(BaseModel):
    """Blockchain posting information."""

    network: str
    tx_hash: str
    block_number: int
    confirmed_at: str


class MerkleProofStep(BaseModel):
    """Single step in Merkle proof."""

    hash: str
    position: Literal["left", "right"]


class VerificationResponse(BaseModel):
    """Response for verified image query."""

    status: Literal["verified", "pending", "not_found", "validation_failed"]
    image_hash: str
    submission_type: Optional[str] = None
    modification_level: Optional[int] = None
    modification_level_description: Optional[str] = None
    parent_image_hash: Optional[str] = None
    authority: Optional[AuthorityInfo] = None
    batch_id: Optional[str] = None
    batch_index: Optional[int] = None
    timestamp: Optional[int] = None
    merkle_root: Optional[str] = None
    merkle_proof: Optional[List[MerkleProofStep]] = None
    blockchain: Optional[BlockchainInfo] = None
    message: Optional[str] = None
    error: Optional[str] = None
    validation_status: Optional[str] = None
    estimated_batch_time: Optional[str] = None


# Batch Verification Models


class BatchVerifyRequest(BaseModel):
    """Batch verification request."""

    image_hashes: List[str] = Field(..., max_length=100)

    @field_validator("image_hashes")
    @classmethod
    def validate_hashes(cls, v: List[str]) -> List[str]:
        for hash_val in v:
            if not re.match(r"^[0-9a-fA-F]{64}$", hash_val):
                raise ValueError(f"Invalid hash format: {hash_val}")
        return [h.lower() for h in v]


class BatchVerifyResponse(BaseModel):
    """Batch verification response."""

    results: List[VerificationResponse]


# Provenance Chain Models


class ProvenanceEntry(BaseModel):
    """Single entry in provenance chain."""

    image_hash: str
    submission_type: str
    modification_level: int
    modification_level_description: str
    authority: AuthorityInfo
    timestamp: Optional[int]
    parent_image_hash: Optional[str]


class OriginalCaptureInfo(BaseModel):
    """Information about original capture."""

    image_hash: str
    timestamp: Optional[int]
    manufacturer: str


class ProvenanceResponse(BaseModel):
    """Provenance chain response."""

    image_hash: str
    provenance_chain: List[ProvenanceEntry]
    chain_length: int
    original_capture: Optional[OriginalCaptureInfo]
    total_modification_level: Optional[int]


# Authority Validation Models (Internal)


class CameraValidationRequest(BaseModel):
    """Request to SMA for camera token validation."""

    transaction_id: str
    camera_token: CameraToken
    manufacturer_authority_id: str


class CameraValidationResult(BaseModel):
    """Result from SMA validation."""

    transaction_id: str
    status: Literal["pass", "fail_invalid_token", "fail_unknown_camera", "fail_wrong_table"]
    manufacturer: Optional[str] = None
    validated_at: Optional[str] = None


class CameraValidationBatchRequest(BaseModel):
    """Batch request to SMA."""

    validation_requests: List[CameraValidationRequest]


class CameraValidationBatchResponse(BaseModel):
    """Batch response from SMA."""

    validation_results: List[CameraValidationResult]


class SoftwareValidationRequest(BaseModel):
    """Request to SSA for program token validation."""

    submission_id: str
    program_token: str
    developer_authority_id: str
    version_string: str


class SoftwareValidationResult(BaseModel):
    """Result from SSA validation."""

    submission_id: str
    status: Literal["pass", "fail_invalid_token", "fail_unknown_software", "fail_invalid_version"]
    developer: Optional[str] = None
    software_name: Optional[str] = None
    version: Optional[str] = None
    validated_at: Optional[str] = None


class SoftwareValidationBatchRequest(BaseModel):
    """Batch request to SSA."""

    validation_requests: List[SoftwareValidationRequest]


class SoftwareValidationBatchResponse(BaseModel):
    """Batch response from SSA."""

    validation_results: List[SoftwareValidationResult]


# Health Check Models


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: Literal["healthy", "unhealthy"]
    database: str
    pending_submissions: Optional[int] = None
    last_batch: Optional[str] = None
    timestamp: str
