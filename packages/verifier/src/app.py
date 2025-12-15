"""
Birthmark Image Verifier - Web Application

Simple web app for verifying images against the Birthmark blockchain.
"""

import logging
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .hash_image import hash_image_bytes, verify_hash_format

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Birthmark Image Verifier",
    description="Verify image authenticity against Birthmark blockchain",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
BLOCKCHAIN_NODE_URL = "http://localhost:8545"


class VerificationResult(BaseModel):
    """Verification result response."""
    image_hash: str
    verified: bool
    timestamp: Optional[int] = None
    block_height: Optional[int] = None
    tx_id: Optional[int] = None
    submission_server_id: Optional[str] = None
    modification_level: Optional[int] = None
    modification_display: Optional[str] = None
    parent_image_hash: Optional[str] = None
    message: str


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main verification page."""
    html_path = Path(__file__).parent.parent / "web" / "index.html"

    if not html_path.exists():
        return HTMLResponse(
            content="<h1>Birthmark Verifier</h1><p>Frontend not found. Please create web/index.html</p>",
            status_code=404
        )

    with open(html_path, 'r') as f:
        return HTMLResponse(content=f.read())


@app.post("/api/verify", response_model=VerificationResult)
async def verify_image(file: UploadFile = File(...)):
    """
    Verify an uploaded image against the blockchain.

    Steps:
    1. Hash the uploaded image
    2. Query blockchain for verification
    3. Return verification results with provenance chain
    """
    logger.info(f"📤 Received verification request for: {file.filename}")

    try:
        # Read image file
        image_bytes = await file.read()
        logger.info(f"   File size: {len(image_bytes)} bytes")

        # Hash the image
        image_hash = hash_image_bytes(image_bytes)
        logger.info(f"   Image hash: {image_hash[:32]}...")

        # Query blockchain
        async with httpx.AsyncClient(timeout=10.0) as client:
            blockchain_url = f"{BLOCKCHAIN_NODE_URL}/api/v1/blockchain/verify/{image_hash}"
            logger.info(f"   Querying: {blockchain_url}")

            response = await client.get(blockchain_url)

            if response.status_code != 200:
                logger.error(f"   Blockchain query failed: {response.status_code}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Blockchain node error: {response.status_code}"
                )

            verification_data = response.json()
            logger.info(f"   Blockchain response: {verification_data}")

        # Build response
        if verification_data['verified']:
            modification_level = verification_data.get('modification_level', 0)
            modification_display = {
                0: "Raw (Original Sensor Data)",
                1: "Validated (Camera ISP or Minor Software Edits)",
                2: "Modified (Significant Software Edits)"
            }.get(modification_level, f"Level {modification_level}")

            logger.info(f"   ✅ VERIFIED - {modification_display}")

            result = VerificationResult(
                image_hash=image_hash,
                verified=True,
                timestamp=verification_data.get('timestamp'),
                block_height=verification_data.get('block_height'),
                tx_id=verification_data.get('tx_id'),
                submission_server_id=verification_data.get('submission_server_id'),
                modification_level=modification_level,
                modification_display=modification_display,
                parent_image_hash=verification_data.get('parent_image_hash'),
                message=f"✅ Image verified on blockchain! {modification_display}"
            )
        else:
            logger.info(f"   ❌ NOT VERIFIED - Image not found on blockchain")

            result = VerificationResult(
                image_hash=image_hash,
                verified=False,
                message="❌ Image not found on Birthmark blockchain. This image has not been authenticated."
            )

        return result

    except httpx.ConnectError:
        logger.error(f"   ❌ Cannot connect to blockchain node at {BLOCKCHAIN_NODE_URL}")
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to blockchain node at {BLOCKCHAIN_NODE_URL}. Is the node running?"
        )
    except Exception as e:
        logger.error(f"   ❌ Verification error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Verification error: {str(e)}"
        )


@app.get("/api/verify-hash/{image_hash}", response_model=VerificationResult)
async def verify_hash(image_hash: str):
    """
    Verify a hash directly (without uploading image).

    Useful for verifying hashes you already have.
    """
    logger.info(f"🔍 Hash verification request: {image_hash[:32]}...")

    # Validate hash format
    if not verify_hash_format(image_hash):
        raise HTTPException(
            status_code=400,
            detail="Invalid hash format. Must be 64 character hex string."
        )

    try:
        # Query blockchain
        async with httpx.AsyncClient(timeout=10.0) as client:
            blockchain_url = f"{BLOCKCHAIN_NODE_URL}/api/v1/blockchain/verify/{image_hash}"
            response = await client.get(blockchain_url)

            if response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Blockchain node error: {response.status_code}"
                )

            verification_data = response.json()

        # Build response
        if verification_data['verified']:
            modification_level = verification_data.get('modification_level', 0)
            modification_display = {
                0: "Raw (Original Sensor Data)",
                1: "Validated (Camera ISP or Minor Software Edits)",
                2: "Modified (Significant Software Edits)"
            }.get(modification_level, f"Level {modification_level}")

            logger.info(f"   ✅ VERIFIED - {modification_display}")

            return VerificationResult(
                image_hash=image_hash,
                verified=True,
                timestamp=verification_data.get('timestamp'),
                block_height=verification_data.get('block_height'),
                tx_id=verification_data.get('tx_id'),
                submission_server_id=verification_data.get('submission_server_id'),
                modification_level=modification_level,
                modification_display=modification_display,
                parent_image_hash=verification_data.get('parent_image_hash'),
                message=f"✅ Hash verified on blockchain! {modification_display}"
            )
        else:
            logger.info(f"   ❌ NOT VERIFIED")

            return VerificationResult(
                image_hash=image_hash,
                verified=False,
                message="❌ Hash not found on Birthmark blockchain."
            )

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to blockchain node at {BLOCKCHAIN_NODE_URL}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Check if blockchain node is reachable
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{BLOCKCHAIN_NODE_URL}/api/v1/blockchain/status")
            blockchain_ok = response.status_code == 200

            if blockchain_ok:
                blockchain_status = response.json()
            else:
                blockchain_status = {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        blockchain_ok = False
        blockchain_status = {"error": str(e)}

    return {
        "status": "healthy" if blockchain_ok else "degraded",
        "verifier": "operational",
        "blockchain_node": blockchain_status if blockchain_ok else "unreachable",
        "blockchain_url": BLOCKCHAIN_NODE_URL
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
