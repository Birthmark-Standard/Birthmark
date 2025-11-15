"""SMA (Simulated Manufacturer Authority) mock endpoints for Phase 1."""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.database import get_db
from src.models import SMACamera, SMAKeyTable
from src.schemas import (
    CameraValidationBatchRequest,
    CameraValidationBatchResponse,
    CameraValidationResult,
)

router = APIRouter(prefix="/sma", tags=["SMA"])


# Provisioning Models


class ProvisionCameraRequest(BaseModel):
    """Request to provision a new camera."""

    camera_serial: str
    manufacturer: str
    nuc_data: str  # Raw NUC data (would be actual sensor data in production)


class ProvisionCameraResponse(BaseModel):
    """Response after provisioning a camera."""

    camera_id: str
    camera_serial: str
    nuc_hash: str
    table_ids: List[int]
    provisioned_at: str


# Provisioning Endpoint


@router.post("/provision", response_model=ProvisionCameraResponse)
async def provision_camera(
    request: ProvisionCameraRequest,
    db: AsyncSession = Depends(get_db),
) -> ProvisionCameraResponse:
    """
    Provision a new camera in the SMA.

    Creates NUC hash and assigns 3 random key tables for token encryption.
    This endpoint would be called during manufacturing in production.
    """
    # Check if camera already provisioned
    stmt = select(SMACamera).where(SMACamera.camera_serial == request.camera_serial)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Camera {request.camera_serial} already provisioned",
        )

    # Generate NUC hash from NUC data
    nuc_hash = hashlib.sha256(request.nuc_data.encode()).hexdigest()

    # Assign 3 random key tables (0-249)
    # In production, this would use a more sophisticated assignment algorithm
    table_ids = sorted(secrets.SystemRandom().sample(range(250), 3))

    # Ensure key tables exist
    await ensure_key_tables_exist(db, table_ids)

    # Create camera record
    camera = SMACamera(
        camera_serial=request.camera_serial,
        manufacturer=request.manufacturer,
        nuc_hash=nuc_hash,
        table_ids=table_ids,
        provisioned_at=datetime.now(timezone.utc),
    )
    db.add(camera)
    await db.commit()
    await db.refresh(camera)

    return ProvisionCameraResponse(
        camera_id=str(camera.camera_id),
        camera_serial=camera.camera_serial,
        nuc_hash=nuc_hash,
        table_ids=table_ids,
        provisioned_at=camera.provisioned_at.isoformat() + "Z",
    )


# Validation Endpoint


@router.post("/validate", response_model=CameraValidationBatchResponse)
async def validate_camera_tokens(
    request: CameraValidationBatchRequest,
    db: AsyncSession = Depends(get_db),
) -> CameraValidationBatchResponse:
    """
    Validate camera tokens from aggregator.

    Decrypts tokens and verifies against registered cameras.
    CRITICAL: Never receives image hashes, only encrypted tokens.
    """
    validation_results = []

    for val_req in request.validation_requests:
        result = await validate_single_token(
            transaction_id=val_req.transaction_id,
            camera_token=val_req.camera_token,
            manufacturer_authority_id=val_req.manufacturer_authority_id,
            db=db,
        )
        validation_results.append(result)

    return CameraValidationBatchResponse(validation_results=validation_results)


async def validate_single_token(
    transaction_id: str,
    camera_token,
    manufacturer_authority_id: str,
    db: AsyncSession,
) -> CameraValidationResult:
    """Validate a single camera token."""

    # In Phase 1, we simulate decryption by treating the ciphertext as the NUC hash
    # In production, this would:
    # 1. Get the key from the specified table_id and key_index
    # 2. Decrypt the ciphertext using AES-GCM with the nonce and auth_tag
    # 3. Extract the NUC hash from the decrypted data

    # Phase 1 simulation: assume ciphertext IS the NUC hash (for testing)
    # We'll look up the camera by this "decrypted" NUC hash
    simulated_nuc_hash = camera_token.ciphertext[:64]  # First 64 chars as NUC hash

    # Look up camera by NUC hash
    stmt = select(SMACamera).where(SMACamera.nuc_hash == simulated_nuc_hash)
    result = await db.execute(stmt)
    camera = result.scalar_one_or_none()

    if not camera:
        return CameraValidationResult(
            transaction_id=transaction_id,
            status="fail_unknown_camera",
        )

    # Verify table_id is assigned to this camera
    if camera_token.table_id not in camera.table_ids:
        return CameraValidationResult(
            transaction_id=transaction_id,
            status="fail_wrong_table",
        )

    # Success
    return CameraValidationResult(
        transaction_id=transaction_id,
        status="pass",
        manufacturer=camera.manufacturer,
        validated_at=datetime.now(timezone.utc).isoformat() + "Z",
    )


async def ensure_key_tables_exist(db: AsyncSession, table_ids: List[int]) -> None:
    """Ensure key tables exist, create if missing."""
    for table_id in table_ids:
        stmt = select(SMAKeyTable).where(SMAKeyTable.table_id == table_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            # Generate random 256-bit key (64 hex chars)
            master_key = secrets.token_hex(32)
            key_table = SMAKeyTable(table_id=table_id, master_key=master_key)
            db.add(key_table)

    await db.commit()


# Helper endpoints for testing


@router.get("/cameras/{camera_serial}")
async def get_camera_info(
    camera_serial: str,
    db: AsyncSession = Depends(get_db),
):
    """Get camera provisioning info (for testing only)."""
    stmt = select(SMACamera).where(SMACamera.camera_serial == camera_serial)
    result = await db.execute(stmt)
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    return {
        "camera_id": str(camera.camera_id),
        "camera_serial": camera.camera_serial,
        "manufacturer": camera.manufacturer,
        "nuc_hash": camera.nuc_hash,
        "table_ids": camera.table_ids,
        "provisioned_at": camera.provisioned_at.isoformat() + "Z",
    }


@router.get("/key-tables/{table_id}")
async def get_key_table(
    table_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get key table info (for testing only - would be secured in production)."""
    stmt = select(SMAKeyTable).where(SMAKeyTable.table_id == table_id)
    result = await db.execute(stmt)
    key_table = result.scalar_one_or_none()

    if not key_table:
        raise HTTPException(status_code=404, detail="Key table not found")

    return {
        "table_id": key_table.table_id,
        "master_key": key_table.master_key,
    }
