# Mock Camera Client - Usage Guide

## Purpose

The mock camera client simulates a Raspberry Pi camera submitting 2-hash bundles to the aggregation server for testing the Week 1+2 implementation.

## Prerequisites

1. **SMA Server Running:**
   ```bash
   cd packages/sma
   python -m src.main
   # Should be running on http://localhost:8001
   ```

2. **Aggregator Server Running:**
   ```bash
   cd packages/blockchain
   alembic upgrade head  # First time only
   uvicorn src.main:app --port 8545
   # Should be running on http://localhost:8545
   ```

3. **SMA Key Tables Initialized:**
   ```bash
   cd packages/sma
   python scripts/setup_sma.py  # Creates table_id 0 and others
   ```

## Usage

### Single Capture Test

Simulates one camera capture with 2 hashes (raw + processed):

```bash
cd packages/blockchain
python scripts/mock_camera_client.py
```

**Expected Output:**
```
============================================================
MOCK CAMERA - Single Capture
============================================================

[1/4] Generating mock image hashes...
  Raw hash: abc123...
  Processed hash: def456...

[2/4] Generating mock camera token...
  Table ID: 0
  Key Index: 0
  Ciphertext: ...

[3/4] Submitting to aggregator...
✓ Submission accepted
  Receipt ID: uuid-here
  Status: pending_validation
  Raw hash: abc123...
  Processed hash: def456...

[4/4] Waiting 2 seconds for validation...

Verifying raw hash...
⚠ Hash pending validation/batching

Verifying processed hash...
⚠ Hash pending validation/batching

============================================================
CAPTURE SUMMARY
============================================================
Receipt ID: uuid-here
Raw hash verified: ⚠ Pending
Processed hash verified: ⚠ Pending
============================================================
```

### Continuous Capture (Load Testing)

Simulates multiple captures for load testing:

```bash
# Submit 10 images with 1 second interval
python scripts/mock_camera_client.py --continuous 10

# Submit 250 images with 0.1 second interval (load test)
python scripts/mock_camera_client.py --continuous 250 --interval 0.1
```

**Expected Output:**
```
============================================================
MOCK CAMERA - Continuous Capture (10 images)
============================================================

--- Capture 1/10 ---
✓ Submission accepted
  Receipt ID: ...
  ...

--- Capture 2/10 ---
✓ Submission accepted
  ...

============================================================
CONTINUOUS CAPTURE SUMMARY
============================================================
Total captures: 10
Submitted: 10
Failed: 0
Elapsed time: 12.34 seconds
Average rate: 0.81 captures/second
============================================================

⏳ Waiting 30 seconds for batching service...
```

## What It Tests

### Simulated Components

1. **Mock Image Hashes:**
   - Raw Bayer data: ~24MB random bytes → SHA-256
   - Processed JPEG: ~3MB random bytes → SHA-256
   - Different hashes each capture

2. **Mock Camera Token:**
   - Ciphertext: 128 hex chars
   - Auth tag: 32 hex chars (16 bytes)
   - Nonce: 24 hex chars (12 bytes)
   - Table ID: 0 (must exist in SMA)
   - Key index: 0

3. **2-Hash Bundle Format:**
   - Hash 1: modification_level=0, parent_image_hash=null
   - Hash 2: modification_level=1, parent_image_hash=<raw_hash>

### Validation Flow

1. Client → Aggregator: Submit 2-hash bundle
2. Aggregator → Database: Store both hashes with shared transaction_id
3. Aggregator → SMA: Validate camera token
4. SMA → Aggregator: Return PASS/FAIL
5. Aggregator → Database: Update validation status
6. Client → Aggregator: Query verification status

## Troubleshooting

### Error: "Cannot connect to aggregator"

**Solution:** Start the aggregator server:
```bash
cd packages/blockchain
uvicorn src.main:app --port 8545
```

### Error: "Submission failed: 500"

**Cause:** SMA server not running or validation failed

**Solution:** Check SMA server logs:
```bash
cd packages/sma
python -m src.main
# Look for validation errors
```

### Error: "Invalid table_id: 0"

**Cause:** SMA key tables not initialized

**Solution:** Run SMA setup script:
```bash
cd packages/sma
python scripts/setup_sma.py
```

### Status: "Hash pending validation/batching"

**Normal Behavior:** Hashes are validated but not yet batched to blockchain

**Wait Time:** Batching service runs every 30 seconds (check BATCH_INTERVAL config)

## Testing Checklist

- [ ] Single capture succeeds (202 Accepted)
- [ ] Both hashes stored in database with same transaction_id
- [ ] SMA validation called (check SMA logs)
- [ ] Verification queries return "pending" status
- [ ] After 30+ seconds, hashes batched to blockchain
- [ ] Verification queries return "verified" with block_height
- [ ] Continuous capture handles 10+ images without errors
- [ ] Load test (250 images) completes successfully

## Next Steps

After mock camera testing is successful:

1. **Week 3 Task 4:** Create load testing script (target: 250 submissions)
2. **Week 3 Task 5:** Create performance testing script
3. **Week 3 Task 6:** Document Week 3 results

## Files Modified/Created

- `packages/blockchain/scripts/mock_camera_client.py` - Main mock client
- `packages/blockchain/scripts/README_MOCK_CAMERA.md` - This file

## Phase 1 vs Real Camera

**Phase 1 (Mock):**
- Random hash generation (no real image)
- Placeholder camera tokens (no real TPM)
- SMA validates format only (no crypto decryption)

**Real Camera (Future):**
- Hash of actual raw Bayer sensor data
- Camera token encrypted with LetsTrust TPM
- SMA decrypts and validates NUC hash
- Device signature from secure element

---

**Created:** December 3, 2025
**Part of:** Week 3 Integration Testing (Task 3)
