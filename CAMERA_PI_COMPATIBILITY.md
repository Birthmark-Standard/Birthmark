# Camera-Pi ↔ Submission Server Compatibility Guide

**Date:** December 3, 2025
**Issue:** Camera-pi uses old format, submission server expects new format
**Solution:** Use legacy endpoint (1 line change)

---

## Current Situation

### Camera-Pi Configuration (Your Setup)
- **Location:** Raspberry Pi (SSH access)
- **Network:** Local wireless
- **TPM:** None (mock crypto operations)
- **Data:** Raw Bayer only (no ISP processing)
- **Format:** Legacy 3-table submission

### Camera-Pi Current Output
```python
# What aggregation_client.py sends:
{
    "image_hash": "abc123...",              # Single raw Bayer hash
    "encrypted_nuc_token": "base64...",      # Packed: ciphertext + nonce + tag
    "table_references": [42, 123, 456],     # 3 assigned tables
    "key_indices": [7, 99, 512],            # Actual + 2 random (privacy)
    "timestamp": 1733259600
}
```

### Submission Server Endpoints

#### Endpoint 1: `/api/v1/submit` (NEW - 2-hash format)
**Expected:**
```python
{
    "submission_type": "camera",
    "image_hashes": [  # Array of hashes
        {"image_hash": "...", "modification_level": 0, "parent_image_hash": null},
        {"image_hash": "...", "modification_level": 1, "parent_image_hash": "..."}
    ],
    "camera_token": {  # Structured (not packed)
        "ciphertext": "hex...",
        "auth_tag": "hex...",
        "nonce": "hex...",
        "table_id": 42,     # Single table
        "key_index": 7
    },
    "manufacturer_cert": {...},
    "timestamp": 1733259600
}
```

#### Endpoint 2: `/api/v1/submit-legacy` (OLD - Your format) ✅
**Expected:**
```python
{
    "image_hash": "abc123...",
    "encrypted_nuc_token": "base64...",
    "table_references": [42, 123, 456],  # 3 tables
    "key_indices": [7, 99, 512],
    "timestamp": 1733259600
}
```

**THIS MATCHES YOUR CURRENT OUTPUT!**

---

## ✅ Quick Fix (1 Line Change)

**File:** `packages/camera-pi/src/camera_pi/aggregation_client.py`
**Line:** 223

### Change:
```python
# FROM:
endpoint = f"{self.server_url}/api/v1/submit"

# TO:
endpoint = f"{self.server_server}/api/v1/submit-legacy"
```

**That's it!** Your camera-pi will now work with the submission server.

---

## Verification Steps

### 1. Check What Camera-Pi Sends

On the Pi, run:
```bash
cd /home/user/Birthmark/packages/camera-pi
python3 -c "
from camera_pi.aggregation_client import AuthenticationBundle
import time

bundle = AuthenticationBundle(
    image_hash='a' * 64,
    camera_token={
        'ciphertext': 'b' * 64,
        'nonce': 'c' * 24,
        'auth_tag': 'd' * 32,
        'table_id': 42,
        'key_index': 7
    },
    timestamp=int(time.time()),
    table_assignments=[42, 123, 456]
)

import json
print(json.dumps(bundle.to_json(), indent=2))
"
```

**Expected output:**
```json
{
  "image_hash": "aaaa...",
  "encrypted_nuc_token": "YmJi...",
  "table_references": [42, 123, 456],
  "key_indices": [7, <random>, <random>],
  "timestamp": 1733259600
}
```

### 2. Test Submission to Server

**Start submission server:**
```bash
# Terminal 1: Start aggregator
cd packages/blockchain
uvicorn src.main:app --port 8545 --host 0.0.0.0

# Terminal 2: Start SMA
cd packages/sma
uvicorn src.main:app --port 8001 --host 0.0.0.0
```

**From Pi, test connection:**
```bash
# Replace with actual server IP
SERVER_IP="192.168.1.x"

# Test health
curl http://$SERVER_IP:8545/

# Should return: {"service": "Birthmark Blockchain Node", ...}
```

**From Pi, submit bundle:**
```python
# packages/camera-pi/test_submission.py
from camera_pi.aggregation_client import AggregationClient, AuthenticationBundle
import time

# Create client (replace with your server IP)
client = AggregationClient(server_url="http://192.168.1.x:8545")

# Test connection
if not client.test_connection():
    print("✗ Cannot connect to server!")
    exit(1)

print("✓ Connected to server")

# Create test bundle
bundle = AuthenticationBundle(
    image_hash="a" * 64,
    camera_token={
        'ciphertext': 'b' * 64,
        'nonce': 'c' * 24,
        'auth_tag': 'd' * 32,
        'table_id': 0,  # Use table 0 (must exist in SMA)
        'key_index': 0
    },
    timestamp=int(time.time()),
    table_assignments=[0, 1, 2]  # First 3 tables
)

# Submit
try:
    receipt = client.submit_bundle(bundle)
    print(f"✓ Submission successful!")
    print(f"  Receipt ID: {receipt.receipt_id}")
    print(f"  Status: {receipt.status}")
except Exception as e:
    print(f"✗ Submission failed: {e}")
```

**Run:**
```bash
python3 test_submission.py
```

**Expected:**
```
✓ Connected to server
✓ Submission successful!
  Receipt ID: a1b2c3d4-e5f6-7890-abcd-ef0123456789
  Status: pending_validation
```

---

## Configuration for Pi Camera

### Network Setup

**Your setup:** Pi on local wireless → Server on same network

**Find server IP:**
```bash
# On server machine
ip addr show | grep "inet "

# Example output:
# inet 192.168.1.100/24
```

**Update camera-pi config:**
```python
# In your camera capture script
from camera_pi.aggregation_client import AggregationClient

client = AggregationClient(
    server_url="http://192.168.1.100:8545",  # Your server IP
    timeout=10,
    max_retries=3
)
```

### No TPM = Mock Crypto

Since you don't have TPM working, the camera token will use mock values:

```python
# camera_token.py currently generates mock tokens
camera_token = {
    "ciphertext": secrets.token_hex(32),  # Random (not real NUC hash)
    "auth_tag": secrets.token_hex(16),
    "nonce": secrets.token_hex(12),
    "table_id": 0,
    "key_index": 0
}
```

**This is fine for Phase 1 testing!** The SMA will validate the format but not decrypt.

---

## What Happens After Submission

### Current Flow (With Legacy Endpoint):

```
Pi Camera
  ↓ POST /api/v1/submit-legacy
Aggregator (receives, stores in DB)
  ↓ Validate with SMA
SMA (validates token format)
  ↓ Returns PASS/FAIL
Aggregator (updates validation status)
  ↓ Submits to blockchain ← ⚠️ THIS WILL FAIL (no blockchain yet)
Blockchain (ERROR - not implemented)
```

### What Works:
- ✅ Pi → Aggregator submission
- ✅ Storage in database
- ✅ SMA validation (format checks)

### What Fails:
- ❌ Blockchain submission (no blockchain node)

**Error you'll see:**
```
✗ Cannot connect to blockchain node at http://localhost:8546
```

This is expected! We need to implement the blockchain node next.

---

## Next Steps

### Immediate (Test Legacy Endpoint):
1. ✅ Change endpoint to `/api/v1/submit-legacy`
2. ✅ Test from Pi to server
3. ✅ Verify submission reaches aggregator
4. ✅ Check database for stored hash

### Short-term (Add Blockchain):
1. Create mock blockchain endpoint (30 min)
2. Test end-to-end flow
3. Verify hashes stored

### Long-term (Real Blockchain):
1. Implement minimal blockchain (1 week)
2. Multi-node support
3. Production deployment

---

## Blockchain Node Implementation (Next Task)

Since your submission will fail at blockchain submission, we need to create a minimal blockchain node.

**Requirements:**
- Accept hash submissions
- Store in PostgreSQL
- Return tx_id and block_height
- Provide verification API

**Estimated time:** 4-6 hours for minimal implementation

Would you like me to:
1. Create mock blockchain endpoint (30 min) - Unblocks testing immediately
2. Implement real blockchain (4-6 hours) - Full Phase 1 system

---

## Summary

**Current Status:**
- ✅ Camera-pi code exists and works
- ✅ Submission server exists and works
- ❌ Format mismatch (easily fixed with 1 line)
- ❌ No blockchain node (need to implement)

**Quickest Path:**
1. Change endpoint to `submit-legacy` (1 line)
2. Test Pi → Aggregator (works!)
3. Implement mock blockchain (30 min)
4. Test full flow (works!)

**Then you have a working end-to-end system today!**
