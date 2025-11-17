# GIMP Wrapper End-to-End Testing Guide

**Phase:** Phase 3 Proof of Concept
**Last Updated:** November 2025
**Purpose:** Test complete provenance chain from camera capture through editing to verification

---

## Overview

This guide walks through testing the complete Birthmark workflow with modification tracking:

```
1. Camera Captures Photo → Authenticates on Blockchain
2. User Opens in GIMP → Initializes Tracking
3. User Edits Photo → Logs Modifications
4. User Exports → Creates Provenance Record
5. Anyone Verifies → Sees Complete Chain
```

## Prerequisites

### Hardware (Optional for Phase 1)
- Raspberry Pi 4 + HQ Camera (for real captures)
- OR mock camera mode (for testing without hardware)

### Software
- GIMP 2.10 with Python-Fu
- Python 3.10+ (for servers)
- PostgreSQL (or SQLite for dev)

### Services
All three servers must be running:
1. **SMA** (port 8001) - Validates cameras
2. **SSA** (port 8002) - Validates editing software
3. **Blockchain Node** (port 8545) - Aggregator + validator

---

## Setup

### Terminal 1: Start SMA

```bash
cd packages/sma
python generate_ca.py  # First time only
uvicorn src.main:app --port 8001 --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8001
[SMA] Loaded X key tables
```

### Terminal 2: Start SSA

```bash
cd packages/ssa
python generate_ca.py  # First time only
uvicorn src.main:app --port 8002 --reload
```

Wait - SSA uses Flask, not FastAPI:

```bash
cd packages/ssa
python generate_ca.py  # First time only
python ssa_server.py
```

**Expected output:**
```
SSA Validation Server - Running
Listening on: http://0.0.0.0:8002
[SSA] Loaded X provisioned software entries
```

### Terminal 3: Start Blockchain Node

```bash
cd packages/blockchain
# Create database if needed
alembic upgrade head

# Start server
uvicorn src.main:app --port 8545 --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8545
Starting Birthmark Blockchain Node: birthmark-node-001
Consensus mode: single_node
```

### Verify All Services Running

```bash
# Check SMA
curl http://localhost:8001/health

# Check SSA
curl http://localhost:8002/health

# Check Blockchain
curl http://localhost:8545/api/v1/status
```

All should return healthy responses.

---

## Part 1: Provision GIMP Plugin

The GIMP plugin must be provisioned with SSA before it can validate itself.

### Step 1: Provision Plugin with SSA

```bash
cd packages/ssa

python provision_software.py \
    --software-id "GIMP-Wrapper-POC-001" \
    --wrapper-path ../verifier/gimp/birthmark_gimp_plugin.py \
    --version "1.0.0"
```

**Expected output:**
```
[SSA] Provisioning software: GIMP-Wrapper-POC-001
[SSA] Computing wrapper baseline hash...
[SSA]   Baseline hash: abc123...def456
[SSA] Computing versioned hash for v1.0.0...
[SSA]   Versioned hash: 789abc...012def
[SSA] Generating software keypair...
[SSA] Creating software certificate...
[SSA] Saving provisioning data...
[SSA] Provisioning complete!
```

This creates:
- `provisioned_software/gimp-wrapper-poc-001/software_certificate.pem`
- `provisioned_software/gimp-wrapper-poc-001/software_private_key.pem`
- `provisioned_software/gimp-wrapper-poc-001/certificate_chain.pem`
- `provisioned_software/gimp-wrapper-poc-001/provisioning_data.json`

### Step 2: Install Certificates for GIMP

```bash
# Create Birthmark config directory
mkdir -p ~/.birthmark

# Copy certificates
cp provisioned_software/gimp-wrapper-poc-001/software_certificate.pem ~/.birthmark/
cp provisioned_software/gimp-wrapper-poc-001/software_private_key.pem ~/.birthmark/
```

### Step 3: Install GIMP Plugin

```bash
# Find GIMP plugins directory
# Linux: ~/.config/GIMP/2.10/plug-ins/
# Windows: %APPDATA%\GIMP\2.10\plug-ins\
# macOS: ~/Library/Application Support/GIMP/2.10/plug-ins/

# Copy plugin
cp ../verifier/gimp/birthmark_gimp_plugin.py ~/.config/GIMP/2.10/plug-ins/

# Make executable (Linux/macOS)
chmod +x ~/.config/GIMP/2.10/plug-ins/birthmark_gimp_plugin.py
```

### Step 4: Verify Plugin Installation

1. Start GIMP
2. Open any image
3. Look for **"Birthmark"** menu
4. You should see:
   - Initialize Tracking
   - Log Level 1 Operation
   - Log Level 2 Operation
   - Show Status
   - Export with Record

If menu doesn't appear:
- Check **Filters → Python-Fu → Console** for errors
- Ensure file is executable
- Restart GIMP

---

## Part 2: Capture Authenticated Image

### Option A: With Real Raspberry Pi Camera

```bash
cd packages/camera-pi

# Provision camera (first time only)
# Copy provisioning.json from SMA

# Capture with certificate format
python -m camera_pi capture \
    --use-certificates \
    --output test_capture.jpg
```

**Expected output:**
```
[Camera] Capturing image...
[Camera] Computing hash...
[Camera] Image hash: abc123...
[Camera] Submitting to blockchain...
[Aggregation] Submission accepted
[Camera] Photo saved: test_capture.jpg
```

### Option B: With Mock Camera (No Hardware)

```bash
cd packages/camera-pi

python -m camera_pi capture \
    --use-mock-camera \
    --use-certificates \
    --output test_capture.jpg
```

### Verify Image is Authenticated

```bash
# Get image hash
IMAGE_HASH=$(sha256sum test_capture.jpg | cut -d' ' -f1)

# Query blockchain
curl http://localhost:8545/api/v1/verify/$IMAGE_HASH
```

**Expected response:**
```json
{
  "verified": true,
  "image_hash": "abc123...",
  "timestamp": 1700000000,
  "block_height": 1,
  "aggregator": "birthmark-node-001"
}
```

---

## Part 3: Edit in GIMP with Tracking

### Step 1: Open Image in GIMP

1. Start GIMP
2. **File → Open** → Select `test_capture.jpg`
3. **File → Save As...** → Save as `test_image.xcf` (XCF format required for parasites)

### Step 2: Initialize Tracking

1. Go to **Birthmark → Initialize Tracking**
2. Plugin validates itself with SSA (takes a few seconds)
3. Plugin checks if image is authenticated
4. You should see:

```
Birthmark tracking initialized!

Image authenticated: YES
Current modification level: 0 (unmodified)

Use 'Log Level 1 Operation' or 'Log Level 2 Operation'
after making edits.
```

If you see "NOT authenticated" - the image wasn't found on blockchain. Check that capture succeeded.

### Step 3: Make Minor Edits (Level 1)

Make some minor adjustments:
- **Colors → Brightness-Contrast** - Adjust as needed
- **Colors → Hue-Saturation** - Adjust colors
- **Image → Crop to Selection** - Crop if desired

### Step 4: Log Level 1 Operation

After making minor edits:
1. Go to **Birthmark → Log Level 1 Operation**
2. You should see:

```
Modification level updated: 0 → 1

Image now marked as having minor modifications.
```

### Step 5: Make Heavy Edits (Level 2)

Now make a content-altering edit:
- Use **Clone tool** to remove or duplicate something
- Or use **Filters → Enhance → Sharpen** heavily
- Or add text with **Text Tool**

### Step 6: Log Level 2 Operation

After making heavy edits:
1. Go to **Birthmark → Log Level 2 Operation**
2. You should see:

```
Modification level updated: 1 → 2

Image now marked as having heavy modifications.
```

### Step 7: Check Status

At any time, check tracking status:
1. Go to **Birthmark → Show Status**
2. You should see:

```
Birthmark Tracking Status
==========================

Status: ACTIVE
Authenticated: YES
Modification Level: 2 (Heavy Modifications)
Software ID: GIMP-Wrapper-POC-001
Plugin Version: 1.0.0
Original Hash: abc123...
Initialized: 2025-11-15T10:00:00
Original Size: 4056x3040
```

---

## Part 4: Export with Modification Record

### Step 1: Export Record

1. Make sure you've saved your XCF file
2. Go to **Birthmark → Export with Record**
3. Plugin creates sidecar and submits to blockchain
4. You should see:

```
Birthmark Export Complete!
==========================

Modification Level: 2
Authenticated: YES
Sidecar File: /path/to/test_image.xcf.birthmark.json
Server Status: recorded

The modification record has been saved and submitted.
```

If you see "Offline" - blockchain server isn't running, but sidecar file is still created.

### Step 2: Verify Sidecar File Created

```bash
# Check sidecar file exists
cat test_image.xcf.birthmark.json
```

**Expected content:**
```json
{
  "original_image_hash": "abc123...",
  "final_image_hash": "def456...",
  "modification_level": 2,
  "authenticated": true,
  "original_dimensions": [4056, 3040],
  "final_dimensions": [4056, 3040],
  "software_id": "GIMP-Wrapper-POC-001",
  "plugin_version": "1.0.0",
  "initialized_at": "2025-11-15T10:00:00",
  "exported_at": "2025-11-15T10:30:00",
  "authority_type": "software"
}
```

### Step 3: Export Final Image

Now export your edited image as JPEG:
1. **File → Export As...**
2. Choose name: `test_image_edited.jpg`
3. Export as JPEG

You now have:
- `test_image.xcf` - GIMP file with tracking parasite
- `test_image.xcf.birthmark.json` - Modification record
- `test_image_edited.jpg` - Final exported image

---

## Part 5: Verify Complete Provenance Chain

### Query Modification Record

```bash
# Get final image hash
FINAL_HASH=$(sha256sum test_image_edited.jpg | cut -d' ' -f1)

# Query provenance chain
curl http://localhost:8545/api/v1/provenance/$FINAL_HASH
```

**Expected response:**
```json
{
  "image_hash": "def456...",
  "verified": true,
  "chain": [
    {
      "hash": "abc123...",
      "type": "capture",
      "timestamp": "2025-11-15T09:00:00",
      "authority_type": "manufacturer",
      "authority_id": "birthmark-node-001",
      "modification_level": 0
    },
    {
      "hash": "def456...",
      "type": "modification",
      "timestamp": "2025-11-15T10:30:00",
      "authority_type": "software",
      "authority_id": "GIMP-Wrapper-POC-001",
      "modification_level": 2,
      "software_version": "1.0.0"
    }
  ],
  "chain_length": 2
}
```

This proves:
- ✅ Original image was captured by authenticated camera
- ✅ Image was edited with certified software
- ✅ Modification level was 2 (heavy)
- ✅ Complete timeline from capture to final export

### Query Modification History

```bash
# Query all modifications of original image
curl http://localhost:8545/api/v1/modifications/$ORIGINAL_HASH
```

Shows all editing versions created from this original.

---

## Testing Scenarios

### Scenario 1: Unmodified Image (Level 0)

1. Capture image
2. Open in GIMP, initialize tracking
3. Don't make any edits
4. Export with record
5. Verification shows: modification_level = 0

### Scenario 2: Minor Edits Only (Level 1)

1. Capture image
2. Open in GIMP, initialize tracking
3. Adjust brightness/contrast only
4. Log Level 1 Operation
5. Export with record
6. Verification shows: modification_level = 1

### Scenario 3: Heavy Edits (Level 2)

1. Capture image
2. Open in GIMP, initialize tracking
3. Use clone stamp to remove object
4. Log Level 2 Operation
5. Export with record
6. Verification shows: modification_level = 2

### Scenario 4: Sticky Levels

1. Capture image
2. Open in GIMP, initialize tracking (Level 0)
3. Crop image, log Level 1 (Level 0 → 1)
4. Use clone stamp, log Level 2 (Level 1 → 2)
5. Adjust brightness, log Level 1 (Level 2 stays 2)
6. Verify: Final level is 2 (levels never go down)

### Scenario 5: Non-Authenticated Image

1. Open any random JPEG (not from camera)
2. Initialize tracking
3. Shows: "Image authenticated: NO"
4. Can still track modifications
5. But provenance chain shows verified=false

### Scenario 6: Multiple Edits Chain

1. Capture image A (authenticated)
2. Edit in GIMP → Export as B (modification_level=1)
3. Open B in GIMP, initialize tracking
4. Edit more → Export as C (modification_level=2)
5. Query C provenance: Shows A → B → C chain

---

## Troubleshooting

### Plugin Validation Fails

**Error:** `ERROR: Plugin validation failed`

**Causes:**
- SSA server not running
- Plugin code was modified after provisioning
- Version mismatch

**Solutions:**
```bash
# Check SSA is running
curl http://localhost:8002/health

# Re-provision if plugin was modified
cd packages/ssa
python provision_software.py \
    --software-id "GIMP-Wrapper-POC-001" \
    --wrapper-path ../verifier/gimp/birthmark_gimp_plugin.py \
    --version "1.0.0"

# Copy new certificates
cp provisioned_software/gimp-wrapper-poc-001/*.pem ~/.birthmark/
```

### Authentication Check Fails

**Error:** `Authentication check failed: ...`

**Causes:**
- Blockchain server not running
- Image wasn't actually captured/authenticated

**Solutions:**
```bash
# Check blockchain is running
curl http://localhost:8545/api/v1/status

# Verify image is on blockchain
IMAGE_HASH=$(sha256sum test_capture.jpg | cut -d' ' -f1)
curl http://localhost:8545/api/v1/verify/$IMAGE_HASH
```

### Modification Record Submission Fails

**Error:** `Could not submit to server: ...`

**This is OK!** The sidecar file is still created locally. You can:
- Submit it later when server is online
- Or just keep the sidecar file as offline proof

### Image Hash Mismatch

**Problem:** Verification fails even though image was captured

**Cause:** Image was re-encoded, changing the hash

**Solution:** Use the original capture file, not a re-saved version. If you must edit, use XCF format in GIMP (preserves quality), then export final version once.

---

## Success Criteria

After following this guide, you should have:

- ✅ All three servers running and healthy
- ✅ GIMP plugin installed and validating
- ✅ Authenticated image captured on blockchain
- ✅ Image opened in GIMP with tracking initialized
- ✅ Modifications logged at correct levels
- ✅ Modification record exported and submitted
- ✅ Complete provenance chain queryable via API
- ✅ Sidecar JSON file with modification metadata

##Phase 3 POC Limitations

This proof of concept demonstrates the architecture but has limitations:

### Manual Logging
- User must remember to log operations
- Easy to misclassify or forget
- Production would track automatically

### Simplified Hashing
- Current hashing is not optimized
- May not be consistent across saves
- Production would use robust hashing

### No SSA Validation Yet
- Blockchain accepts all modification records
- TODO: Add certificate validation with SSA
- Production would validate every submission

### Single Plugin Only
- Only GIMP plugin implemented
- Production would support multiple editors
- Each with their own SSA certificate

---

## Next Steps

After successful testing:

1. **Gather Feedback:** How intuitive is the workflow?
2. **Test Edge Cases:** Multiple edits, large files, offline mode
3. **Document Issues:** What breaks? What's confusing?
4. **Prepare Demos:** Screenshots and screen recordings for partnership pitches
5. **Write Phase 3 Report:** Performance, usability, limitations

---

**Testing Complete!** You've verified the complete Birthmark provenance chain from authenticated camera capture through certified editing software to final verification.

This demonstrates the full lifecycle authentication story for partnership demonstrations.
