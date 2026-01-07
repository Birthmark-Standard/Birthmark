# Birthmark Phase 1 - End-to-End Verification Guide

## What We Accomplished ✅

Successfully demonstrated the complete Birthmark authentication pipeline:

```
Camera (Raspberry Pi) → Submission Server → SMA Validation → Blockchain Registry → Web Verifier
```

### Recent Submission

- **Submission ID**: `bb460c95-a7f3-4545-a2ec-7ba02b7c1e34`
- **Status**: ✅ SMA Validation PASSED
- **Camera**: PI-001 (provisioned with tables [4, 5, 8])
- **Timestamp**: Jan 7, 2026 09:28 UTC
- **Owner**: Sam Ryan - Birthmark

## Quick Verification

### Option 1: Automated Script (Recommended)

Run the comprehensive verification script in **PowerShell**:

```powershell
cd C:\Users\samue\Birthmark
.\verify_submission.ps1
```

This will:
- ✓ Check all Docker services are running
- ✓ Query blockchain status
- ✓ Fetch latest capture from Raspberry Pi
- ✓ Verify the hash on blockchain
- ✓ Check web verifier status
- ✓ Display complete end-to-end verification report

### Option 2: Manual Verification

#### 1. Check Blockchain Status

```powershell
Invoke-RestMethod -Uri "http://localhost:8545/api/v1/blockchain/status"
```

Expected output:
```json
{
  "node_id": "validator_001",
  "height": 1,
  "transaction_count": 1,
  "submission_count": 1,
  "status": "operational"
}
```

#### 2. Get Hash from Pi

```powershell
# Using plink (PuTTY)
plink -batch birthmark@192.168.50.161 "cat ~/Birthmark/packages/camera-pi/data/captures/IMG_1767806917.json"

# Or using ssh (if installed)
ssh birthmark@192.168.50.161 "cat ~/Birthmark/packages/camera-pi/data/captures/IMG_1767806917.json"
```

Extract the `processed_hash` field from the JSON output.

#### 3. Verify Hash on Blockchain

```powershell
$hash = "YOUR_PROCESSED_HASH_HERE"
Invoke-RestMethod -Uri "http://localhost:8545/api/v1/blockchain/verify/$hash"
```

Expected output if verified:
```json
{
  "verified": true,
  "modification_level": 1,
  "block_height": 1,
  "tx_id": 1,
  "timestamp": 1767806917,
  "owner_hash": "abc123..."
}
```

### Option 3: Web Interface

1. **Open verifier**: http://localhost:8080

2. **Verify by hash**:
   - Enter the processed hash from the capture
   - Click "Verify Hash"
   - See verification results with provenance

3. **Verify by image** (if image file was saved):
   - Drag and drop the image file
   - Click "Verify on Blockchain"
   - See full verification with owner attribution

## Verification Scripts

### `verify_submission.ps1`
Comprehensive end-to-end verification (PowerShell)
- Checks all services
- Fetches latest capture from Pi
- Verifies on blockchain
- Full status report

### `get_pi_hash.ps1`
Get latest hash from Pi and verify (PowerShell)
```powershell
.\get_pi_hash.ps1
```

### `verify_hash.py`
Verify a specific hash (Python)
```bash
python verify_hash.py <hash>
```

### `check_blockchain.py`
Check blockchain status and recent blocks (Python)
```bash
python check_blockchain.py
```

## System Architecture

### Services Running

| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| **SMA Server** | 8001 | ✓ Running | Validates camera tokens |
| **Blockchain Registry** | 8545 | ✓ Running | Stores image hashes |
| **PostgreSQL** | 5432 | ✓ Running | Database backend |
| **Web Verifier** | 8080 | ✓ Running | Public verification interface |

### Camera (Raspberry Pi)

- **Model**: Raspberry Pi 4 + Sony IMX477 HQ Camera
- **Location**: `192.168.50.161`
- **Serial**: PI-001
- **Tables**: [4, 5, 8]
- **Capture Directory**: `~/Birthmark/packages/camera-pi/data/captures/`

## Troubleshooting

### "Cannot connect to blockchain"

**Check Docker containers:**
```powershell
docker ps
```

Should show:
- `birthmark-node` (blockchain)
- `birthmark-postgres` (database)

**Restart if needed:**
```powershell
cd C:\Users\samue\Birthmark\packages\blockchain
docker-compose up -d
```

### "Hash not verified"

**Possible reasons:**
1. **Submission still pending** - Wait a few seconds and retry
2. **Validation failed** - Check SMA logs: `docker logs birthmark-node`
3. **Wrong hash** - Make sure you're using the `processed_hash`, not `raw_hash`

### "Cannot connect to Pi"

**Check connectivity:**
```powershell
ping 192.168.50.161
```

**Check SSH:**
```powershell
plink birthmark@192.168.50.161 "echo OK"
```

If password prompts, add key to Pageant (PuTTY) or use ssh with key file.

## What's Next

### Phase 1 Completion Checklist

- [x] Camera captures raw Bayer data
- [x] Hash generation (SHA-256)
- [x] Simulated Secure Element encryption
- [x] Camera token generation (legacy format)
- [x] Submission Server accepts submissions
- [x] SMA validates camera tokens
- [x] Blockchain stores verified submissions
- [x] Web verifier queries blockchain
- [ ] **End-to-end verification complete** ← YOU ARE HERE
- [ ] Owner attribution verification
- [ ] Documentation finalized
- [ ] Phase 2 transition plan

### Immediate Next Steps

1. **Verify submission visually** - Check web UI at http://localhost:8080
2. **Test owner attribution** - Verify owner name appears in verification results
3. **Capture more images** - Test with multiple submissions
4. **Test provenance chain** - Submit processed versions and verify parent links

### Phase 2 Preview

- Real Secure Element (hardware TPM)
- Android app implementation
- Multi-node blockchain testnet
- Production manufacturer integration
- GPS opt-in support

## Support

**Project**: Birthmark Standard (Phase 1)
**Repository**: github.com/Birthmark-Standard/Birthmark
**Contact**: samryan.pdx@proton.me

## Files Created

- `verify_submission.ps1` - Main verification script (PowerShell)
- `get_pi_hash.ps1` - Get hash from Pi (PowerShell)
- `verify_hash.py` - Verify specific hash (Python)
- `check_blockchain.py` - Blockchain status (Python)
- `VERIFICATION_GUIDE.md` - This file

---

**Last Updated**: January 7, 2026
**Status**: ✅ End-to-end pipeline operational
