"""SSA (Simulated Software Authority) mock endpoints for Phase 1."""

import hashlib
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.database import get_db
from src.models import SSASoftware, SSASoftwareVersion
from src.schemas import (
    SoftwareValidationBatchRequest,
    SoftwareValidationBatchResponse,
    SoftwareValidationResult,
)

router = APIRouter(prefix="/ssa", tags=["SSA"])


# Registration Models


class RegisterSoftwareRequest(BaseModel):
    """Request to register new software."""

    authority_id: str  # e.g., "ADOBE_LIGHTROOM"
    developer_name: str  # e.g., "Adobe"
    software_name: str  # e.g., "Lightroom Classic"


class RegisterSoftwareResponse(BaseModel):
    """Response after registering software."""

    software_id: str
    authority_id: str
    developer_name: str
    software_name: str
    program_hash: str
    registered_at: str


class RegisterVersionRequest(BaseModel):
    """Request to register a software version."""

    authority_id: str
    version_string: str  # e.g., "Adobe Lightroom Classic 14.1.0"


class RegisterVersionResponse(BaseModel):
    """Response after registering version."""

    version_id: str
    software_id: str
    version_string: str
    expected_token: str
    registered_at: str


# Registration Endpoints


@router.post("/register-software", response_model=RegisterSoftwareResponse)
async def register_software(
    request: RegisterSoftwareRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterSoftwareResponse:
    """
    Register new software in the SSA.

    Generates a unique program_hash for the software.
    This endpoint would be called during developer onboarding in production.
    """
    # Check if software already registered
    stmt = select(SSASoftware).where(SSASoftware.authority_id == request.authority_id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Software {request.authority_id} already registered",
        )

    # Generate unique program_hash (secret identifier for this software)
    program_hash = secrets.token_hex(32)  # 64 hex characters

    # Create software record
    software = SSASoftware(
        authority_id=request.authority_id,
        developer_name=request.developer_name,
        software_name=request.software_name,
        program_hash=program_hash,
        registered_at=datetime.now(timezone.utc),
    )
    db.add(software)
    await db.commit()
    await db.refresh(software)

    return RegisterSoftwareResponse(
        software_id=str(software.software_id),
        authority_id=software.authority_id,
        developer_name=software.developer_name,
        software_name=software.software_name,
        program_hash=program_hash,
        registered_at=software.registered_at.isoformat() + "Z",
    )


@router.post("/register-version", response_model=RegisterVersionResponse)
async def register_software_version(
    request: RegisterVersionRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterVersionResponse:
    """
    Register a new version of software.

    Generates expected_token = SHA256(program_hash || version_string).
    Software must submit this token when authenticating images.
    """
    # Find software by authority_id
    stmt = select(SSASoftware).where(SSASoftware.authority_id == request.authority_id)
    result = await db.execute(stmt)
    software = result.scalar_one_or_none()

    if not software:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Software {request.authority_id} not found. Register software first.",
        )

    # Check if version already registered
    stmt = select(SSASoftwareVersion).where(
        SSASoftwareVersion.software_id == software.software_id,
        SSASoftwareVersion.version_string == request.version_string,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Version {request.version_string} already registered",
        )

    # Generate expected token: SHA256(program_hash || version_string)
    token_input = software.program_hash + request.version_string
    expected_token = hashlib.sha256(token_input.encode()).hexdigest()

    # Create version record
    version = SSASoftwareVersion(
        software_id=software.software_id,
        version_string=request.version_string,
        expected_token=expected_token,
        registered_at=datetime.now(timezone.utc),
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)

    return RegisterVersionResponse(
        version_id=str(version.version_id),
        software_id=str(version.software_id),
        version_string=version.version_string,
        expected_token=expected_token,
        registered_at=version.registered_at.isoformat() + "Z",
    )


# Validation Endpoint


@router.post("/validate", response_model=SoftwareValidationBatchResponse)
async def validate_software_tokens(
    request: SoftwareValidationBatchRequest,
    db: AsyncSession = Depends(get_db),
) -> SoftwareValidationBatchResponse:
    """
    Validate software tokens from aggregator.

    Verifies that program_token matches expected SHA256(program_hash || version_string).
    """
    validation_results = []

    for val_req in request.validation_requests:
        result = await validate_single_token(
            submission_id=val_req.submission_id,
            program_token=val_req.program_token,
            developer_authority_id=val_req.developer_authority_id,
            version_string=val_req.version_string,
            db=db,
        )
        validation_results.append(result)

    return SoftwareValidationBatchResponse(validation_results=validation_results)


async def validate_single_token(
    submission_id: str,
    program_token: str,
    developer_authority_id: str,
    version_string: str,
    db: AsyncSession,
) -> SoftwareValidationResult:
    """Validate a single software token."""

    # Find software by authority_id
    stmt = select(SSASoftware).where(SSASoftware.authority_id == developer_authority_id)
    result = await db.execute(stmt)
    software = result.scalar_one_or_none()

    if not software:
        return SoftwareValidationResult(
            submission_id=submission_id,
            status="fail_unknown_software",
        )

    # Find version
    stmt = select(SSASoftwareVersion).where(
        SSASoftwareVersion.software_id == software.software_id,
        SSASoftwareVersion.version_string == version_string,
    )
    result = await db.execute(stmt)
    version = result.scalar_one_or_none()

    if not version:
        return SoftwareValidationResult(
            submission_id=submission_id,
            status="fail_invalid_version",
        )

    # Verify token matches expected value
    if program_token != version.expected_token:
        return SoftwareValidationResult(
            submission_id=submission_id,
            status="fail_invalid_token",
        )

    # Success
    return SoftwareValidationResult(
        submission_id=submission_id,
        status="pass",
        developer=software.developer_name,
        software_name=software.software_name,
        version=version_string,
        validated_at=datetime.now(timezone.utc).isoformat() + "Z",
    )


# Helper endpoints for testing


@router.get("/software/{authority_id}")
async def get_software_info(
    authority_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get software registration info (for testing only)."""
    stmt = select(SSASoftware).where(SSASoftware.authority_id == authority_id)
    result = await db.execute(stmt)
    software = result.scalar_one_or_none()

    if not software:
        raise HTTPException(status_code=404, detail="Software not found")

    # Get all versions
    stmt = select(SSASoftwareVersion).where(SSASoftwareVersion.software_id == software.software_id)
    result = await db.execute(stmt)
    versions = result.scalars().all()

    return {
        "software_id": str(software.software_id),
        "authority_id": software.authority_id,
        "developer_name": software.developer_name,
        "software_name": software.software_name,
        "program_hash": software.program_hash,
        "registered_at": software.registered_at.isoformat() + "Z",
        "versions": [
            {
                "version_id": str(v.version_id),
                "version_string": v.version_string,
                "expected_token": v.expected_token,
                "registered_at": v.registered_at.isoformat() + "Z",
            }
            for v in versions
        ],
    }
