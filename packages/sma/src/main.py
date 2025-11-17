"""
Simulated Manufacturer Authority (SMA) - Main Application

FastAPI application providing:
- Device provisioning endpoints (Phase 2)
- NUC token validation endpoints
- Health check and monitoring

Phase 1: Manual provisioning via script
Phase 2: Full API with automatic provisioning
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from pathlib import Path
from datetime import datetime

from .provisioning.certificate import CertificateAuthority
from .provisioning.provisioner import (
    DeviceProvisioner,
    ProvisioningRequest,
    ProvisioningResponse
)
from .key_tables.table_manager import KeyTableManager
from .identity.device_registry import DeviceRegistry, DeviceRegistration

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))
from certificates.parser import CertificateParser


# Pydantic models for API
class ProvisionDeviceRequest(BaseModel):
    """API request model for device provisioning."""
    device_serial: str = Field(..., description="Unique device serial number")
    device_family: str = Field(default="Raspberry Pi", description="Device type")
    nuc_hash: Optional[str] = Field(None, description="Hex-encoded NUC hash (optional)")


class ProvisionDeviceResponse(BaseModel):
    """API response model for device provisioning."""
    device_serial: str
    device_certificate: str
    certificate_chain: str
    device_private_key: str
    device_public_key: str
    table_assignments: List[int]
    nuc_hash: str
    device_family: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    total_devices: int
    total_tables: int
    service: str


class StatsResponse(BaseModel):
    """Statistics response."""
    total_devices: int
    devices_by_family: dict
    total_table_assignments: int
    unique_tables_used: int
    table_statistics: dict


# Create FastAPI app
app = FastAPI(
    title="Birthmark SMA (Simulated Manufacturer Authority)",
    description="Device provisioning and NUC token validation service",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state (initialized on startup)
ca: Optional[CertificateAuthority] = None
table_manager: Optional[KeyTableManager] = None
device_registry: Optional[DeviceRegistry] = None
provisioner: Optional[DeviceProvisioner] = None


@app.on_event("startup")
async def startup_event():
    """Initialize SMA components on startup."""
    global ca, table_manager, device_registry, provisioner

    # Define storage paths
    base_path = Path(__file__).parent.parent / "data"
    base_path.mkdir(exist_ok=True)

    ca_cert_path = base_path / "intermediate-ca.crt"
    ca_key_path = base_path / "intermediate-ca.key"
    key_tables_path = base_path / "key_tables.json"
    registry_path = base_path / "device_registry.json"

    # Initialize or load CA
    if ca_cert_path.exists() and ca_key_path.exists():
        ca = CertificateAuthority(ca_cert_path, ca_key_path)
        print(f"✓ Loaded CA certificates from {ca_cert_path}")
    else:
        print("⚠ CA certificates not found. Run setup script to generate CA.")
        print(f"  Expected: {ca_cert_path} and {ca_key_path}")
        ca = None  # Will fail on provisioning attempts

    # Initialize or load key tables
    table_manager = KeyTableManager(
        total_tables=10,  # Phase 1: 10 tables
        tables_per_device=3,
        storage_path=key_tables_path
    )

    if key_tables_path.exists():
        table_manager.load_from_file()
        print(f"✓ Loaded {len(table_manager.key_tables)} key tables from {key_tables_path}")
    else:
        print(f"⚠ Key tables not found at {key_tables_path}")
        print("  Run setup script to generate key tables.")

    # Initialize device registry
    device_registry = DeviceRegistry(storage_path=registry_path)
    if registry_path.exists():
        device_registry.load_from_file()
        print(f"✓ Loaded {len(device_registry._registrations)} device registrations")
    else:
        print("✓ Initialized empty device registry")

    # Initialize provisioner
    if ca:
        provisioner = DeviceProvisioner(ca, table_manager)
        print("✓ Device provisioner ready")
    else:
        print("⚠ Device provisioner unavailable (CA not loaded)")


@app.get("/", tags=["General"])
async def root():
    """Root endpoint."""
    return {
        "service": "Birthmark SMA",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
async def health_check():
    """
    Health check endpoint.

    Returns service status and basic statistics.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        total_devices=len(device_registry._registrations) if device_registry else 0,
        total_tables=len(table_manager.key_tables) if table_manager else 0,
        service="sma"
    )


@app.get("/stats", response_model=StatsResponse, tags=["Monitoring"])
async def get_statistics():
    """
    Get detailed statistics about provisioned devices.
    """
    if not device_registry or not table_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )

    device_stats = device_registry.get_statistics()
    table_stats = table_manager.get_statistics()

    return StatsResponse(
        total_devices=device_stats["total_devices"],
        devices_by_family=device_stats["devices_by_family"],
        total_table_assignments=device_stats["total_table_assignments"],
        unique_tables_used=device_stats["unique_tables_used"],
        table_statistics=table_stats
    )


@app.post(
    "/api/v1/devices/provision",
    response_model=ProvisionDeviceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Provisioning"]
)
async def provision_device(request: ProvisionDeviceRequest):
    """
    Provision a new device.

    Phase 1: Manual provisioning via script (this endpoint for testing)
    Phase 2: Production endpoint for automated provisioning

    Args:
        request: Device provisioning request

    Returns:
        Complete provisioning data including:
        - Device certificate and private key
        - Table assignments
        - NUC hash (simulated in Phase 1)

    Raises:
        HTTPException: If provisioning fails or device already exists
    """
    if not provisioner:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Provisioner not initialized (CA certificates missing)"
        )

    # Check if device already registered
    if device_registry.device_exists(request.device_serial):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device {request.device_serial} already provisioned"
        )

    try:
        # Convert hex NUC hash to bytes if provided
        nuc_hash_bytes = None
        if request.nuc_hash:
            try:
                nuc_hash_bytes = bytes.fromhex(request.nuc_hash)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid NUC hash format (must be hex)"
                )

        # Provision device
        prov_request = ProvisioningRequest(
            device_serial=request.device_serial,
            device_family=request.device_family,
            nuc_hash=nuc_hash_bytes
        )

        response = provisioner.provision_device(prov_request)

        # Register device in registry
        registration = DeviceRegistration(
            device_serial=response.device_serial,
            nuc_hash=response.nuc_hash,
            table_assignments=response.table_assignments,
            device_certificate=response.device_certificate,
            device_public_key=response.device_public_key,
            device_family=response.device_family,
            provisioned_at=datetime.utcnow().isoformat()
        )

        device_registry.register_device(registration)

        # Save registry to disk
        device_registry.save_to_file()

        # Save key table assignments to disk
        table_manager.save_to_file()

        return ProvisionDeviceResponse(**response.to_dict())

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Provisioning failed: {str(e)}"
        )


@app.get("/api/v1/devices/{device_serial}", tags=["Provisioning"])
async def get_device_info(device_serial: str):
    """
    Get device information (non-sensitive data only).

    Args:
        device_serial: Device serial number

    Returns:
        Device information (without private keys)
    """
    if not device_registry:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )

    device = device_registry.get_device(device_serial)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_serial} not found"
        )

    return {
        "device_serial": device.device_serial,
        "device_family": device.device_family,
        "table_assignments": device.table_assignments,
        "provisioned_at": device.provisioned_at,
        # Exclude sensitive data like NUC hash, certificates, keys
    }


@app.get("/api/v1/devices", tags=["Provisioning"])
async def list_devices(device_family: Optional[str] = None):
    """
    List all provisioned devices.

    Args:
        device_family: Optional filter by device family

    Returns:
        List of device serial numbers and basic info
    """
    if not device_registry:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )

    devices = device_registry.list_devices(device_family)

    return {
        "total": len(devices),
        "devices": [
            {
                "device_serial": d.device_serial,
                "device_family": d.device_family,
                "provisioned_at": d.provisioned_at
            }
            for d in devices
        ]
    }


# Validation endpoint - matches blockchain expectation
class ValidationRequest(BaseModel):
    """Request model for token validation from blockchain aggregator."""
    ciphertext: str = Field(..., description="Hex-encoded encrypted NUC token")
    table_references: List[int] = Field(..., min_length=3, max_length=3, description="3 table IDs")
    key_indices: List[int] = Field(..., min_length=3, max_length=3, description="3 key indices")


class ValidationResponse(BaseModel):
    """Response model for validation."""
    valid: bool
    message: Optional[str] = None


@app.post("/validate", response_model=ValidationResponse, tags=["Validation"])
async def validate_token(request: ValidationRequest):
    """
    Validate encrypted NUC token from blockchain aggregator.

    Phase 1: Simplified validation (format checking + table existence)
    Phase 2: Full cryptographic validation (decrypt + compare NUC hash)

    Args:
        request: Validation request with encrypted token and table references

    Returns:
        Validation response (PASS/FAIL)

    Note: This endpoint is called by the blockchain aggregator, NOT directly by cameras.
    The aggregator never sends the image hash - only the encrypted camera token.
    """
    if not table_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMA not initialized (key tables not loaded)"
        )

    # Validate request format
    try:
        # Check encrypted token is valid hex
        try:
            encrypted_bytes = bytes.fromhex(request.ciphertext)
        except ValueError:
            return ValidationResponse(
                valid=False,
                message="Invalid ciphertext format (must be hex)"
            )

        # Check table references are valid
        for table_id in request.table_references:
            if table_id not in table_manager.key_tables:
                return ValidationResponse(
                    valid=False,
                    message=f"Invalid table reference: {table_id}"
                )

        # Check key indices are in valid range (0-999)
        for key_idx in request.key_indices:
            if not (0 <= key_idx < 1000):
                return ValidationResponse(
                    valid=False,
                    message=f"Invalid key index: {key_idx} (must be 0-999)"
                )

        # Phase 1: Simple validation (format checks passed)
        # Phase 2: TODO - Decrypt token using table keys and validate against NUC hash
        # For Phase 1 testing, we accept valid format as PASS
        return ValidationResponse(
            valid=True,
            message="Phase 1 validation: format valid"
        )

    except Exception as e:
        # Log error but don't expose details to aggregator
        print(f"Validation error: {str(e)}")
        return ValidationResponse(
            valid=False,
            message="Validation failed"
        )


class CertificateValidationRequest(BaseModel):
    """Request model for certificate-based validation (NEW format)."""
    camera_cert: str = Field(..., description="Base64-encoded DER camera certificate")
    image_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 image hash")


@app.post("/validate-cert", response_model=ValidationResponse, tags=["Validation"])
async def validate_certificate(request: CertificateValidationRequest):
    """
    Validate camera certificate (NEW format).

    This endpoint receives the camera certificate and extracts the encrypted NUC,
    key table ID, and key index from the certificate extensions.

    Phase 1: Certificate parsing + format validation
    Phase 2: Full cryptographic validation (decrypt NUC + compare to registry)

    Args:
        request: Certificate validation request

    Returns:
        Validation response (PASS/FAIL)

    Note: The MA never uses the image_hash in validation logic - it's only for
    logging/audit purposes. The MA validates camera authenticity, not image content.
    """
    if not table_manager or not device_registry:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMA not initialized"
        )

    try:
        # Parse certificate
        import base64
        cert_bytes = base64.b64decode(request.camera_cert)

        parser = CertificateParser()
        cert, extensions = parser.parse_camera_cert_bytes(cert_bytes)

        print(f"Certificate validation request:")
        print(f"  Manufacturer: {extensions.manufacturer_id}")
        print(f"  Device Family: {extensions.device_family}")
        print(f"  Key Table ID: {extensions.key_table_id}")
        print(f"  Key Index: {extensions.key_index}")
        print(f"  Image Hash: {request.image_hash[:16]}... (not used in validation)")

        # Validate table exists
        if extensions.key_table_id not in table_manager.key_tables:
            return ValidationResponse(
                valid=False,
                message=f"Invalid table ID: {extensions.key_table_id}"
            )

        # Validate key index range
        if not (0 <= extensions.key_index < 1000):
            return ValidationResponse(
                valid=False,
                message=f"Invalid key index: {extensions.key_index}"
            )

        # Validate encrypted NUC length
        if len(extensions.encrypted_nuc) != 60:
            return ValidationResponse(
                valid=False,
                message=f"Invalid encrypted NUC length: {len(extensions.encrypted_nuc)}"
            )

        # Phase 1: Format validation passed
        # Phase 2 TODO: Decrypt NUC using table key and validate against registry
        return ValidationResponse(
            valid=True,
            message="Phase 1 certificate validation: format valid"
        )

    except Exception as e:
        print(f"Certificate validation error: {str(e)}")
        return ValidationResponse(
            valid=False,
            message=f"Certificate validation failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
