# Birthmark Phase 1 Demo Guide

Complete end-to-end demonstration of the Birthmark authentication pipeline.

## System Components

1. **SMA (Simulated Manufacturer Authority)** - Validates camera tokens
2. **Blockchain Node** - Combined submission server + blockchain storage
3. **Demo Script** - Simulates camera and runs end-to-end test

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

```
┌─────────────┐
│   Camera    │  Captures image + generates token
│  (Demo)     │
└──────┬──────┘
       │ POST /api/v1/submit
       ▼
┌─────────────────┐
│  Blockchain     │  Receives submission
│  Node           │
│  (Port 8545)    │
└──────┬──────────┘
       │ POST /validate
       ▼
┌─────────────────┐
│  SMA            │  Validates camera token
│  (Port 8001)    │  Returns PASS/FAIL
└─────────────────┘
       │
       ▼ (if PASS)
┌─────────────────┐
│  Blockchain     │  Stores hash + metadata
│  Database       │  (PostgreSQL)
└─────────────────┘
```

## Phase 1 Complete ✅

You now have a working end-to-end Birthmark authentication system demonstrating:
- Camera token generation and encryption
- Submission server intake
- SMA validation without seeing image hashes
- Blockchain storage with provenance tracking
- Public verification queries

**Ready for Phase 2:** Real camera integration on Raspberry Pi
