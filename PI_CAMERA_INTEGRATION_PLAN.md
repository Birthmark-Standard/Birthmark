# Pi Camera → Submission Server Integration Plan

**Date:** December 3, 2025
**Status:** 🚧 Integration Pending
**Goal:** Connect tested Raspberry Pi camera to submission server for Phase 1

---

## Current Status

### ✅ What's Complete

**Submission Server:**
- ✅ 2-hash camera submission endpoint (`POST /api/v1/submit`)
- ✅ Structured camera token validation
- ✅ SMA integration (validates camera tokens)
- ✅ Direct blockchain submission logic
- ✅ Database schema (with migration)
- ✅ Mock camera client for testing

**Raspberry Pi Camera (Assumption):**
- ✅ Raw Bayer capture working
- ✅ Hash computation with TPM
- ✅ 12MP image capture
- ✅ Hardware validated (HQ Camera + LetsTrust TPM)

### ❌ What's Missing

**Critical Blockers:**
1. ❌ **Blockchain Node API** - Aggregator tries to submit but no blockchain exists
2. ❌ **Pi Camera Submission Client** - Need to adapt mock client for real Pi
3. ❌ **Real Camera Token Generation** - Mock tokens won't work with real SMA
4. ❌ **Network Configuration** - How does Pi reach aggregator?
5. ❌ **Device Provisioning** - Pi needs to be registered with SMA

---

## Integration Tasks

### Task 1: Implement Blockchain Node API ⚠️ CRITICAL

**Current Problem:**
```python
# In submissions.py after SMA validation:
blockchain_result = await blockchain_client.submit_hash(...)
# ^ This will fail - no blockchain node exists!
```

**Options:**

#### Option A: Mock Blockchain for Phase 1 (Fastest)
Create a simple mock that accepts submissions without actual blockchain:

```python
# packages/blockchain/src/node/api/mock_blockchain.py
@router.post("/api/v1/blockchain/submit")
async def mock_blockchain_submit(data: dict):
    """Mock blockchain submission for Phase 1 testing."""
    return {
        "tx_id": random.randint(1, 100000),
        "block_height": random.randint(1, 1000),
        "message": "Mock submission successful"
    }
```

**Pros:** Unblocks Pi camera testing immediately
**Cons:** Not real blockchain
**Time:** 30 minutes

#### Option B: Implement Minimal Blockchain (Recommended)
Build a simple blockchain node that stores hashes:

**Required Components:**
1. Block storage (PostgreSQL)
2. Transaction recording
3. Hash verification API
4. Simple consensus (single node for now)

**Time:** 4-6 hours

#### Option C: Wait for Full Blockchain Implementation
Complete the full PoA blockchain with multiple nodes.

**Time:** 2-3 weeks

**Recommendation:** Start with **Option A (mock)** to unblock Pi testing, then implement **Option B** in parallel.

---

### Task 2: Create Pi Camera Submission Client

**Location:** `packages/camera-pi/src/submission.py`

**Requirements:**
Adapt the mock camera client to use real Pi hardware:

```python
# packages/camera-pi/src/submission.py
import hashlib
from picamera2 import Picamera2
from tpm_interface import get_tpm_signature
from crypto_utils import generate_camera_token

async def capture_and_submit():
    """Capture raw Bayer, hash with TPM, submit to aggregator."""

    # 1. Capture raw Bayer data
    picam2 = Picamera2()
    config = picam2.create_still_configuration(
        raw={'format': 'SRGGB10', 'size': (4056, 3040)}
    )
    picam2.configure(config)
    picam2.start()
    raw_array = picam2.capture_array("raw")
    bayer_bytes = raw_array.tobytes()

    # 2. Hash raw Bayer with TPM
    raw_hash = hashlib.sha256(bayer_bytes).hexdigest()

    # 3. Process to JPEG and hash
    jpeg_bytes = convert_to_jpeg(raw_array)
    processed_hash = hashlib.sha256(jpeg_bytes).hexdigest()

    # 4. Generate real camera token (not mock!)
    camera_token = generate_camera_token(
        nuc_hash=get_nuc_hash(),
        table_id=get_assigned_table_id(),
        key_index=get_current_key_index(),
        encryption_key=get_table_key()
    )

    # 5. Create submission
    submission = {
        "submission_type": "camera",
        "image_hashes": [
            {
                "image_hash": raw_hash,
                "modification_level": 0,
                "parent_image_hash": None
            },
            {
                "image_hash": processed_hash,
                "modification_level": 1,
                "parent_image_hash": raw_hash
            }
        ],
        "camera_token": camera_token,
        "manufacturer_cert": {
            "authority_id": "SIMULATED_MFG_001",
            "validation_endpoint": "http://aggregator:8001/validate"
        },
        "timestamp": int(time.time())
    }

    # 6. Submit to aggregator
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{AGGREGATOR_URL}/api/v1/submit",
            json=submission
        )
        return response.json()
```

**Key Differences from Mock:**
- ❌ No `secrets.token_bytes()` - use real camera data
- ✅ Real Picamera2 capture
- ✅ Real TPM operations
- ✅ Real camera token encryption
- ✅ Real NUC hash

**Time:** 2-3 hours

---

### Task 3: Real Camera Token Generation

**Current Problem:**
Mock camera client uses fake tokens:
```python
# Mock (current)
camera_token = {
    "ciphertext": secrets.token_hex(64),  # FAKE
    "auth_tag": secrets.token_hex(16),    # FAKE
    "nonce": secrets.token_hex(12),       # FAKE
    "table_id": 0,
    "key_index": 0
}
```

**Real Implementation Needed:**
```python
# packages/camera-pi/src/crypto_utils.py
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

def generate_camera_token(
    nuc_hash: bytes,
    table_id: int,
    key_index: int,
    encryption_key: bytes  # From provisioning
) -> dict:
    """Generate real encrypted camera token."""

    # 1. Get NUC hash from camera sensor
    # (NUC = Non-Uniformity Correction map unique to this sensor)

    # 2. Encrypt NUC hash with AES-GCM
    aesgcm = AESGCM(encryption_key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, nuc_hash, None)

    # 3. Split ciphertext and auth tag
    # (AESGCM returns ciphertext || auth_tag)
    auth_tag = ciphertext[-16:]
    ciphertext_only = ciphertext[:-16]

    return {
        "ciphertext": ciphertext_only.hex(),
        "auth_tag": auth_tag.hex(),
        "nonce": nonce.hex(),
        "table_id": table_id,
        "key_index": key_index
    }
```

**Dependencies:**
- NUC map extraction from camera sensor
- Provisioned encryption keys from SMA
- Secure key storage on Pi

**Time:** 3-4 hours

---

### Task 4: Device Provisioning

**Problem:** Pi camera needs to be registered with SMA before it can submit.

**Provisioning Process:**

#### Step 1: SMA Generates Device Identity
```bash
cd packages/sma
python scripts/provision_device.py \
  --serial "PI_CAMERA_001" \
  --device-family "Raspberry Pi HQ Camera" \
  --nuc-hash <extracted_from_sensor>
```

**This creates:**
- Device record in SMA database
- Assigns 3 key tables (or 1 in Phase 1)
- Generates encryption keys
- Creates device certificate

#### Step 2: Pi Camera Receives Credentials
The Pi needs to store:
```json
{
  "device_serial": "PI_CAMERA_001",
  "table_id": 42,
  "encryption_key": "base64_encoded_key",
  "manufacturer_cert": {
    "authority_id": "SIMULATED_MFG_001",
    "validation_endpoint": "http://aggregator:8001/validate"
  }
}
```

**Storage Location:** `/etc/birthmark/device_config.json` (secure permissions)

**Time:** 2 hours (including secure storage setup)

---

### Task 5: Network Configuration

**Deployment Scenarios:**

#### Scenario A: Local Development (Same Machine)
```
Pi Camera          Aggregator         SMA
localhost:---  →   localhost:8545  ←→ localhost:8001
                        ↓
                   Blockchain Node
                   localhost:8546
```

**Configuration:**
```bash
# On Pi
export AGGREGATOR_URL=http://localhost:8545

# Aggregator
export SMA_URL=http://localhost:8001
export BLOCKCHAIN_URL=http://localhost:8546
```

#### Scenario B: Local Network (Separate Devices)
```
Pi Camera          Aggregator         SMA
192.168.1.10   →   192.168.1.100  ←→ 192.168.1.101
                        ↓
                   Blockchain Node
                   192.168.1.102
```

**Configuration:**
```bash
# On Pi
export AGGREGATOR_URL=http://192.168.1.100:8545

# Aggregator
export SMA_URL=http://192.168.1.101:8001
export BLOCKCHAIN_URL=http://192.168.1.102:8546
```

#### Scenario C: Production (Internet)
```
Pi Camera          Aggregator              SMA
anywhere       →   aggregator.birthmark.org  ←→  sma.manufacturer.com
                        ↓
                   Blockchain Network
                   (multiple nodes)
```

**Requires:**
- Domain names
- SSL certificates
- Authentication tokens
- Rate limiting

**Time:** 1 hour (local), 1 day (production)

---

### Task 6: End-to-End Testing

**Test Sequence:**

#### Test 1: Single Capture
```bash
# On Pi
python src/main.py --capture-once

# Expected:
# ✓ Raw Bayer captured (12MP)
# ✓ Raw hash computed with TPM
# ✓ JPEG processed
# ✓ Processed hash computed
# ✓ Camera token generated
# ✓ Submitted to aggregator
# ✓ SMA validation PASSED
# ✓ Blockchain submission successful
# ✓ Receipt ID received
```

#### Test 2: Continuous Capture
```bash
# On Pi
python src/main.py --continuous 10

# Expected:
# ✓ 10 captures complete
# ✓ All submitted successfully
# ✓ <5 second processing time per capture
# ✓ No errors or crashes
```

#### Test 3: Verification
```bash
# Query aggregator
curl http://aggregator:8545/api/v1/verify/<image_hash>

# Expected:
{
  "verified": true,
  "timestamp": 1733259600,
  "block_height": 123,
  "tx_id": 456
}
```

**Time:** 2 hours

---

## Implementation Timeline

### Phase 1: Mock Blockchain (1 Day)
**Goal:** Unblock Pi testing with mock blockchain

- [ ] Implement mock blockchain API (30 min)
- [ ] Update aggregator config to use mock (15 min)
- [ ] Test mock submission with mock camera client (15 min)
- [ ] Create Pi camera submission client (3 hours)
- [ ] Test Pi → Aggregator → Mock Blockchain (1 hour)

**Deliverable:** Pi camera can submit to aggregator, gets mock blockchain confirmation

### Phase 2: Real Blockchain (1 Week)
**Goal:** Implement minimal blockchain with real storage

- [ ] Design blockchain schema (2 hours)
- [ ] Implement block storage (4 hours)
- [ ] Implement transaction recording (4 hours)
- [ ] Implement hash verification API (4 hours)
- [ ] Add blockchain consensus (8 hours)
- [ ] Integration testing (4 hours)

**Deliverable:** Real blockchain that stores hashes with verification

### Phase 3: Production Readiness (2 Weeks)
**Goal:** Multi-node blockchain, real cryptography, monitoring

- [ ] Multi-node blockchain network
- [ ] Real NUC extraction and encryption
- [ ] Device provisioning workflow
- [ ] SSL/TLS for production
- [ ] Monitoring and alerting
- [ ] Performance optimization

**Deliverable:** Production-ready system

---

## Critical Path (Fastest to Working System)

### Day 1: Mock Blockchain + Pi Integration
1. ✅ Implement mock blockchain API (30 min)
2. ✅ Create Pi camera submission client (3 hours)
3. ✅ Test end-to-end with mock tokens (1 hour)

**Outcome:** Pi can capture, hash, and submit (with mock validation)

### Day 2: Real Camera Tokens
1. ✅ Implement real camera token generation (4 hours)
2. ✅ Device provisioning with SMA (2 hours)
3. ✅ Test with real SMA validation (2 hours)

**Outcome:** Pi submits with real encrypted tokens, SMA validates

### Day 3: Minimal Blockchain
1. ✅ Implement simple blockchain storage (6 hours)
2. ✅ Test full end-to-end flow (2 hours)

**Outcome:** Fully functional Phase 1 system

---

## Files to Create

### 1. Pi Camera Client
```
packages/camera-pi/src/
├── submission.py          # Main submission logic
├── crypto_utils.py        # Camera token generation
├── config.py              # Load device config
└── main.py                # CLI entry point
```

### 2. Mock Blockchain (Temporary)
```
packages/blockchain/src/node/api/
├── mock_blockchain.py     # Mock blockchain API
└── __init__.py
```

### 3. Real Blockchain (Phase 2)
```
packages/blockchain/src/node/
├── api/
│   └── blockchain.py      # Real blockchain API
├── storage/
│   └── block_storage.py   # Block and transaction storage
└── consensus/
    └── poa.py             # Proof of Authority consensus
```

---

## Configuration Files Needed

### Pi Camera: `/etc/birthmark/device_config.json`
```json
{
  "device_serial": "PI_CAMERA_001",
  "table_id": 42,
  "encryption_key": "base64_encoded_key_from_provisioning",
  "aggregator_url": "http://192.168.1.100:8545",
  "manufacturer_cert": {
    "authority_id": "SIMULATED_MFG_001",
    "validation_endpoint": "http://192.168.1.101:8001/validate"
  }
}
```

### Aggregator: `.env`
```bash
DATABASE_URL=postgresql://birthmark:birthmark@localhost:5432/birthmark_dev
SMA_VALIDATION_ENDPOINT=http://localhost:8001/validate
BLOCKCHAIN_ENDPOINT=http://localhost:8546/api/v1/blockchain/submit
AGGREGATOR_NODE_ID=aggregator_node_001
```

### SMA: `.env`
```bash
SMA_DATA_DIR=/var/lib/birthmark/sma
KEY_TABLES_PATH=/var/lib/birthmark/sma/key_tables.json
DEVICE_REGISTRY_PATH=/var/lib/birthmark/sma/device_registry.json
```

---

## Testing Checklist

**Before Integration:**
- [ ] Submission server passes all tests (✅ Done)
- [ ] Pi camera can capture raw Bayer (✅ Assumed done)
- [ ] Pi camera can hash with TPM (✅ Assumed done)
- [ ] SMA key tables initialized (❌ Needs running)
- [ ] Aggregator database migrated (❌ Needs running)

**After Integration:**
- [ ] Pi can submit with mock tokens
- [ ] Aggregator receives and stores submission
- [ ] SMA validates mock tokens
- [ ] Mock blockchain accepts submission
- [ ] Pi can submit with real tokens
- [ ] SMA validates real tokens
- [ ] Real blockchain stores hashes
- [ ] Verification queries work
- [ ] Continuous capture works (10+ images)
- [ ] Load test works (250+ images)

---

## Recommendations

### Start Here (Fastest Path):
1. **Implement mock blockchain** (30 min) - Unblocks everything
2. **Create Pi submission client** (3 hours) - Uses real camera hardware
3. **Test with mock tokens** (1 hour) - Validates data flow

This gives you a working system **today** that you can iterate on.

### Then:
4. Implement real camera token generation (4 hours)
5. Provision Pi device with SMA (2 hours)
6. Test with real SMA validation (2 hours)

This gives you **real cryptographic validation**.

### Finally:
7. Implement minimal blockchain (1 week)
8. Full end-to-end testing (2 days)

This gives you a **complete Phase 1 system**.

---

## Questions to Answer

1. **Where is the Pi camera currently?**
   - Same machine as servers?
   - Separate device on local network?
   - Remote location?

2. **What's the current Pi camera status?**
   - Can it capture raw Bayer?
   - Can it compute hashes?
   - Does it have TPM working?

3. **What's the priority?**
   - Fast demo (mock blockchain)?
   - Real blockchain (takes longer)?
   - Production-ready (weeks)?

4. **What hardware is available?**
   - Single Pi + laptop?
   - Multiple devices?
   - Server infrastructure?

---

**Next Step:** Implement mock blockchain API (30 minutes) to unblock Pi camera testing.

Would you like me to create the mock blockchain API now?
