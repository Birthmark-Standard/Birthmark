# Birthmark Phase 1 Demo Guide

**Status:** Phase 1 Complete ✅
**Last Updated:** January 10, 2026

Complete end-to-end demonstration of the Birthmark authentication pipeline using the current Phase 1 architecture.

## System Components

The Phase 1 build consists of three operational packages:

1. **SMA (Simulated Manufacturer Authority)** - `packages/sma/`
   - Validates camera tokens using encrypted NUC hashes
   - Maintains key table database (10 tables in Phase 1)
   - Returns PASS/FAIL without seeing image hashes
   - Provisions cameras with table assignments

2. **Blockchain Node** - `packages/blockchain/`
   - Merged aggregator + blockchain validator architecture
   - Receives camera submissions via FastAPI
   - Routes validation to SMA
   - Stores authenticated hashes in PostgreSQL
   - Single-node consensus for Phase 1

3. **Camera (Raspberry Pi)** - `packages/camera-pi/`
   - Sony IMX477 HQ Camera (12.3 MP)
   - Raw Bayer + ISP-processed image capture
   - Simulated Secure Element (AES-256-GCM encryption)
   - SHA-256 hashing and certificate generation
   - Submits to blockchain node

4. **Demo Script** - `scripts/demo_phase1_pipeline.py`
   - Simulates camera capture without hardware
   - Runs complete end-to-end test
   - Demonstrates all system components

## Prerequisites

- PostgreSQL running with `birthmark_chain` database
- Python 3.11+
- All dependencies installed

## Quick Start

### Terminal 1: Start SMA

```bash
cd /home/user/Birthmark/packages/sma
uvicorn src.main:app --host 0.0.0.0 --port 8001
```

You should see:
```
✓ Loaded Phase 1 key tables: 10 tables
✓ Loaded 1 device registrations
✓ Device provisioner ready
```

### Terminal 2: Start Blockchain Node

```bash
cd /home/user/Birthmark/packages/blockchain
python -m src.main
```

You should see:
```
Starting Birthmark Blockchain Node: phase1_blockchain_node
Consensus mode: single
```

The node runs on `http://localhost:8545`

### Terminal 3: Run Demo

```bash
cd /home/user/Birthmark
python scripts/demo_phase1_pipeline.py
```

## What the Demo Does

### Step 1: Check Services
- Verifies SMA is running on port 8001
- Verifies blockchain node is running on port 8545
- Shows current blockchain status

### Step 2: Simulate Camera Capture
- Loads camera provisioning data
- Generates test image hashes (raw + processed)
- Creates encrypted camera token
- Shows token details (table ID, key index, ciphertext)

### Step 3: Submit to Blockchain
- Sends complete camera submission with 2 hashes
- Includes manufacturer certificate
- Shows submission receipt

**🔍 Watch Terminal 2 (Blockchain) for detailed logs showing:**
- Complete submission contents (image hashes, camera token)
- SMA validation request/response
- Blockchain storage confirmation

### Step 4: Verify on Blockchain
- Queries blockchain for each hash
- Shows verification results including:
  - Block height and TX ID
  - Timestamp
  - Submission server ID
  - Modification level (0=raw, 1=processed)
  - Parent hash (provenance chain)

### Step 5: Final Status
- Shows updated blockchain statistics
- Confirms hashes were stored

## Expected Output

```
🎬 BIRTHMARK PHASE 1 - END-TO-END DEMONSTRATION
================================================================================

🔍 Step 1: Checking services...
✅ SMA is running at http://localhost:8001
✅ Blockchain node is running at http://localhost:8545
   Current block height: 1
   Total hashes: 0

📷 Step 2: Simulating camera capture...
✅ Loaded provisioning for device: BIRTHMARK_PI_001
📋 Simulated image capture:
   Raw hash: a1b2c3d4e5f6...
   Processed hash: f6e5d4c3b2a1...

🔐 Generated camera token:
   Table ID: 3
   Key Index: 452
   Ciphertext: 2f358ac4a60fe672...

📤 Step 3: Submitting to blockchain node...
✅ Submission accepted!
   Receipt ID: 550e8400-e29b-41d4-a716-446655440000
   Status: pending_validation

🔍 Step 4: Verifying hashes on blockchain...
[1] Verifying raw hash: a1b2c3d4e5f6...
   ✅ VERIFIED on blockchain!
      Block height: 1
      TX ID: 1
      Modification level: 0

[2] Verifying processed hash: f6e5d4c3b2a1...
   ✅ VERIFIED on blockchain!
      Block height: 1
      TX ID: 2
      Modification level: 1
      Parent hash: a1b2c3d4e5f6...

📊 Step 5: Final blockchain status...
✅ Blockchain node status:
   Block height: 1
   Total hashes: 2

🎉 DEMO COMPLETE!
```

## Viewing Detailed Logs

The blockchain node (Terminal 2) shows comprehensive logging:

### Submission Received
```
================================================================================
📨 CAMERA SUBMISSION RECEIVED (Transaction ID: 550e8400-...)
================================================================================
Number of hashes: 2
Manufacturer: SIMULATED_CAMERA_001

📋 IMAGE HASHES:
  [1] Hash: a1b2c3d4e5f6...
      Level: 0 (Raw)
      Parent: None

  [2] Hash: f6e5d4c3b2a1...
      Level: 1 (Processed)
      Parent: a1b2c3d4e5f6...

🔐 CAMERA TOKEN:
  Ciphertext: 2f358ac4a60fe672...
  Auth Tag: 1a2b3c4d5e6f...
  Nonce: 9f8e7d6c5b4a...
  Table ID: 3
  Key Index: 452
```

### SMA Validation
```
================================================================================
🔒 VALIDATING with SMA: SIMULATED_CAMERA_001
================================================================================
Transaction ID: 550e8400-...
Sending to: http://localhost:8001/validate
Token - Table: 3, Key: 452

📬 SMA VALIDATION RESPONSE:
  Result: ✅ PASS
  Message: Camera authenticated
```

### Blockchain Storage
```
🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗
⛓️  BLOCKCHAIN SUBMISSION SUCCESS
   Hash: a1b2c3d4e5f6...f6e5d4c3b2a1
   TX ID: 1
   Block Height: 1
   Modification Level: 0
🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗
```

## Troubleshooting

### SMA Not Running
```
❌ Connection error: [Errno 111] Connection refused
```
**Solution:** Start SMA in Terminal 1

### Blockchain Node Not Running
```
❌ Blockchain node returned 404
```
**Solution:** Start blockchain node in Terminal 2

### Provisioning Data Not Found
```
❌ Provisioning data not found at packages/camera-pi/data/provisioning_data.json
```
**Solution:** Run camera provisioning:
```bash
cd packages/camera-pi
python scripts/provision_camera.py
```

### PostgreSQL Not Running
```
sqlalchemy.exc.OperationalError: could not connect to server
```
**Solution:** Start PostgreSQL:
```bash
pg_ctlcluster 16 main start
```

## Database Inspection

View stored hashes directly in PostgreSQL:

```bash
psql -U birthmark -d birthmark_chain
```

```sql
-- View all hashes
SELECT image_hash, modification_level, block_height, timestamp
FROM image_hashes
ORDER BY block_height DESC;

-- View transactions
SELECT tx_id, submission_server_id, batch_size, block_height
FROM transactions
ORDER BY tx_id DESC;

-- View provenance chain
SELECT
  ih.image_hash,
  ih.modification_level,
  ih.parent_image_hash,
  t.submission_server_id
FROM image_hashes ih
JOIN transactions t ON ih.tx_id = t.tx_id
ORDER BY ih.modification_level;
```

## Next Steps

### Test with Real Camera
Replace the demo script with actual Raspberry Pi camera:

```bash
cd packages/camera-pi
python -m camera_pi.main --submission-url http://localhost:8545
```

### Add More Devices
Provision additional cameras:

```bash
cd packages/sma
python scripts/provision_device.py --serial CAMERA_002
```

### Monitor System
- Check SMA statistics: `http://localhost:8001/stats`
- Check blockchain status: `http://localhost:8545/api/v1/blockchain/status`
- View device list: `http://localhost:8001/api/v1/devices`

## Architecture Summary

### Current Phase 1 Architecture

```
┌────────────────────────────────────────────────────────────┐
│  Camera Package (packages/camera-pi/)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 1. Capture raw Bayer data (Sony IMX477)             │  │
│  │ 2. Hash raw data (SHA-256)                           │  │
│  │ 3. Process through ISP → hash processed image       │  │
│  │ 4. Generate NUC hash (simulated sensor calibration) │  │
│  │ 5. Encrypt NUC hash with AES-256-GCM                │  │
│  │ 6. Create manufacturer certificate                   │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────┬───────────────────────────────────────────┘
                 │ POST /api/v1/submit
                 │ (image_hashes + manufacturer_cert)
                 ▼
┌────────────────────────────────────────────────────────────┐
│  Blockchain Node (packages/blockchain/)                    │
│  Merged Aggregator + Validator                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ FastAPI Server (Port 8545)                           │  │
│  │ - Receives camera submissions                         │  │
│  │ - Extracts manufacturer certificate                   │  │
│  │ - Routes to appropriate SMA                           │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────┬───────────────────────────────────────────┘
                 │ POST /validate
                 │ (camera_token + key_reference)
                 │ ❌ NO IMAGE HASHES SENT
                 ▼
┌────────────────────────────────────────────────────────────┐
│  SMA (packages/sma/)                                       │
│  Simulated Manufacturer Authority                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 1. Decrypt camera token using key table             │  │
│  │ 2. Verify NUC hash matches provisioned camera        │  │
│  │ 3. Return PASS/FAIL (never sees image hashes)       │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────┬───────────────────────────────────────────┘
                 │ Response: {"valid": true, "authority_validation": "PASS"}
                 ▼
┌────────────────────────────────────────────────────────────┐
│  Blockchain Storage (PostgreSQL)                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ If PASS: Store image hashes + metadata              │  │
│  │ - image_hash (SHA-256, 64 hex chars)                 │  │
│  │ - modification_level (0=raw, 1=processed)            │  │
│  │ - parent_image_hash (provenance chain)               │  │
│  │ - authority_id (SIMULATED_CAMERA_001)                │  │
│  │ - timestamp, block_height, tx_id                     │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│  Public Verification (GET /api/v1/verify/{hash})           │
│  Anyone can query blockchain to verify image authenticity  │
└────────────────────────────────────────────────────────────┘
```

### Key Architecture Decisions

**Direct Hash Submission (No Batching):**
- Removed Merkle tree batching (see `ARCHITECTURE_CHANGE_NO_BATCHING.md`)
- Each hash submitted individually to custom blockchain
- Simpler verification: hash image → query blockchain directly
- No gas fees on custom blockchain operated by coalition

**Merged Aggregator + Validator:**
- Single deployable node per institution
- Trust alignment: aggregators ARE validators
- Operational simplicity: fewer moving parts
- Natural scaling: each institution adds capacity + redundancy

**Privacy by Design:**
- SMA never sees image hashes (only encrypted camera token)
- Blockchain stores hashes only (irreversible, no image content)
- Table anonymity: thousands of cameras share same table IDs
- Timestamp obfuscation: server processing time, not capture time

## Phase 1 Status ✅

### What's Working (January 10, 2026)

You now have a **complete, operational** end-to-end Birthmark authentication system:

**✅ Camera Authentication Pipeline:**
- Raw Bayer capture and hashing (Sony IMX477)
- ISP-processed image capture and hashing
- Simulated Secure Element with AES-256-GCM encryption
- HKDF key derivation from 3 master keys
- Manufacturer certificate generation
- Complete submission to blockchain node

**✅ Blockchain Node (Merged Architecture):**
- FastAPI server accepting camera submissions
- SMA validation routing (never exposes image hashes)
- Direct blockchain storage (no batching)
- PostgreSQL persistence with provenance tracking
- Single-node consensus for Phase 1

**✅ SMA Validation:**
- 10 key tables operational (Phase 1 subset)
- Camera provisioning and token validation
- PASS/FAIL responses without seeing image content
- Audit logging of all validation attempts

**✅ Verification Tools:**
- Public API for hash verification
- Provenance chain queries
- Blockchain status and statistics
- Web verification interface (`packages/verifier/`)

**✅ Testing & Documentation:**
- End-to-end integration testing
- Demo script for system demonstration
- Comprehensive deployment guide
- Architecture documentation updated

### Phase 1 Limitations

**Hardware:**
- TPM hardware issue (using simulated SE in software)
- Single Raspberry Pi camera (no fleet management)

**Software:**
- Simulated SE keys stored in files (no physical tamper resistance)
- Local network only (no internet connectivity)
- Single-node blockchain (Phase 1 testnet)
- Mock provisioning (simulated manufacturing process)

**Scope:**
- Proves concept with prototype hardware
- Validates architecture and privacy design
- Ready for Phase 2 production deployment

### Ready for Phase 2

**Production Deployment:**
- Real TPM integration (hardware secure element)
- Multi-node blockchain with PoA consensus
- Internet-connected submission nodes
- Real manufacturer provisioning workflow

**Mobile Apps:**
- Android app with hardware SE
- iOS app with Secure Enclave
- Mobile-first user experience

**Production Blockchain:**
- Coalition-operated validator nodes
- Geographic distribution
- Production-grade consensus and fault tolerance
