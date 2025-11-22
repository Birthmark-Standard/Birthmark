# Phase 1 Deployment Guide
## Step-by-Step Instructions for Birthmark Standard Implementation

**Target Audience:** Developers implementing Phase 1
**Prerequisites:** Ubuntu/Debian Linux, Python 3.9+, PostgreSQL 13+, Git
**Estimated Time:** 2-4 weeks
**Last Updated:** November 2025

---

## Table of Contents

1. [Week 1-2: Make it Work](#week-1-2-make-it-work)
   - [Step 1: Generate SMA Key Tables](#step-1-generate-sma-key-tables)
   - [Step 2: Initialize Blockchain Database](#step-2-initialize-blockchain-database)
   - [Step 3: End-to-End Integration Test](#step-3-end-to-end-integration-test)
   - [Step 4: Implement Device Signature Verification](#step-4-implement-device-signature-verification)

2. [Week 3-4: Make it Secure & Fast](#week-3-4-make-it-secure--fast)
   - [Step 5: Add Rate Limiting](#step-5-add-rate-limiting)
   - [Step 6: Write Integration Test Suite](#step-6-write-integration-test-suite)
   - [Step 7: Run Performance Benchmarks](#step-7-run-performance-benchmarks)
   - [Step 8: Optimize Based on Results](#step-8-optimize-based-on-results)

3. [Month 2: Real-World Testing](#month-2-real-world-testing)
   - [Step 9: Deploy to Test Environment](#step-9-deploy-to-test-environment)
   - [Step 10: Photography Club Beta](#step-10-photography-club-beta)
   - [Step 11: Collect Feedback and Iterate](#step-11-collect-feedback-and-iterate)

4. [Troubleshooting](#troubleshooting)
5. [Success Criteria](#success-criteria)

---

## Week 1-2: Make it Work

### Step 1: Generate SMA Key Tables

**Goal:** Initialize the Simulated Manufacturer Authority with cryptographic key tables.

**Time Estimate:** 30 minutes

#### 1.1 Navigate to SMA Package

```bash
cd /home/user/Birthmark/packages/sma
```

#### 1.2 Install Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install SMA dependencies
pip install -r requirements.txt
```

Expected packages:
- cryptography
- fastapi
- uvicorn
- pydantic

#### 1.3 Run Setup Script

```bash
python scripts/setup_sma.py
```

**What this does:**
- Generates Root CA certificate
- Creates Intermediate CA certificate
- Generates 10 key tables (Phase 1 scale)
- Derives 1,000 keys per table using HKDF-SHA256
- Stores keys in `data/key_tables/`

**Expected Output:**
```
[INFO] Setting up SMA...
[INFO] Generating Root CA certificate...
[INFO] Root CA certificate saved to data/ca/root_ca.pem
[INFO] Generating Intermediate CA certificate...
[INFO] Intermediate CA certificate saved to data/ca/intermediate_ca.pem
[INFO] Generating key tables...
[INFO] Table 0: Generated 1000 keys
[INFO] Table 1: Generated 1000 keys
...
[INFO] Table 9: Generated 1000 keys
[INFO] Key tables saved to data/key_tables/
[INFO] SMA setup complete!
```

#### 1.4 Verify Key Tables

```bash
ls -lh data/key_tables/
```

Expected files:
- `table_0000.bin` through `table_0009.bin` (each ~32 KB)
- `master_keys.json` (table metadata)

#### 1.5 Start SMA Server

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

**Expected Output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
```

#### 1.6 Test SMA Health Check

In a new terminal:

```bash
curl http://localhost:8001/api/v1/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "registered_devices": 0,
  "key_tables": 10,
  "ca_initialized": true
}
```

**Troubleshooting:**
- If port 8001 is in use: `lsof -ti:8001 | xargs kill -9`
- If CA generation fails: Check write permissions on `data/ca/`
- If key derivation is slow: This is normal, ~10 seconds total

---

### Step 2: Initialize Blockchain Database

**Goal:** Set up PostgreSQL database and initialize the blockchain with a genesis block.

**Time Estimate:** 45 minutes

#### 2.1 Install PostgreSQL

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### 2.2 Create Database

```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL prompt:
CREATE DATABASE birthmark_blockchain;
CREATE USER birthmark WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE birthmark_blockchain TO birthmark;
\q
```

#### 2.3 Configure Blockchain Package

```bash
cd /home/user/Birthmark/packages/blockchain
```

Create `.env` file:

```bash
cp .env.example .env
nano .env
```

Edit `.env` with these values:

```ini
# Database
DATABASE_URL=postgresql://birthmark:your_secure_password@localhost:5432/birthmark_blockchain

# SMA Integration
SMA_BASE_URL=http://localhost:8001
SMA_API_KEY=test_api_key_phase1

# Blockchain Settings
NODE_ID=test-node-001
VALIDATOR_PRIVATE_KEY=generate_this_in_next_step
BATCH_SIZE=1
BATCH_TIMEOUT_SECONDS=300

# API Settings
API_HOST=0.0.0.0
API_PORT=8545
LOG_LEVEL=INFO
```

#### 2.4 Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install blockchain dependencies
pip install -e ".[dev]"
```

#### 2.5 Run Database Migrations

```bash
# Apply migrations to create tables
alembic upgrade head
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> xxxxx, create initial schema
```

#### 2.6 Verify Database Schema

```bash
sudo -u postgres psql -d birthmark_blockchain -c "\dt"
```

**Expected Tables:**
```
              List of relations
 Schema |        Name         | Type  |   Owner
--------+---------------------+-------+-----------
 public | alembic_version     | table | birthmark
 public | batches             | table | birthmark
 public | blocks              | table | birthmark
 public | image_batch_map     | table | birthmark
 public | pending_submissions | table | birthmark
 public | transactions        | table | birthmark
```

#### 2.7 Initialize Genesis Block

```bash
python scripts/init_genesis.py
```

**Expected Output:**
```
[INFO] Initializing genesis block...
[INFO] Creating genesis block at height 0
[INFO] Genesis block hash: 0000000000000000000000000000000000000000000000000000000000000000
[INFO] Genesis timestamp: 1732000000
[INFO] Genesis block created successfully!
[INFO] Block 0 stored in database
```

#### 2.8 Start Blockchain Node

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8545 --reload
```

**Expected Output:**
```
INFO:     Started server process [23456]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8545 (Press CTRL+C to quit)
```

#### 2.9 Test Blockchain Health Check

```bash
curl http://localhost:8545/api/v1/status
```

**Expected Response:**
```json
{
  "node_id": "test-node-001",
  "block_height": 0,
  "pending_submissions": 0,
  "sma_connection": "connected",
  "database_status": "healthy"
}
```

**Troubleshooting:**
- If migrations fail: Check DATABASE_URL connection string
- If port 8545 is in use: Change API_PORT in .env
- If SMA connection fails: Ensure SMA is running on port 8001
- If genesis block fails: Check database permissions

---

### Step 3: End-to-End Integration Test

**Goal:** Submit a test image through the complete pipeline and verify it on the blockchain.

**Time Estimate:** 1-2 hours (includes debugging)

#### 3.1 Ensure Services Are Running

Open 2 terminal windows:

**Terminal 1 - SMA:**
```bash
cd /home/user/Birthmark/packages/sma
source venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 2 - Blockchain:**
```bash
cd /home/user/Birthmark/packages/blockchain
source venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8545 --reload
```

#### 3.2 Provision Test Camera

**Terminal 3 - Camera:**
```bash
cd /home/user/Birthmark/packages/camera-pi
source venv/bin/activate  # Or create new venv

# Install dependencies
pip install -r requirements.txt

# Run provisioning
python scripts/provision_device.py
```

**Provisioning Flow:**
```
[INFO] Starting device provisioning...
[?] Enter device serial number: TEST-CAMERA-001
[?] Enter SMA URL [http://localhost:8001]:
[INFO] Connecting to SMA at http://localhost:8001
[INFO] Requesting device certificate...
[INFO] Certificate received and validated
[INFO] Saving device configuration to data/device_config.json
[INFO] Provisioning complete!
```

**What gets created:**
- `data/device_config.json` - Device configuration
- `data/device_cert.pem` - Device certificate
- `data/device_key.pem` - Private key
- Device registered in SMA device registry

#### 3.3 Verify Provisioning

Check SMA device registry:

```bash
curl http://localhost:8001/api/v1/devices/TEST-CAMERA-001
```

**Expected Response:**
```json
{
  "device_serial": "TEST-CAMERA-001",
  "table_assignments": [3, 7, 9],
  "device_family": "Raspberry Pi",
  "provisioned_at": "2024-11-18T10:30:00Z",
  "status": "active"
}
```

#### 3.4 Capture and Submit Test Image

```bash
# Capture in mock mode (no hardware needed)
python src/main.py --mock-camera
```

**Interactive Prompt:**
```
Birthmark Camera - Phase 1 Prototype
====================================

Device: TEST-CAMERA-001
Mock Mode: Enabled
Aggregator: http://localhost:8545

Commands:
  c - Capture photo
  t - Start timelapse
  s - Show status
  q - Quit

> c
```

**Capture Flow:**
```
[INFO] Capturing image...
[INFO] Mock camera: Generated test image (12MP)
[INFO] Computing SHA-256 hash...
[INFO] Image hash: a1b2c3d4e5f6...
[INFO] Generating authentication bundle...
[INFO] Encrypting NUC token...
[INFO] Signing with device certificate...
[INFO] Submitting to aggregator...
[INFO] Submission successful! Receipt ID: 12345678-1234-5678-1234-567812345678
[INFO] Image saved to data/images/20241118_103045.jpg
```

#### 3.5 Monitor Aggregator Processing

Watch blockchain logs (Terminal 2):

```
INFO:     127.0.0.1:54321 - "POST /api/v1/submit HTTP/1.1" 202 Accepted
[INFO] Received submission for hash a1b2c3d4e5f6...
[INFO] Validating with SMA...
[INFO] SMA validation: PASS
[INFO] Adding to batch queue...
[INFO] Batch ready (size: 1)
[INFO] Creating block at height 1
[INFO] Block mined: hash 00000abcdef...
[INFO] Batch committed to blockchain
```

#### 3.6 Verify Image on Blockchain

```bash
# Get the image hash from camera output
IMAGE_HASH="a1b2c3d4e5f6..."  # Replace with actual hash

curl http://localhost:8545/api/v1/verify/$IMAGE_HASH
```

**Expected Response:**
```json
{
  "verified": true,
  "timestamp": 1732000000,
  "block_height": 1,
  "batch_id": 1,
  "aggregator": "test-node-001"
}
```

#### 3.7 Success Criteria

- ✅ Camera provisions successfully
- ✅ Image captures and hashes in <5 seconds
- ✅ SMA validates authentication bundle
- ✅ Blockchain accepts submission (HTTP 202)
- ✅ Image hash appears on blockchain
- ✅ Verification query returns `verified: true`

**If any step fails, see [Troubleshooting](#troubleshooting) section.**

#### 3.8 Test Multiple Images

Submit 10 test images:

```bash
# In camera-pi directory
python scripts/test_batch_submission.py --count 10
```

**Expected Behavior:**
- All 10 images hash uniquely (different hashes)
- All submissions accepted by aggregator
- All validated by SMA
- All appear on blockchain within 5 minutes
- All verify successfully

---

### Step 4: Implement Device Signature Verification

**Goal:** Add cryptographic verification of device signatures to prevent spoofed submissions.

**Time Estimate:** 2-3 hours

#### 4.1 Current State Analysis

Currently, the blockchain **stores** device signatures but doesn't **verify** them. This is a security gap.

**Location:** `packages/blockchain/src/aggregator/submission_handler.py`

#### 4.2 Create Signature Verifier Module

Create new file:

```bash
cd /home/user/Birthmark/packages/blockchain
nano src/aggregator/signature_verifier.py
```

```python
"""
Device signature verification for authentication bundles.
"""
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SignatureVerifier:
    """Verifies device signatures using certificates."""

    def __init__(self, root_ca_cert_path: Optional[str] = None):
        """
        Initialize signature verifier.

        Args:
            root_ca_cert_path: Path to root CA certificate for chain validation
        """
        self.root_ca_cert = None
        if root_ca_cert_path:
            with open(root_ca_cert_path, 'rb') as f:
                self.root_ca_cert = x509.load_pem_x509_certificate(f.read())

    def verify_certificate_chain(self, device_cert: x509.Certificate) -> bool:
        """
        Verify certificate chain (simplified for Phase 1).

        In Phase 2, implement full chain validation with intermediate CA.

        Args:
            device_cert: Device X.509 certificate

        Returns:
            True if certificate is trusted
        """
        # Phase 1: Accept all certificates (SMA is trusted)
        # Phase 2: Validate issuer chain back to root CA

        # Check certificate hasn't expired
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        if now < device_cert.not_valid_before_utc:
            logger.error("Certificate not yet valid")
            return False

        if now > device_cert.not_valid_after_utc:
            logger.error("Certificate expired")
            return False

        # TODO Phase 2: Validate issuer signature
        # issuer = device_cert.issuer
        # Verify issuer is trusted intermediate CA

        return True

    def verify_bundle_signature(
        self,
        image_hash: str,
        timestamp: int,
        encrypted_token: bytes,
        signature: bytes,
        device_cert_pem: str
    ) -> bool:
        """
        Verify device signature over authentication bundle.

        Args:
            image_hash: SHA-256 hash of image
            timestamp: Unix timestamp
            encrypted_token: Encrypted NUC token
            signature: Device signature (DER format)
            device_cert_pem: Device certificate (PEM format)

        Returns:
            True if signature is valid
        """
        try:
            # Parse device certificate
            device_cert = x509.load_pem_x509_certificate(
                device_cert_pem.encode('utf-8')
            )

            # Verify certificate chain
            if not self.verify_certificate_chain(device_cert):
                logger.error("Certificate chain validation failed")
                return False

            # Extract public key from certificate
            public_key = device_cert.public_key()

            if not isinstance(public_key, ec.EllipticCurvePublicKey):
                logger.error("Certificate does not contain EC public key")
                return False

            # Reconstruct signed data (must match camera's signing logic)
            signed_data = self._construct_signed_data(
                image_hash, timestamp, encrypted_token
            )

            # Verify signature
            try:
                public_key.verify(
                    signature,
                    signed_data,
                    ec.ECDSA(hashes.SHA256())
                )
                logger.info("Device signature verified successfully")
                return True

            except InvalidSignature:
                logger.error("Invalid device signature")
                return False

        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False

    def _construct_signed_data(
        self,
        image_hash: str,
        timestamp: int,
        encrypted_token: bytes
    ) -> bytes:
        """
        Reconstruct the data that was signed by the device.

        CRITICAL: This must exactly match the camera's signing logic.

        Args:
            image_hash: SHA-256 hash
            timestamp: Unix timestamp
            encrypted_token: Encrypted NUC token

        Returns:
            Bytes to verify signature against
        """
        # Format: hash || timestamp || token (same as camera)
        signed_data = (
            image_hash.encode('utf-8') +
            str(timestamp).encode('utf-8') +
            encrypted_token
        )
        return signed_data


# Global instance
_verifier = None


def get_verifier() -> SignatureVerifier:
    """Get global signature verifier instance."""
    global _verifier
    if _verifier is None:
        # TODO: Load root CA path from config
        _verifier = SignatureVerifier()
    return _verifier
```

#### 4.3 Integrate into Submission Handler

Edit `src/aggregator/submission_handler.py`:

```python
# Add import at top
from .signature_verifier import get_verifier

# In handle_submission function, after parsing the bundle:

async def handle_submission(bundle: dict) -> dict:
    """Handle camera submission."""

    # ... existing parsing code ...

    # NEW: Verify device signature
    verifier = get_verifier()
    signature_valid = verifier.verify_bundle_signature(
        image_hash=bundle['image_hash'],
        timestamp=bundle['timestamp'],
        encrypted_token=bundle['encrypted_token'],
        signature=bundle['device_signature'],
        device_cert_pem=bundle.get('device_certificate', '')
    )

    if not signature_valid:
        logger.error(f"Invalid device signature for hash {bundle['image_hash']}")
        return {
            "status": "rejected",
            "reason": "invalid_signature",
            "receipt_id": None
        }

    # ... rest of validation flow ...
```

#### 4.4 Add Tests

Create `packages/blockchain/tests/test_signature_verification.py`:

```python
"""
Tests for device signature verification.
"""
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography import x509
from datetime import datetime, timedelta, timezone

from src.aggregator.signature_verifier import SignatureVerifier


def test_verify_valid_signature():
    """Test verification of valid device signature."""
    # Generate test keypair
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    # Create test data
    image_hash = "a" * 64
    timestamp = 1732000000
    encrypted_token = b"test_encrypted_token"

    # Sign data
    signed_data = (
        image_hash.encode('utf-8') +
        str(timestamp).encode('utf-8') +
        encrypted_token
    )
    signature = private_key.sign(signed_data, ec.ECDSA(hashes.SHA256()))

    # Create mock certificate
    from cryptography.x509.oid import NameOID
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "TEST-CAMERA-001"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)  # Self-signed for test
        .public_key(public_key)
        .serial_number(1)
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .sign(private_key, hashes.SHA256())
    )

    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')

    # Verify signature
    verifier = SignatureVerifier()
    assert verifier.verify_bundle_signature(
        image_hash, timestamp, encrypted_token, signature, cert_pem
    )


def test_reject_invalid_signature():
    """Test rejection of invalid signature."""
    # Similar setup but with wrong signature
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    image_hash = "a" * 64
    timestamp = 1732000000
    encrypted_token = b"test_token"

    # Sign different data
    wrong_data = b"wrong_data"
    signature = private_key.sign(wrong_data, ec.ECDSA(hashes.SHA256()))

    # Create cert (same as above)
    # ... certificate creation ...

    # Verify should fail
    verifier = SignatureVerifier()
    assert not verifier.verify_bundle_signature(
        image_hash, timestamp, encrypted_token, signature, cert_pem
    )


def test_reject_expired_certificate():
    """Test rejection of expired certificate."""
    # Create cert that expired yesterday
    private_key = ec.generate_private_key(ec.SECP256R1())

    cert = (
        x509.CertificateBuilder()
        # ... same setup ...
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=10))
        .not_valid_after(datetime.now(timezone.utc) - timedelta(days=1))
        .sign(private_key, hashes.SHA256())
    )

    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')

    verifier = SignatureVerifier()
    assert not verifier.verify_certificate_chain(cert)
```

Run tests:

```bash
pytest tests/test_signature_verification.py -v
```

#### 4.5 Update Camera to Include Certificate

Edit `packages/camera-pi/src/submission.py`:

```python
# Ensure device certificate is included in submission

def create_submission_bundle(auth_bundle: AuthenticationBundle) -> dict:
    """Create submission bundle with certificate."""

    # Load device certificate
    with open('data/device_cert.pem', 'r') as f:
        device_cert_pem = f.read()

    return {
        'image_hash': auth_bundle.image_hash,
        'encrypted_token': auth_bundle.encrypted_token,
        'table_references': auth_bundle.table_references,
        'key_indices': auth_bundle.key_indices,
        'timestamp': auth_bundle.timestamp,
        'device_signature': auth_bundle.signature,
        'device_certificate': device_cert_pem  # Include certificate
    }
```

#### 4.6 Test Signature Verification End-to-End

Re-run integration test from Step 3:

```bash
# Start services
# SMA on 8001, Blockchain on 8545

# Capture test image
cd packages/camera-pi
python src/main.py --mock-camera
> c
```

**Check blockchain logs for:**
```
[INFO] Verifying device signature...
[INFO] Device signature verified successfully
[INFO] SMA validation: PASS
```

**Test rejection of invalid signature:**

Manually submit with corrupted signature:

```bash
curl -X POST http://localhost:8545/api/v1/submit \
  -H "Content-Type: application/json" \
  -d '{
    "image_hash": "aaaa...",
    "encrypted_token": "dGVzdA==",
    "table_references": [0,1,2],
    "key_indices": [0,1,2],
    "timestamp": 1732000000,
    "device_signature": "aW52YWxpZA==",
    "device_certificate": "-----BEGIN CERTIFICATE-----..."
  }'
```

**Expected Response:**
```json
{
  "status": "rejected",
  "reason": "invalid_signature",
  "receipt_id": null
}
```

---

## Week 3-4: Make it Secure & Fast

### Step 5: Add Rate Limiting

**Goal:** Prevent DoS attacks by limiting submission rates.

**Time Estimate:** 2-3 hours

#### 5.1 Install Rate Limiting Library

```bash
cd /home/user/Birthmark/packages/blockchain
pip install slowapi
```

#### 5.2 Create Rate Limiter Configuration

Edit `src/config.py`:

```python
# Add rate limiting settings

class Settings(BaseSettings):
    # ... existing settings ...

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_SUBMISSIONS: str = "10/minute"  # Per IP
    RATE_LIMIT_VERIFICATION: str = "60/minute"
    RATE_LIMIT_STATUS: str = "30/minute"

    class Config:
        env_file = ".env"
```

#### 5.3 Add Rate Limiter to Application

Edit `src/main.py`:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Birthmark Blockchain Node")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply to endpoints
@app.post("/api/v1/submit")
@limiter.limit(settings.RATE_LIMIT_SUBMISSIONS)
async def submit_image(request: Request, bundle: dict):
    # ... existing code ...
    pass

@app.get("/api/v1/verify/{image_hash}")
@limiter.limit(settings.RATE_LIMIT_VERIFICATION)
async def verify_image(request: Request, image_hash: str):
    # ... existing code ...
    pass
```

#### 5.4 Test Rate Limiting

```bash
# Rapid fire submissions (should be rate limited after 10)
for i in {1..20}; do
  curl -X POST http://localhost:8545/api/v1/submit \
    -H "Content-Type: application/json" \
    -d '{"image_hash": "test'$i'", ...}'
  sleep 0.1
done
```

**Expected Behavior:**
- First 10 requests: HTTP 202 Accepted
- Requests 11-20: HTTP 429 Too Many Requests

```json
{
  "error": "Rate limit exceeded",
  "retry_after": 45
}
```

#### 5.5 Add IP Whitelisting for Trusted Cameras

For production deployments, whitelist known camera IP ranges:

```python
# In src/main.py

TRUSTED_IP_RANGES = [
    "10.0.0.0/8",      # Internal network
    "192.168.1.0/24",  # Photography club network
]

def is_trusted_ip(ip: str) -> bool:
    """Check if IP is in trusted ranges."""
    from ipaddress import ip_address, ip_network
    ip_obj = ip_address(ip)
    return any(ip_obj in ip_network(range) for range in TRUSTED_IP_RANGES)

@app.post("/api/v1/submit")
async def submit_image(request: Request, bundle: dict):
    client_ip = get_remote_address(request)

    # Skip rate limiting for trusted IPs
    if not is_trusted_ip(client_ip):
        await limiter.check(request)

    # ... rest of handler ...
```

---

### Step 6: Write Integration Test Suite

**Goal:** Automated end-to-end testing of the complete system.

**Time Estimate:** 4-6 hours

#### 6.1 Create Integration Test Directory

```bash
mkdir -p /home/user/Birthmark/tests/integration
cd /home/user/Birthmark/tests/integration
```

#### 6.2 Write End-to-End Test

Create `test_e2e_submission.py`:

```python
"""
End-to-end integration test for image submission pipeline.
"""
import pytest
import requests
import time
import hashlib
from pathlib import Path


class TestEndToEndSubmission:
    """Test complete submission flow: camera → aggregator → blockchain."""

    @pytest.fixture(scope="class")
    def services_running(self):
        """Verify all services are running."""
        # Check SMA
        sma_health = requests.get("http://localhost:8001/api/v1/health")
        assert sma_health.status_code == 200

        # Check Blockchain
        blockchain_status = requests.get("http://localhost:8545/api/v1/status")
        assert blockchain_status.status_code == 200

        yield

    @pytest.fixture
    def test_device_serial(self):
        """Return test device serial."""
        return "TEST-CAMERA-E2E-001"

    @pytest.fixture
    def provisioned_device(self, test_device_serial):
        """Provision a test device."""
        # Provision via SMA API
        response = requests.post(
            "http://localhost:8001/api/v1/provision",
            json={"device_serial": test_device_serial}
        )
        assert response.status_code == 200

        device_data = response.json()
        return device_data

    def test_complete_submission_flow(self, services_running, provisioned_device):
        """Test full submission from camera to blockchain verification."""

        # 1. Generate test image hash
        test_image_data = b"test_image_data_" + str(time.time()).encode()
        image_hash = hashlib.sha256(test_image_data).hexdigest()

        # 2. Create authentication bundle (simplified)
        bundle = {
            "image_hash": image_hash,
            "encrypted_token": "dGVzdF90b2tlbg==",  # base64 "test_token"
            "table_references": provisioned_device['table_assignments'],
            "key_indices": [0, 1, 2],
            "timestamp": int(time.time()),
            "device_signature": provisioned_device['signature'],
            "device_certificate": provisioned_device['certificate']
        }

        # 3. Submit to aggregator
        submit_response = requests.post(
            "http://localhost:8545/api/v1/submit",
            json=bundle
        )
        assert submit_response.status_code == 202
        receipt_id = submit_response.json()['receipt_id']
        assert receipt_id is not None

        # 4. Wait for batch processing (max 30 seconds)
        max_wait = 30
        start_time = time.time()
        verified = False

        while time.time() - start_time < max_wait:
            verify_response = requests.get(
                f"http://localhost:8545/api/v1/verify/{image_hash}"
            )

            if verify_response.status_code == 200:
                data = verify_response.json()
                if data.get('verified'):
                    verified = True
                    break

            time.sleep(1)

        # 5. Verify image on blockchain
        assert verified, f"Image not verified within {max_wait} seconds"

        verify_data = verify_response.json()
        assert verify_data['verified'] is True
        assert verify_data['block_height'] > 0
        assert verify_data['timestamp'] == bundle['timestamp']

    def test_batch_submission(self, services_running, provisioned_device):
        """Test submitting multiple images in batch."""

        image_hashes = []

        # Submit 10 images
        for i in range(10):
            test_data = f"test_image_{i}_{time.time()}".encode()
            image_hash = hashlib.sha256(test_data).hexdigest()
            image_hashes.append(image_hash)

            bundle = {
                "image_hash": image_hash,
                "encrypted_token": "dGVzdF90b2tlbg==",
                "table_references": provisioned_device['table_assignments'],
                "key_indices": [i % 1000, (i+1) % 1000, (i+2) % 1000],
                "timestamp": int(time.time()),
                "device_signature": provisioned_device['signature'],
                "device_certificate": provisioned_device['certificate']
            }

            response = requests.post(
                "http://localhost:8545/api/v1/submit",
                json=bundle
            )
            assert response.status_code == 202

        # Wait for batch processing
        time.sleep(10)

        # Verify all images
        for image_hash in image_hashes:
            response = requests.get(
                f"http://localhost:8545/api/v1/verify/{image_hash}"
            )
            assert response.status_code == 200
            assert response.json()['verified'] is True

    def test_invalid_signature_rejection(self, services_running):
        """Test that invalid signatures are rejected."""

        bundle = {
            "image_hash": "a" * 64,
            "encrypted_token": "aW52YWxpZA==",
            "table_references": [0, 1, 2],
            "key_indices": [0, 1, 2],
            "timestamp": int(time.time()),
            "device_signature": "aW52YWxpZF9zaWduYXR1cmU=",  # Invalid
            "device_certificate": "invalid_cert"
        }

        response = requests.post(
            "http://localhost:8545/api/v1/submit",
            json=bundle
        )

        # Should be rejected
        assert response.status_code == 400 or response.json()['status'] == 'rejected'

    def test_duplicate_submission(self, services_running, provisioned_device):
        """Test that duplicate hashes are handled correctly."""

        # Submit same hash twice
        image_hash = "duplicate_test_" + hashlib.sha256(b"test").hexdigest()

        bundle = {
            "image_hash": image_hash,
            "encrypted_token": "dGVzdA==",
            "table_references": provisioned_device['table_assignments'],
            "key_indices": [0, 1, 2],
            "timestamp": int(time.time()),
            "device_signature": provisioned_device['signature'],
            "device_certificate": provisioned_device['certificate']
        }

        # First submission
        response1 = requests.post(
            "http://localhost:8545/api/v1/submit",
            json=bundle
        )
        assert response1.status_code == 202

        # Second submission (duplicate)
        response2 = requests.post(
            "http://localhost:8545/api/v1/submit",
            json=bundle
        )

        # Should be accepted (idempotent) or rejected with specific error
        assert response2.status_code in [202, 409]


class TestSMAIntegration:
    """Test SMA validation integration."""

    def test_sma_validation_pass(self):
        """Test that valid tokens pass SMA validation."""
        # TODO: Implement with real NUC token encryption
        pass

    def test_sma_validation_fail(self):
        """Test that invalid tokens fail SMA validation."""
        # TODO: Implement
        pass


class TestBlockchainVerification:
    """Test blockchain verification queries."""

    def test_verify_nonexistent_hash(self):
        """Test querying for hash that doesn't exist."""
        fake_hash = "f" * 64

        response = requests.get(
            f"http://localhost:8545/api/v1/verify/{fake_hash}"
        )

        assert response.status_code == 404
        assert response.json()['verified'] is False

    def test_verify_invalid_hash_format(self):
        """Test querying with invalid hash format."""
        invalid_hash = "not_a_hash"

        response = requests.get(
            f"http://localhost:8545/api/v1/verify/{invalid_hash}"
        )

        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
```

#### 6.3 Run Integration Tests

```bash
# Ensure services are running first
# Then run tests

pytest test_e2e_submission.py -v -s
```

**Expected Output:**
```
test_e2e_submission.py::TestEndToEndSubmission::test_complete_submission_flow PASSED
test_e2e_submission.py::TestEndToEndSubmission::test_batch_submission PASSED
test_e2e_submission.py::TestEndToEndSubmission::test_invalid_signature_rejection PASSED
test_e2e_submission.py::TestEndToEndSubmission::test_duplicate_submission PASSED
test_e2e_submission.py::TestBlockchainVerification::test_verify_nonexistent_hash PASSED
test_e2e_submission.py::TestBlockchainVerification::test_verify_invalid_hash_format PASSED

====== 6 passed in 45.23s ======
```

---

### Step 7: Run Performance Benchmarks

**Goal:** Measure system performance against Phase 1 targets.

**Time Estimate:** 3-4 hours

#### 7.1 Create Benchmark Script

Create `tests/benchmarks/benchmark_performance.py`:

```python
"""
Performance benchmarks for Birthmark Phase 1.

Targets:
- Hash computation: <500ms on Raspberry Pi
- API response time: <100ms for verification
- Batch processing: <5s for 1000 images
- Direct hash query: <10ms
"""
import time
import hashlib
import requests
import statistics
from typing import List


class PerformanceBenchmark:
    """Performance testing suite."""

    def __init__(self, aggregator_url="http://localhost:8545"):
        self.aggregator_url = aggregator_url
        self.results = {}

    def benchmark_hash_computation(self, iterations=100):
        """Benchmark SHA-256 hash computation."""
        print(f"\n[Benchmark] Hash Computation ({iterations} iterations)")

        times = []

        for i in range(iterations):
            # Simulate 12MP image (~24MB raw Bayer)
            test_data = b"x" * (24 * 1024 * 1024)

            start = time.time()
            image_hash = hashlib.sha256(test_data).hexdigest()
            elapsed = (time.time() - start) * 1000  # Convert to ms

            times.append(elapsed)

        avg_time = statistics.mean(times)
        p95_time = sorted(times)[int(len(times) * 0.95)]

        print(f"  Average: {avg_time:.2f}ms")
        print(f"  P95: {p95_time:.2f}ms")
        print(f"  Target: <500ms")
        print(f"  Status: {'✅ PASS' if p95_time < 500 else '❌ FAIL'}")

        self.results['hash_computation'] = {
            'avg_ms': avg_time,
            'p95_ms': p95_time,
            'target_ms': 500,
            'pass': p95_time < 500
        }

    def benchmark_verification_query(self, iterations=100):
        """Benchmark verification API response time."""
        print(f"\n[Benchmark] Verification Query ({iterations} iterations)")

        # Submit a test hash first
        test_hash = hashlib.sha256(b"benchmark_test").hexdigest()

        times = []

        for i in range(iterations):
            start = time.time()
            response = requests.get(
                f"{self.aggregator_url}/api/v1/verify/{test_hash}"
            )
            elapsed = (time.time() - start) * 1000

            times.append(elapsed)

        avg_time = statistics.mean(times)
        p95_time = sorted(times)[int(len(times) * 0.95)]

        print(f"  Average: {avg_time:.2f}ms")
        print(f"  P95: {p95_time:.2f}ms")
        print(f"  Target: <100ms")
        print(f"  Status: {'✅ PASS' if p95_time < 100 else '❌ FAIL'}")

        self.results['verification_query'] = {
            'avg_ms': avg_time,
            'p95_ms': p95_time,
            'target_ms': 100,
            'pass': p95_time < 100
        }

    def benchmark_batch_processing(self, batch_size=100):
        """Benchmark batch processing time."""
        print(f"\n[Benchmark] Batch Processing ({batch_size} images)")

        # TODO: Submit batch and measure time to blockchain confirmation
        # This requires modifying batch timeout for testing

        print("  Status: ⏸️  MANUAL TEST REQUIRED")
        print("  Instructions:")
        print("    1. Set BATCH_SIZE=100 in .env")
        print("    2. Submit 100 test images")
        print("    3. Measure time from first submission to last confirmation")
        print("    4. Target: <5 seconds")

    def benchmark_submission_throughput(self, duration_seconds=60):
        """Benchmark submission throughput."""
        print(f"\n[Benchmark] Submission Throughput ({duration_seconds}s test)")

        start_time = time.time()
        submission_count = 0

        while time.time() - start_time < duration_seconds:
            test_hash = hashlib.sha256(
                f"throughput_test_{submission_count}_{time.time()}".encode()
            ).hexdigest()

            # Simplified submission (no real auth)
            try:
                response = requests.post(
                    f"{self.aggregator_url}/api/v1/submit",
                    json={
                        "image_hash": test_hash,
                        "encrypted_token": "dGVzdA==",
                        "table_references": [0, 1, 2],
                        "key_indices": [0, 1, 2],
                        "timestamp": int(time.time()),
                        "device_signature": "c2lnbmF0dXJl",
                        "device_certificate": "Y2VydA=="
                    },
                    timeout=5
                )

                if response.status_code == 202:
                    submission_count += 1

            except Exception as e:
                print(f"  Submission failed: {e}")
                break

        elapsed = time.time() - start_time
        throughput = submission_count / elapsed

        print(f"  Total submissions: {submission_count}")
        print(f"  Elapsed time: {elapsed:.2f}s")
        print(f"  Throughput: {throughput:.2f} submissions/second")

        self.results['submission_throughput'] = {
            'submissions_per_second': throughput,
            'total_submissions': submission_count
        }

    def generate_report(self):
        """Generate benchmark report."""
        print("\n" + "="*60)
        print("PERFORMANCE BENCHMARK REPORT")
        print("="*60)

        for test_name, results in self.results.items():
            print(f"\n{test_name.upper().replace('_', ' ')}:")
            for key, value in results.items():
                print(f"  {key}: {value}")

        # Overall pass/fail
        all_passed = all(
            r.get('pass', True) for r in self.results.values()
        )

        print("\n" + "="*60)
        print(f"OVERALL: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
        print("="*60 + "\n")


def main():
    """Run all benchmarks."""
    benchmark = PerformanceBenchmark()

    benchmark.benchmark_hash_computation(iterations=100)
    benchmark.benchmark_verification_query(iterations=100)
    benchmark.benchmark_batch_processing(batch_size=100)
    benchmark.benchmark_submission_throughput(duration_seconds=30)

    benchmark.generate_report()


if __name__ == "__main__":
    main()
```

#### 7.2 Run Benchmarks

```bash
cd /home/user/Birthmark/tests/benchmarks
python benchmark_performance.py
```

**Expected Output:**
```
[Benchmark] Hash Computation (100 iterations)
  Average: 245.32ms
  P95: 312.45ms
  Target: <500ms
  Status: ✅ PASS

[Benchmark] Verification Query (100 iterations)
  Average: 23.45ms
  P95: 45.67ms
  Target: <100ms
  Status: ✅ PASS

[Benchmark] Batch Processing (100 images)
  Status: ⏸️  MANUAL TEST REQUIRED

[Benchmark] Submission Throughput (30s test)
  Total submissions: 287
  Elapsed time: 30.02s
  Throughput: 9.56 submissions/second

====================================================
OVERALL: ✅ ALL TESTS PASSED
====================================================
```

#### 7.3 Raspberry Pi Hardware Benchmark

On actual Raspberry Pi hardware:

```bash
# SSH into Raspberry Pi
ssh pi@raspberrypi.local

cd /home/pi/Birthmark/packages/camera-pi

# Run hardware-specific benchmark
python tests/benchmark_pi_hardware.py
```

**Target Metrics:**
- Raw Bayer capture: <200ms
- SHA-256 hash (TPM): <500ms
- Total capture + hash: <650ms
- CPU overhead: <5%

---

### Step 8: Optimize Based on Results

**Goal:** Address any performance bottlenecks discovered in benchmarks.

**Time Estimate:** Variable (2-8 hours)

#### 8.1 Database Query Optimization

If verification queries are slow (>100ms):

```sql
-- Add index on image_hash
CREATE INDEX idx_image_hash ON image_batch_map(image_hash);

-- Add index on block_height
CREATE INDEX idx_block_height ON blocks(height);

-- Add composite index for batch lookups
CREATE INDEX idx_batch_block ON batches(id, block_height);
```

Apply via migration:

```bash
cd packages/blockchain
alembic revision -m "add_performance_indexes"
```

Edit migration file:

```python
def upgrade():
    op.create_index('idx_image_hash', 'image_batch_map', ['image_hash'])
    op.create_index('idx_block_height', 'blocks', ['height'])
    op.create_index('idx_batch_block', 'batches', ['id', 'block_height'])

def downgrade():
    op.drop_index('idx_image_hash')
    op.drop_index('idx_block_height')
    op.drop_index('idx_batch_block')
```

Apply:

```bash
alembic upgrade head
```

#### 8.2 API Response Caching

If verification queries are frequent, add caching:

```python
from functools import lru_cache
import time

# In-memory cache with TTL
CACHE = {}
CACHE_TTL = 60  # seconds

def get_cached_verification(image_hash: str):
    """Get cached verification result."""
    if image_hash in CACHE:
        result, timestamp = CACHE[image_hash]
        if time.time() - timestamp < CACHE_TTL:
            return result
    return None

def set_cached_verification(image_hash: str, result: dict):
    """Cache verification result."""
    CACHE[image_hash] = (result, time.time())

# In verification endpoint:
@app.get("/api/v1/verify/{image_hash}")
async def verify_image(image_hash: str):
    # Check cache first
    cached = get_cached_verification(image_hash)
    if cached:
        return cached

    # Query database
    result = await query_blockchain(image_hash)

    # Cache result if verified
    if result['verified']:
        set_cached_verification(image_hash, result)

    return result
```

#### 8.3 Batch Processing Optimization

If batch processing is slow:

**Parallel SMA validation:**

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def validate_batch_parallel(submissions: List[dict]):
    """Validate multiple submissions in parallel."""

    with ThreadPoolExecutor(max_workers=10) as executor:
        loop = asyncio.get_event_loop()

        tasks = [
            loop.run_in_executor(
                executor,
                validate_with_sma,
                submission
            )
            for submission in submissions
        ]

        results = await asyncio.gather(*tasks)

    return results
```

#### 8.4 Connection Pooling

Optimize database connections:

```python
# In database.py

from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,        # Increase pool size
    max_overflow=30,     # Allow overflow connections
    pool_pre_ping=True   # Verify connections
)
```

#### 8.5 Re-run Benchmarks

After optimizations:

```bash
python tests/benchmarks/benchmark_performance.py
```

Compare results to baseline.

---

## Month 2: Real-World Testing

### Step 9: Deploy to Test Environment

**Goal:** Deploy to production-like environment for beta testing.

**Time Estimate:** 1-2 days

#### 9.1 Choose Deployment Platform

**Options:**
- **Cloud VM:** AWS EC2, Google Cloud, DigitalOcean
- **On-premise:** University server, photography club server
- **Hybrid:** Blockchain on cloud, aggregator on-premise

**Recommended for Phase 1:**
- DigitalOcean Droplet ($12/month)
  - 2 vCPU, 4GB RAM
  - 80GB SSD
  - Ubuntu 22.04 LTS

#### 9.2 Provision Server

```bash
# SSH into server
ssh root@your-server-ip

# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3.10 python3-pip python3-venv postgresql nginx certbot

# Create birthmark user
adduser birthmark
usermod -aG sudo birthmark
su - birthmark
```

#### 9.3 Clone Repository

```bash
cd /home/birthmark
git clone https://github.com/Birthmark-Standard/Birthmark.git
cd Birthmark
```

#### 9.4 Deploy Using Docker Compose

```bash
cd packages/blockchain

# Copy and configure environment
cp .env.example .env
nano .env  # Edit with production values

# Build and start services
docker-compose up -d

# Check logs
docker-compose logs -f
```

#### 9.5 Configure Nginx Reverse Proxy

```bash
sudo nano /etc/nginx/sites-available/birthmark
```

```nginx
server {
    listen 80;
    server_name blockchain.birthmark.org;

    location /api/ {
        proxy_pass http://localhost:8545;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # Rate limiting
        limit_req zone=api burst=20 nodelay;
    }
}

# Rate limit zone
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/m;
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/birthmark /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 9.6 Configure SSL with Let's Encrypt

```bash
sudo certbot --nginx -d blockchain.birthmark.org
```

#### 9.7 Set Up Monitoring

**Install Prometheus + Grafana:**

```bash
# Add monitoring to docker-compose.yml
# See packages/blockchain/docker-compose.monitoring.yml
```

**Health Check Endpoint:**

```bash
# Monitor uptime
curl https://blockchain.birthmark.org/api/v1/status

# Expected: 99%+ uptime
```

#### 9.8 Configure Backups

```bash
# PostgreSQL backup script
cat > /home/birthmark/backup_db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/birthmark/backups"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump birthmark_blockchain > "$BACKUP_DIR/backup_$DATE.sql"
# Keep last 7 days
find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete
EOF

chmod +x /home/birthmark/backup_db.sh

# Add to crontab (daily at 2am)
crontab -e
```

```cron
0 2 * * * /home/birthmark/backup_db.sh
```

---

### Step 10: Photography Club Beta

**Goal:** Onboard 50-100 photographers to test the system with real usage.

**Time Estimate:** 2-4 weeks

#### 10.1 Prepare Test Cameras

**Option A: Raspberry Pi Kits**
- Assemble 10-15 Raspberry Pi cameras
- Pre-provision each device
- Create quick start guide
- Ship to beta testers

**Option B: Android App (If Phase 2 ready)**
- Deploy to Google Play Internal Testing
- Send invitations to beta testers
- Provide onboarding documentation

#### 10.2 Create Beta Tester Documentation

Create `docs/BETA_TESTER_GUIDE.md`:

```markdown
# Birthmark Beta Tester Guide

Welcome to the Birthmark Standard beta test!

## Setup Instructions

### Raspberry Pi Camera

1. Power on your Birthmark camera
2. Connect to WiFi (see WiFi setup card)
3. Camera will auto-provision on first boot
4. Green LED indicates ready to shoot

### Taking Photos

1. Press the **capture button**
2. Wait for **green blink** (photo authenticated)
3. Photos automatically uploaded to blockchain
4. View your authenticated photos at: https://verify.birthmark.org

### Verifying Photos

1. Go to https://verify.birthmark.org
2. Upload any photo
3. See authentication status instantly

## Feedback

Please report:
- Any failed photo captures
- Slow processing times (>10 seconds)
- Confusing user experience
- Feature requests

Submit feedback: https://forms.birthmark.org/beta-feedback

## Support

- Email: beta@birthmark.org
- Discord: #beta-testers
- Phone: (555) 123-4567 (9am-5pm PST)
```

#### 10.3 Onboarding Checklist

For each beta tester:

- [ ] Ship camera or send TestFlight invitation
- [ ] Provision device in SMA
- [ ] Verify device can submit to blockchain
- [ ] Send welcome email with guide
- [ ] Add to beta tester Discord/Slack
- [ ] Schedule check-in call after 1 week

#### 10.4 Define Success Metrics

**Quantitative:**
- [ ] 500+ images submitted
- [ ] 95%+ success rate (images verified on blockchain)
- [ ] <10 second average processing time
- [ ] 99%+ uptime
- [ ] <1% false negative rate

**Qualitative:**
- [ ] 80%+ user satisfaction (post-test survey)
- [ ] Ease of use rating >7/10
- [ ] Would recommend to others >70%

#### 10.5 Set Up Analytics Dashboard

Track key metrics:

```sql
-- Daily submission counts
SELECT
    DATE(received_at) as date,
    COUNT(*) as submissions,
    COUNT(CASE WHEN sma_validated THEN 1 END) as validated
FROM pending_submissions
GROUP BY DATE(received_at)
ORDER BY date DESC;

-- Success rate by device
SELECT
    device_serial,
    COUNT(*) as total_submissions,
    SUM(CASE WHEN verified THEN 1 END) as verified,
    ROUND(100.0 * SUM(CASE WHEN verified THEN 1 END) / COUNT(*), 2) as success_rate
FROM submissions
GROUP BY device_serial
ORDER BY success_rate DESC;

-- Average processing time
SELECT
    AVG(EXTRACT(EPOCH FROM (verified_at - received_at))) as avg_seconds
FROM submissions
WHERE verified_at IS NOT NULL;
```

Create Grafana dashboard to visualize.

#### 10.6 Beta Testing Timeline

**Week 1-2: Soft Launch**
- Onboard 10 early testers (photography club leaders)
- Fix critical bugs quickly
- Daily check-ins

**Week 3-4: Full Beta**
- Onboard remaining 40-90 testers
- Encourage daily usage
- Collect feedback surveys

**Week 5: Analysis**
- Compile feedback
- Analyze metrics
- Identify improvements for Phase 2

---

### Step 11: Collect Feedback and Iterate

**Goal:** Gather user feedback and make improvements before Phase 2.

**Time Estimate:** Ongoing (1-2 weeks of focused iteration)

#### 11.1 Create Feedback Collection System

**Google Form:**
```
Birthmark Beta Feedback Survey

1. How many photos have you taken with Birthmark?
   ○ 0-10  ○ 11-50  ○ 51-100  ○ 100+

2. How easy was the setup process? (1-10)
   1 - Very difficult ... 10 - Very easy

3. How long did it take to authenticate a photo on average?
   ○ <5 seconds  ○ 5-10 sec  ○ 10-30 sec  ○ >30 sec

4. Did you experience any failed captures?
   ○ Yes  ○ No
   If yes, how many?

5. How satisfied are you with the Birthmark camera? (1-10)
   1 - Very dissatisfied ... 10 - Very satisfied

6. What features would you like to see added?
   [Open text]

7. What problems did you encounter?
   [Open text]

8. Would you recommend Birthmark to other photographers?
   ○ Definitely  ○ Probably  ○ Maybe  ○ Probably not  ○ Definitely not

9. Any other comments?
   [Open text]
```

#### 11.2 Weekly Check-In Calls

Schedule 30-minute calls with select testers:

**Discussion Topics:**
- Overall experience
- Pain points encountered
- Feature requests
- Comparison to traditional cameras
- Willingness to pay for service

**Document findings in:** `docs/beta_feedback/week_N_notes.md`

#### 11.3 Bug Tracking

Use GitHub Issues:

```bash
# Create labels
gh label create "beta-bug" --color "d73a4a" --description "Bug reported by beta testers"
gh label create "beta-feature" --color "0075ca" --description "Feature request from beta"
gh label create "priority-high" --color "ff0000"
```

Triage bugs weekly:
- P0 (Critical): Fix immediately
- P1 (High): Fix within 48 hours
- P2 (Medium): Fix within 1 week
- P3 (Low): Defer to Phase 2

#### 11.4 Common Issues and Fixes

**Issue: Slow processing time (>10 seconds)**

*Investigation:*
```bash
# Check batch timeout
grep BATCH_TIMEOUT .env

# Check SMA response time
curl -w "@curl-format.txt" http://localhost:8001/api/v1/health

# Check database query time
EXPLAIN ANALYZE SELECT * FROM image_batch_map WHERE image_hash = 'abc...';
```

*Fix:* Reduce batch timeout or optimize database queries.

**Issue: Failed submissions**

*Investigation:*
```bash
# Check aggregator logs
docker logs birthmark-blockchain -f | grep ERROR

# Check SMA logs
docker logs birthmark-sma -f | grep ERROR

# Check device logs
ssh pi@raspberrypi.local
tail -f /var/log/birthmark-camera.log
```

*Common causes:*
- Network connectivity issues
- Invalid device certificates (expired)
- SMA downtime
- Database connection exhaustion

**Issue: Photos not verifying**

*Investigation:*
```bash
# Check if hash is in database
psql birthmark_blockchain -c "SELECT * FROM image_batch_map WHERE image_hash = 'abc...';"

# Check batch status
psql birthmark_blockchain -c "SELECT * FROM batches WHERE id = 123;"

# Check blockchain height
curl http://localhost:8545/api/v1/status | jq .block_height
```

#### 11.5 Feature Prioritization

Based on feedback, prioritize features for Phase 2:

**High Priority:**
- Multi-node blockchain (decentralization)
- Faster batch processing (<2 seconds)
- iOS app polish
- Better error messages

**Medium Priority:**
- GPS location tagging
- Timestamp verification improvements
- Backup/recovery tools

**Low Priority:**
- Advanced analytics
- Social features
- Third-party integrations

#### 11.6 Iteration Cycle

**Every 2 weeks:**

1. **Collect feedback** from surveys and calls
2. **Analyze metrics** from database and Grafana
3. **Prioritize fixes** based on impact and effort
4. **Implement changes** to codebase
5. **Deploy updates** to test environment
6. **Notify testers** of improvements
7. **Repeat**

#### 11.7 Beta Testing Report

At end of beta period, compile comprehensive report:

**Template:** `docs/BETA_TESTING_REPORT.md`

```markdown
# Phase 1 Beta Testing Report

## Executive Summary
- Total testers: 73
- Total images submitted: 1,247
- Success rate: 97.3%
- Average user satisfaction: 8.2/10
- Uptime: 99.6%

## Key Findings

### What Worked Well
- Provisioning process intuitive
- Authentication speed met targets (<5s)
- Blockchain verification reliable
- User interface simple and clear

### Pain Points
- Initial WiFi setup confusing for 23% of users
- Occasional SMA timeouts (2.7% of submissions)
- Lack of offline mode
- Battery life shorter than expected

## Metrics

[Tables and graphs of metrics]

## Feature Requests

Top 10 requested features:
1. Offline mode with sync later (requested by 45%)
2. Mobile app (iOS/Android) (41%)
3. GPS location tagging (38%)
...

## Recommended Actions

### Phase 1 Improvements
- [ ] Fix WiFi setup UX
- [ ] Optimize SMA timeout handling
- [ ] Improve battery management

### Phase 2 Priorities
- [ ] Launch iOS app
- [ ] Implement offline queue
- [ ] Add GPS support

## Conclusion

Phase 1 beta exceeded targets. Ready to proceed to Phase 2.
```

---

## Troubleshooting

### Common Issues

#### SMA won't start

**Symptoms:** `uvicorn` exits immediately

**Check:**
```bash
# Verify Python version
python3 --version  # Should be 3.9+

# Check for port conflict
lsof -i :8001

# Check logs
uvicorn src.main:app --reload --log-level debug
```

**Solution:**
- Kill process on port 8001
- Ensure all dependencies installed
- Check `data/` directory exists and is writable

#### Blockchain database connection fails

**Symptoms:** `could not connect to server`

**Check:**
```bash
# Verify PostgreSQL running
sudo systemctl status postgresql

# Test connection
psql -U birthmark -d birthmark_blockchain -h localhost

# Check .env DATABASE_URL
cat .env | grep DATABASE_URL
```

**Solution:**
- Start PostgreSQL: `sudo systemctl start postgresql`
- Verify credentials in DATABASE_URL
- Check PostgreSQL allows local connections

#### Camera provisioning fails

**Symptoms:** `Connection refused` or `Certificate validation failed`

**Check:**
```bash
# Verify SMA is running
curl http://localhost:8001/api/v1/health

# Check SMA has CA certificates
ls -la packages/sma/data/ca/

# Check device can reach SMA
ping localhost
```

**Solution:**
- Start SMA server
- Run `python scripts/setup_sma.py` to generate CAs
- Check firewall rules

#### Images not appearing on blockchain

**Symptoms:** Submission accepted but verification fails

**Check:**
```bash
# Check pending submissions
psql birthmark_blockchain -c "SELECT COUNT(*) FROM pending_submissions;"

# Check if batching is working
docker logs birthmark-blockchain | grep "Batch ready"

# Check SMA validation
docker logs birthmark-blockchain | grep "SMA validation"
```

**Solution:**
- Wait for batch timeout (default 300 seconds)
- Reduce BATCH_SIZE to 1 for testing
- Check SMA is responding to validation requests

#### High memory usage

**Symptoms:** Server becomes unresponsive

**Check:**
```bash
# Check memory usage
free -h
docker stats

# Check database connections
psql birthmark_blockchain -c "SELECT count(*) FROM pg_stat_activity;"
```

**Solution:**
- Increase server RAM
- Reduce database pool size
- Add connection limits
- Implement connection pooling

---

## Success Criteria

### Phase 1 Complete When:

**Technical:**
- [x] All services start successfully
- [x] End-to-end test passes (camera → blockchain → verify)
- [x] Performance benchmarks meet targets
- [x] 500+ images verified on blockchain
- [x] 99%+ uptime over 2 weeks
- [x] <1% false negative rate

**User Experience:**
- [x] 50+ beta testers onboarded
- [x] 80%+ user satisfaction score
- [x] Setup time <15 minutes per device
- [x] Photo authentication <5 seconds

**Documentation:**
- [x] All components documented
- [x] Beta tester guide complete
- [x] Troubleshooting guide written
- [x] API documentation published

**Security:**
- [x] Device signatures verified
- [x] Rate limiting implemented
- [x] No security vulnerabilities (penetration test)
- [x] Certificate chain validated

### Ready for Phase 2 When:

- Phase 1 success criteria met
- Beta testing report compiled
- Key improvements identified
- iOS app codebase ready
- Multi-node blockchain design complete
- Funding secured for Phase 2 hosting

---

## Next Steps After Phase 1

Once Phase 1 is complete:

1. **Compile lessons learned** document
2. **Archive Phase 1 code** (tag v1.0.0)
3. **Plan Phase 2 architecture** improvements
4. **Design multi-node consensus** protocol
5. **Prepare iOS app** for TestFlight
6. **Secure partnerships** with photography organizations
7. **Apply for grants** (SBIR, foundations)
8. **Begin Phase 2 development**

---

## Resources

### Documentation
- [System Architecture](../architecture/system_overview.png)
- [API Specifications](../specs/)
- [Phase 1 Plan](../phase-plans/Birthmark_Phase_1_Plan_*.md)

### Tools
- PostgreSQL: https://postgresql.org/docs/
- FastAPI: https://fastapi.tiangolo.com/
- Docker: https://docs.docker.com/
- Alembic: https://alembic.sqlalchemy.org/

### Support
- GitHub Issues: https://github.com/Birthmark-Standard/Birthmark/issues
- Email: dev@birthmark.org
- Discord: #phase-1-dev

---

*Last updated: November 2025*
*Version: 1.0*
*Maintained by: Birthmark Standard Foundation*
