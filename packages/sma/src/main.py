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
from .provisioning.certificate_generator import CertificateGenerator
from .provisioning.provisioner import (
    DeviceProvisioner,
    ProvisioningRequest,
    ProvisioningResponse
)
from .key_tables.table_manager import KeyTableManager, Phase2KeyTableManager
from .identity.device_registry import DeviceRegistry, DeviceRegistration
from .identity.submission_logger import SubmissionLogger
from .identity.abuse_detection import AbuseDetector, run_daily_abuse_check
from .validation.certificate_validator import CertificateValidator
from .validation.token_validator import validate_camera_token
from .validation.validation_cache import validation_cache

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))
from certificates.parser import CertificateParser


# Pydantic models for API
class ProvisionDeviceRequest(BaseModel):
    """API request model for device provisioning (Phase 1 & 2)."""
    device_serial: str = Field(..., description="Unique device serial number")
    device_family: str = Field(default="Raspberry Pi", description="Device type")
    nuc_hash: Optional[str] = Field(None, description="Hex-encoded NUC hash (Phase 1)")
    device_secret: Optional[str] = Field(None, description="Hex-encoded device secret (Phase 2)")


class ProvisionDeviceRequestPhase2(BaseModel):
    """API request model for Phase 2 iOS provisioning."""
    device_serial: str = Field(..., description="Unique device identifier (iOS UDID)")
    device_family: str = Field(..., description="Device type (e.g., 'iOS')")
    device_secret: str = Field(..., description="Hex-encoded SHA-256 device secret (64 chars)")


class ProvisionDeviceResponse(BaseModel):
    """API response model for device provisioning (Phase 1)."""
    device_serial: str
    device_certificate: str
    certificate_chain: str
    device_private_key: str
    device_public_key: str
    table_assignments: List[int]
    nuc_hash: str
    device_family: str


class ProvisionDeviceResponsePhase2(BaseModel):
    """API response model for Phase 2 iOS provisioning."""
    device_certificate: str = Field(..., description="PEM-encoded X.509 certificate")
    device_private_key: str = Field(..., description="PEM-encoded ECDSA P-256 private key")
    certificate_chain: str = Field(..., description="PEM-encoded CA certificate chain")
    key_tables: List[List[str]] = Field(..., description="3 arrays of 1000 hex-encoded keys")
    key_table_indices: List[int] = Field(..., description="Global table indices (e.g., [42, 157, 891])")
    device_secret: str = Field(..., description="Hex-encoded device secret (echo back for verification)")


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
cert_generator: Optional[CertificateGenerator] = None  # Phase 2
cert_validator: Optional[CertificateValidator] = None  # Phase 2
table_manager: Optional[KeyTableManager] = None
device_registry: Optional[DeviceRegistry] = None
provisioner: Optional[DeviceProvisioner] = None
submission_logger: Optional[SubmissionLogger] = None
abuse_detector: Optional[AbuseDetector] = None


@app.on_event("startup")
async def startup_event():
    """Initialize SMA components on startup."""
    global ca, cert_generator, cert_validator, table_manager, device_registry, provisioner, submission_logger, abuse_detector

    # Define storage paths
    base_path = Path(__file__).parent.parent / "data"
    base_path.mkdir(exist_ok=True)
    certs_path = Path(__file__).parent.parent / "certs"

    ca_cert_path = base_path / "intermediate-ca.crt"
    ca_key_path = base_path / "intermediate-ca.key"

    # Phase 2: New CA cert paths (from generate_ca_certificate.py)
    phase2_ca_cert_path = certs_path / "ca_certificate.pem"
    phase2_ca_key_path = certs_path / "ca_private_key.pem"

    key_tables_path = base_path / "key_tables.json"
    registry_path = base_path / "device_registry.json"
    submissions_path = base_path / "submissions.json"

    # Initialize or load CA (Phase 1)
    if ca_cert_path.exists() and ca_key_path.exists():
        ca = CertificateAuthority(ca_cert_path, ca_key_path)
        print(f"✓ Loaded CA certificates from {ca_cert_path}")
    else:
        print("⚠ Phase 1 CA certificates not found at {ca_cert_path}")
        ca = None

    # Initialize CertificateGenerator (Phase 2)
    if phase2_ca_cert_path.exists() and phase2_ca_key_path.exists():
        try:
            cert_generator = CertificateGenerator(
                ca_private_key_path=str(phase2_ca_key_path),
                ca_cert_path=str(phase2_ca_cert_path)
            )
            print(f"✓ Loaded Phase 2 CertificateGenerator from {phase2_ca_cert_path}")
        except Exception as e:
            print(f"⚠ Failed to initialize Phase 2 CertificateGenerator: {e}")
            cert_generator = None
    else:
        print(f"⚠ Phase 2 CA not found. Run: python scripts/generate_ca_certificate.py")
        print(f"  Expected: {phase2_ca_cert_path} and {phase2_ca_key_path}")
        cert_generator = None

    # Initialize CertificateValidator (Phase 2)
    if phase2_ca_cert_path.exists():
        try:
            cert_validator = CertificateValidator(
                ca_cert_path=str(phase2_ca_cert_path)
            )
            print(f"✓ Loaded Phase 2 CertificateValidator")
        except Exception as e:
            print(f"⚠ Failed to initialize Phase 2 CertificateValidator: {e}")
            cert_validator = None
    else:
        cert_validator = None

    # Initialize or load key tables (Phase 2 with full keys)
    # Check if Phase 2 key table file exists
    if key_tables_path.exists():
        # Try to detect if it's Phase 2 format
        with open(key_tables_path, 'r') as f:
            import json
            data = json.load(f)
            is_phase2 = 'derived_keys' in data or data.get('total_tables', 0) > 100

        if is_phase2:
            table_manager = Phase2KeyTableManager(storage_path=key_tables_path)
            table_manager.load_from_file_with_keys()
            print(f"✓ Loaded Phase 2 key tables: {len(table_manager.key_tables)} master keys")
            print(f"  {len(table_manager.derived_keys)} tables with derived keys")
        else:
            # Phase 1 format
            table_manager = KeyTableManager(
                total_tables=10,
                tables_per_device=3,
                storage_path=key_tables_path
            )
            table_manager.load_from_file()
            print(f"✓ Loaded Phase 1 key tables: {len(table_manager.key_tables)} tables")
    else:
        # Default to Phase 1 if no file exists
        table_manager = KeyTableManager(
            total_tables=10,
            tables_per_device=3,
            storage_path=key_tables_path
        )
        print(f"⚠ Key tables not found at {key_tables_path}")
        print("  Run setup script to generate key tables.")

    # Initialize device registry
    device_registry = DeviceRegistry(storage_path=registry_path)
    if registry_path.exists():
        device_registry.load_from_file()
        print(f"✓ Loaded {len(device_registry._registrations)} device registrations")
    else:
        print("✓ Initialized empty device registry")

    # Initialize submission logger (Phase 2)
    submission_logger = SubmissionLogger(storage_path=submissions_path)
    if submissions_path.exists():
        submission_logger.load_from_file()
        stats = submission_logger.get_statistics()
        print(f"✓ Loaded submission logs: {stats['total_submissions']} submissions")
    else:
        print("✓ Initialized empty submission logger")

    # Initialize abuse detector (Phase 2)
    if device_registry and submission_logger:
        abuse_detector = AbuseDetector(submission_logger, device_registry)
        print("✓ Abuse detector ready")

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


@app.get("/cache/stats", tags=["Monitoring"])
async def get_cache_statistics():
    """
    Get validation cache statistics.

    Returns cache performance metrics including hit rate and size.
    """
    return {
        "cache": validation_cache.get_statistics(),
        "timestamp": datetime.utcnow().isoformat()
    }


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
    status_code=status.HTTP_201_CREATED,
    tags=["Provisioning"]
)
async def provision_device(request: ProvisionDeviceRequest):
    """
    Provision a new device (supports both Phase 1 and Phase 2).

    Phase 1: Raspberry Pi with NUC hash
    Phase 2: iOS with device secret

    Auto-detects which phase based on request fields:
    - If device_secret present → Phase 2 (iOS)
    - If nuc_hash present → Phase 1 (Raspberry Pi)

    Args:
        request: Device provisioning request

    Returns:
        Complete provisioning data (format depends on phase)

    Raises:
        HTTPException: If provisioning fails or device already exists
    """
    # Detect Phase 2 request (has device_secret)
    if request.device_secret is not None:
        # Route to Phase 2 endpoint
        phase2_request = ProvisionDeviceRequestPhase2(
            device_serial=request.device_serial,
            device_family=request.device_family,
            device_secret=request.device_secret
        )
        return await provision_device_phase2(phase2_request)

    # Phase 1 logic below
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
            device_secret=response.device_secret,  # Phase 2
            key_table_indices=response.key_table_indices or response.table_assignments,  # Phase 2 global indices
            table_assignments=response.table_assignments,  # Backward compat
            device_certificate=response.device_certificate,
            device_public_key=response.device_public_key,
            device_family=response.device_family,
            provisioned_at=datetime.utcnow().isoformat(),
            nuc_hash=response.nuc_hash  # Backward compat
        )

        device_registry.register_device(registration)

        # Save registry to disk
        device_registry.save_to_file()

        # Save key table assignments to disk
        if hasattr(table_manager, 'save_to_file_with_keys'):
            # Phase 2: Save with derived keys
            table_manager.save_to_file_with_keys()
        else:
            # Phase 1: Save master keys only
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


@app.post(
    "/api/v1/devices/provision-phase2",
    response_model=ProvisionDeviceResponsePhase2,
    status_code=status.HTTP_201_CREATED,
    tags=["Provisioning"]
)
async def provision_device_phase2(request: ProvisionDeviceRequestPhase2):
    """
    Provision a Phase 2 device (iOS) with certificate-based authentication.

    This endpoint is used by iOS devices to provision with:
    - Device secret (frozen identity)
    - ECDSA P-256 certificate signed by SMA CA
    - Key tables (3 tables × 1000 keys each)
    - Key table indices (global mapping)

    Args:
        request: Phase 2 provisioning request with device_secret

    Returns:
        Complete provisioning data including certificate, keys, and key tables

    Raises:
        HTTPException: If provisioning fails or device already exists
    """
    # Check if Phase 2 components are initialized
    if not cert_generator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Phase 2 certificate generator not initialized (run generate_ca_certificate.py)"
        )

    if not isinstance(table_manager, Phase2KeyTableManager):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Phase 2 key table manager not initialized"
        )

    # Check if device already registered
    if device_registry and device_registry.device_exists(request.device_serial):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device {request.device_serial} already provisioned"
        )

    try:
        # Validate device_secret format (64 hex characters)
        if len(request.device_secret) != 64:
            raise ValueError(f"device_secret must be 64 hex characters, got {len(request.device_secret)}")

        # Validate hex format
        try:
            bytes.fromhex(request.device_secret)
        except ValueError:
            raise ValueError("device_secret must be valid hexadecimal")

        # Step 1: Assign 3 random key tables (global indices 0-2499)
        key_table_indices = table_manager.assign_random_tables(request.device_serial)
        print(f"[Phase 2] Assigned key tables: {key_table_indices} to {request.device_serial}")

        # Step 2: Generate device certificate with CertificateGenerator
        device_cert_pem, device_key_pem, cert_chain_pem = cert_generator.generate_device_certificate(
            device_serial=request.device_serial,
            device_secret=request.device_secret,
            key_table_indices=key_table_indices,
            device_family=request.device_family
        )
        print(f"[Phase 2] Generated certificate for {request.device_serial}")

        # Step 3: Get key tables (3 arrays of 1000 keys each)
        key_arrays = table_manager.get_multiple_table_keys(key_table_indices)

        # Convert keys to hex strings for JSON serialization
        key_tables = [
            [key.hex() for key in table_keys]
            for table_keys in key_arrays
        ]
        print(f"[Phase 2] Retrieved {len(key_tables)} key tables with {len(key_tables[0])} keys each")

        # Step 4: Register device
        if device_registry:
            registration = DeviceRegistration(
                device_serial=request.device_serial,
                device_secret=request.device_secret,
                key_table_indices=key_table_indices,
                table_assignments=key_table_indices,  # Backward compat
                device_certificate=device_cert_pem,
                device_public_key="",  # Not needed in Phase 2 (cert contains public key)
                device_family=request.device_family,
                provisioned_at=datetime.utcnow().isoformat(),
                nuc_hash=None  # Phase 2 doesn't use NUC
            )

            device_registry.register_device(registration)
            device_registry.save_to_file()
            print(f"[Phase 2] Registered device {request.device_serial}")

        # Step 5: Save key tables to disk
        if hasattr(table_manager, 'save_to_file_with_keys'):
            table_manager.save_to_file_with_keys()

        # Step 6: Return response
        return ProvisionDeviceResponsePhase2(
            device_certificate=device_cert_pem,
            device_private_key=device_key_pem,
            certificate_chain=cert_chain_pem,
            key_tables=key_tables,
            key_table_indices=key_table_indices,
            device_secret=request.device_secret  # Echo back for verification
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Phase 2 provisioning failed: {str(e)}"
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
    """Request model for token validation from blockchain aggregator (LEGACY - Phase 1 old format)."""
    ciphertext: str = Field(..., description="Hex-encoded encrypted NUC token")
    table_references: List[int] = Field(..., min_length=3, max_length=3, description="3 table IDs")
    key_indices: List[int] = Field(..., min_length=3, max_length=3, description="3 key indices")


class CameraTokenValidation(BaseModel):
    """Structured camera token for validation (NEW format)."""
    ciphertext: str = Field(..., description="Hex-encoded AES-GCM ciphertext")
    auth_tag: str = Field(..., min_length=32, max_length=32, description="AES-GCM auth tag (32 hex chars)")
    nonce: str = Field(..., min_length=24, max_length=24, description="AES-GCM nonce (24 hex chars)")
    table_id: int = Field(..., ge=0, lt=250, description="Key table ID (0-249)")
    key_index: int = Field(..., ge=0, lt=1000, description="Key index within table (0-999)")


class CameraTokenValidationRequest(BaseModel):
    """Request model for camera token validation (NEW format from aggregator)."""
    camera_token: CameraTokenValidation = Field(..., description="Structured camera token")
    manufacturer_authority_id: str = Field(..., description="Manufacturer ID (e.g., 'CANON_001')")


class ValidationResponse(BaseModel):
    """Response model for validation."""
    valid: bool
    message: Optional[str] = None


@app.post("/validate", response_model=ValidationResponse, tags=["Validation"])
async def validate_camera_token_new(request: CameraTokenValidationRequest):
    """
    Validate structured camera token from blockchain aggregator (NEW format).

    Phase 1: Simplified validation (format checking + table existence)
    Phase 2: Full cryptographic validation (decrypt + compare NUC hash)

    Args:
        request: Camera token validation request with structured token

    Returns:
        Validation response (PASS/FAIL)

    Note: This endpoint is called by the blockchain aggregator, NOT directly by cameras.
    The aggregator never sends the image hash - only the encrypted camera token.

    Privacy: Image hashes are NEVER sent to SMA, preserving camera anonymity.
    """
    if not table_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMA not initialized (key tables not loaded)"
        )

    try:
        token = request.camera_token

        # Check cache first (idempotency)
        cached_result = validation_cache.get_token_result(
            token.ciphertext,
            token.auth_tag,
            token.nonce,
            token.table_id,
            token.key_index
        )

        if cached_result:
            print(f"✓ Cache hit: returning cached result (count={cached_result.request_count})")
            return ValidationResponse(
                valid=cached_result.valid,
                message=cached_result.message
            )

        # Validate ciphertext is valid hex
        try:
            encrypted_bytes = bytes.fromhex(token.ciphertext)
        except ValueError:
            return ValidationResponse(
                valid=False,
                message="Invalid ciphertext format (must be hex)"
            )

        # Validate auth_tag is valid hex
        try:
            auth_tag_bytes = bytes.fromhex(token.auth_tag)
            if len(auth_tag_bytes) != 16:  # AES-GCM auth tag is 16 bytes
                return ValidationResponse(
                    valid=False,
                    message=f"Invalid auth_tag length: {len(auth_tag_bytes)} bytes (expected 16)"
                )
        except ValueError:
            return ValidationResponse(
                valid=False,
                message="Invalid auth_tag format (must be hex)"
            )

        # Validate nonce is valid hex
        try:
            nonce_bytes = bytes.fromhex(token.nonce)
            if len(nonce_bytes) != 12:  # AES-GCM nonce is 12 bytes
                return ValidationResponse(
                    valid=False,
                    message=f"Invalid nonce length: {len(nonce_bytes)} bytes (expected 12)"
                )
        except ValueError:
            return ValidationResponse(
                valid=False,
                message="Invalid nonce format (must be hex)"
            )

        # Check table_id is valid
        if token.table_id not in table_manager.key_tables:
            return ValidationResponse(
                valid=False,
                message=f"Invalid table_id: {token.table_id} (table not found)"
            )

        # Check key_index is in valid range (already validated by Pydantic, but double-check)
        if not (0 <= token.key_index < 1000):
            return ValidationResponse(
                valid=False,
                message=f"Invalid key_index: {token.key_index} (must be 0-999)"
            )

        # Phase 1: Cryptographic validation - decrypt and verify NUC hash
        if not device_registry:
            return ValidationResponse(
                valid=False,
                message="Device registry not initialized"
            )

        # Validate token using cryptographic validation
        valid, message, device = validate_camera_token(
            table_manager=table_manager,
            device_registry=device_registry,
            ciphertext=token.ciphertext,
            auth_tag=token.auth_tag,
            nonce=token.nonce,
            table_id=token.table_id,
            key_index=token.key_index
        )

        # Log validation result
        if valid and device:
            print(f"✓ Camera authenticated: device={device.device_serial}, "
                  f"manufacturer={request.manufacturer_authority_id}, "
                  f"table={token.table_id}, index={token.key_index}")
        else:
            print(f"✗ Validation failed: manufacturer={request.manufacturer_authority_id}, "
                  f"table={token.table_id}, reason={message}")

        # Cache the result for future requests (idempotency)
        validation_cache.put_token_result(
            token.ciphertext,
            token.auth_tag,
            token.nonce,
            token.table_id,
            token.key_index,
            valid,
            message,
            device.device_serial if device else None
        )

        return ValidationResponse(
            valid=valid,
            message=message
        )

    except Exception as e:
        # Log error but don't expose details to aggregator
        print(f"Validation error: {str(e)}")
        return ValidationResponse(
            valid=False,
            message="Validation failed"
        )


@app.post("/validate-legacy", response_model=ValidationResponse, tags=["Validation"])
async def validate_token_legacy(request: ValidationRequest):
    """
    Validate encrypted NUC token (LEGACY format - 3 table references).

    DEPRECATED: Use /validate with structured CameraTokenValidationRequest instead.

    Args:
        request: Validation request with encrypted token and 3 table references

    Returns:
        Validation response (PASS/FAIL)
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
        return ValidationResponse(
            valid=True,
            message="Legacy validation: format valid"
        )

    except Exception as e:
        # Log error but don't expose details to aggregator
        print(f"Validation error: {str(e)}")
        return ValidationResponse(
            valid=False,
            message="Validation failed"
        )


class CertificateValidationRequest(BaseModel):
    """Request model for certificate-based validation (Phase 2)."""
    camera_cert: str = Field(..., description="Base64-encoded PEM camera certificate")
    image_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 image hash")
    timestamp: int = Field(..., description="Unix timestamp when photo was taken")
    gps_hash: Optional[str] = Field(None, min_length=64, max_length=64, description="SHA-256 GPS hash (optional)")
    bundle_signature: str = Field(..., description="Base64-encoded ECDSA signature over bundle")


@app.post("/validate-cert", response_model=ValidationResponse, tags=["Validation"])
async def validate_certificate(request: CertificateValidationRequest):
    """
    Validate camera certificate bundle (Phase 2).

    This endpoint validates certificate bundles from iOS devices using ECDSA signatures.
    It verifies:
    1. Certificate chain (signed by CA)
    2. Certificate expiration
    3. Device not blacklisted
    4. Bundle signature (ECDSA P-256 over canonical data)

    Args:
        request: Certificate bundle validation request

    Returns:
        Validation response (PASS/FAIL)

    Privacy: The SMA validates camera authenticity without seeing the image content.
    The image_hash is only used for signature verification, not content inspection.
    """
    if not cert_validator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Certificate validator not initialized (Phase 2 CA missing)"
        )

    if not device_registry:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Device registry not initialized"
        )

    try:
        # Check cache first (idempotency)
        cached_result = validation_cache.get_cert_result(
            request.camera_cert,
            request.image_hash,
            request.timestamp,
            request.gps_hash,
            request.bundle_signature
        )

        if cached_result:
            print(f"✓ Cache hit: returning cached result (count={cached_result.request_count})")
            return ValidationResponse(
                valid=cached_result.valid,
                message=cached_result.message
            )

        print(f"Certificate bundle validation request:")
        print(f"  Image Hash: {request.image_hash[:16]}... (used for signature only)")
        print(f"  Timestamp: {request.timestamp}")
        print(f"  GPS Hash: {request.gps_hash[:16] if request.gps_hash else 'none'}...")

        # Validate certificate bundle
        is_valid, reason, device_secret = cert_validator.validate_certificate_bundle(
            camera_cert_b64=request.camera_cert,
            image_hash=request.image_hash,
            timestamp=request.timestamp,
            gps_hash=request.gps_hash,
            bundle_signature_b64=request.bundle_signature,
            device_registry=device_registry
        )

        # Log validation result
        if submission_logger and device_secret:
            # Look up device serial for logging
            device = device_registry.get_device_by_secret(device_secret)
            device_serial = device.device_serial if device else "unknown"

            submission_logger.log_submission(
                device_serial=device_serial,
                validation_result="pass" if is_valid else "fail"
            )

            # Periodically save submission logs
            if submission_logger.count_submissions_all(hours=1) % 100 == 0:
                submission_logger.save_to_file()
        elif submission_logger:
            # Failed early (no device_secret extracted)
            submission_logger.log_submission(
                device_serial="unknown",
                validation_result="fail"
            )

        # Print result
        if is_valid:
            print(f"  ✓ Certificate bundle validated: {reason}")
        else:
            print(f"  ✗ Certificate bundle validation failed: {reason}")

        # Cache the result for future requests (idempotency)
        device = device_registry.get_device_by_secret(device_secret) if device_secret else None
        validation_cache.put_cert_result(
            request.camera_cert,
            request.image_hash,
            request.timestamp,
            request.gps_hash,
            request.bundle_signature,
            is_valid,
            reason,
            device.device_serial if device else None
        )

        return ValidationResponse(
            valid=is_valid,
            message=reason
        )

    except Exception as e:
        print(f"Certificate validation error: {str(e)}")

        # Log failed validation
        if submission_logger:
            submission_logger.log_submission(
                device_serial="unknown",
                validation_result="fail"
            )

        return ValidationResponse(
            valid=False,
            message=f"Certificate validation failed: {str(e)}"
        )


# Phase 2: Abuse Detection and Admin Endpoints


@app.get("/api/admin/abuse/check", tags=["Admin"])
async def run_abuse_check():
    """
    Run abuse detection check on all devices (manual trigger for daily cron).

    Returns results for devices with warnings or blacklists.
    """
    if not abuse_detector or not submission_logger or not device_registry:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Abuse detection not initialized"
        )

    results = run_daily_abuse_check(
        submission_logger,
        device_registry,
        save_registries=True
    )

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "results": [
            {
                "device_serial": r.device_serial,
                "count_24h": r.submission_count_24h,
                "blacklisted": r.blacklisted,
                "warning": r.warning,
                "reason": r.reason
            }
            for r in results
        ],
        "total_checked": len(submission_logger.get_all_device_serials()),
        "actions_taken": len(results)
    }


@app.get("/api/admin/abuse/report", tags=["Admin"])
async def get_abuse_report():
    """
    Get comprehensive abuse detection report.
    """
    if not abuse_detector:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Abuse detection not initialized"
        )

    return abuse_detector.get_abuse_report()


@app.get("/api/devices/{device_serial}/status", tags=["Devices"])
async def get_device_status(device_serial: str):
    """
    Get device status including blacklist and submission count.

    Args:
        device_serial: Device serial number

    Returns:
        Device status information
    """
    if not device_registry or not submission_logger:
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

    # Count submissions
    count_24h = submission_logger.count_submissions(device_serial, hours=24)
    count_total = submission_logger.count_submissions(device_serial)

    return {
        "device_serial": device.device_serial,
        "device_family": device.device_family,
        "provisioned_at": device.provisioned_at,
        "is_blacklisted": device.is_blacklisted,
        "blacklisted_at": device.blacklisted_at,
        "blacklist_reason": device.blacklist_reason,
        "submissions_24h": count_24h,
        "submissions_total": count_total,
        "key_table_indices": device.key_table_indices
    }


@app.post("/api/admin/blacklist/{device_serial}", tags=["Admin"])
async def blacklist_device_manual(
    device_serial: str,
    reason: str = "Manual blacklist via API"
):
    """
    Manually blacklist a device.

    Args:
        device_serial: Device serial number
        reason: Reason for blacklisting
    """
    if not device_registry:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )

    success = device_registry.blacklist_device(device_serial, reason)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_serial} not found"
        )

    # Save registry
    device_registry.save_to_file()

    return {
        "device_serial": device_serial,
        "blacklisted": True,
        "reason": reason,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.delete("/api/admin/blacklist/{device_serial}", tags=["Admin"])
async def unblacklist_device_manual(device_serial: str):
    """
    Remove device from blacklist.

    Args:
        device_serial: Device serial number
    """
    if not device_registry:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )

    success = device_registry.unblacklist_device(device_serial)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_serial} not found"
        )

    # Save registry
    device_registry.save_to_file()

    return {
        "device_serial": device_serial,
        "blacklisted": False,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/admin/blacklist", tags=["Admin"])
async def list_blacklisted_devices():
    """
    List all blacklisted devices.
    """
    if not device_registry:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )

    all_devices = device_registry.list_devices()
    blacklisted = [d for d in all_devices if d.is_blacklisted]

    return {
        "total_blacklisted": len(blacklisted),
        "devices": [
            {
                "device_serial": d.device_serial,
                "device_family": d.device_family,
                "blacklisted_at": d.blacklisted_at,
                "blacklist_reason": d.blacklist_reason
            }
            for d in blacklisted
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
