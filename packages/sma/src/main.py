"""
FastAPI application for the SMA (Simulated Manufacturer Authority).

This application provides endpoints for:
- Validating camera authentication tokens
- Device provisioning (future)
- Health checks
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from shared.types import ValidationRequest, ValidationResponse

from .database import get_db, init_database
from .validation import validate_authentication_token, validate_batch

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Pydantic models for API
class ValidationRequestAPI(BaseModel):
    """API model for validation requests."""

    encrypted_token: str = Field(
        ..., description="Base64-encoded encrypted NUC token"
    )
    table_references: List[int] = Field(
        ..., description="List of 3 key table IDs (0-2499)"
    )
    key_indices: List[int] = Field(..., description="List of 3 key indices (0-999)")

    class Config:
        json_schema_extra = {
            "example": {
                "encrypted_token": "YmFzZTY0IGVuY29kZWQgZW5jcnlwdGVkIGRhdGE=",
                "table_references": [42, 1337, 2001],
                "key_indices": [7, 99, 512],
            }
        }


class ValidationResponseAPI(BaseModel):
    """API model for validation responses."""

    valid: bool = Field(..., description="True if camera is legitimate, False otherwise")

    class Config:
        json_schema_extra = {"example": {"valid": True}}


class BatchValidationRequestAPI(BaseModel):
    """API model for batch validation requests."""

    requests: List[ValidationRequestAPI]


class BatchValidationResponseAPI(BaseModel):
    """API model for batch validation responses."""

    responses: List[ValidationResponseAPI]


class HealthResponse(BaseModel):
    """API model for health check responses."""

    status: str
    database: str
    registered_devices: int


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    database_url = os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost/sma"
    )
    logger.info(f"Initializing database: {database_url}")
    init_database(database_url)
    logger.info("SMA started successfully")
    yield
    logger.info("SMA shutting down")


# Create FastAPI app
app = FastAPI(
    title="Birthmark SMA",
    description="Simulated Manufacturer Authority for validating camera authenticity",
    version="0.1.0",
    lifespan=lifespan,
)


@app.post("/api/v1/validate", response_model=ValidationResponseAPI)
async def validate_token(
    request: ValidationRequestAPI, db: Session = Depends(get_db)
) -> ValidationResponseAPI:
    """
    Validate a camera's encrypted NUC token.

    This endpoint receives an encrypted token and key references from the
    aggregation server, decrypts the token, and checks if the device is
    registered.

    **CRITICAL:** This endpoint never receives or processes image hashes.
    It only validates camera authenticity.

    Args:
        request: Validation request containing encrypted token and key references
        db: Database session (injected)

    Returns:
        ValidationResponse with valid=True if camera is legitimate

    Example:
        ```bash
        curl -X POST http://localhost:8001/api/v1/validate \\
          -H "Content-Type: application/json" \\
          -d '{
            "encrypted_token": "...",
            "table_references": [42, 1337, 2001],
            "key_indices": [7, 99, 512]
          }'
        ```
    """
    try:
        # Convert base64 token to bytes
        import base64

        encrypted_token_bytes = base64.b64decode(request.encrypted_token)

        # Create internal ValidationRequest
        validation_request = ValidationRequest(
            encrypted_token=encrypted_token_bytes,
            table_references=request.table_references,
            key_indices=request.key_indices,
        )

        # Validate
        result = validate_authentication_token(db, validation_request)

        return ValidationResponseAPI(valid=result.valid)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal error during validation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/v1/validate/batch", response_model=BatchValidationResponseAPI)
async def validate_tokens_batch(
    request: BatchValidationRequestAPI, db: Session = Depends(get_db)
) -> BatchValidationResponseAPI:
    """
    Validate multiple camera tokens in a single request.

    This is useful for the aggregation server to validate multiple
    submissions efficiently.

    Args:
        request: Batch validation request
        db: Database session (injected)

    Returns:
        Batch validation response with results for each token
    """
    try:
        import base64

        # Convert API requests to internal ValidationRequests
        validation_requests = [
            ValidationRequest(
                encrypted_token=base64.b64decode(req.encrypted_token),
                table_references=req.table_references,
                key_indices=req.key_indices,
            )
            for req in request.requests
        ]

        # Validate batch
        results = validate_batch(db, validation_requests)

        # Convert to API responses
        api_responses = [ValidationResponseAPI(valid=r.valid) for r in results]

        return BatchValidationResponseAPI(responses=api_responses)

    except ValueError as e:
        logger.error(f"Batch validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal error during batch validation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        Health status including database connection and device count
    """
    try:
        from .identity import get_device_count

        device_count = get_device_count(db)

        return HealthResponse(
            status="healthy", database="connected", registered_devices=device_count
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Birthmark SMA",
        "version": "0.1.0",
        "description": "Simulated Manufacturer Authority for camera validation",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
