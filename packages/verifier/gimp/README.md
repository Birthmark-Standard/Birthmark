# Birthmark GIMP Plugin

**Phase:** Phase 3 Proof of Concept
**Purpose:** Manual modification level tracking for authenticated images

## Overview

This GIMP plugin demonstrates how the Birthmark Standard tracks modifications to authenticated images through the editing workflow. It provides **manual logging** of editing operations at two levels:

- **Level 1**: Minor modifications (exposure, crop, rotation, color correction)
- **Level 2**: Heavy modifications (clone stamp, compositing, content-aware fill)

**Important:** This is a proof-of-concept with manual operation logging. Production implementations would integrate automatic tracking directly into editing software.

## Features

- Initialize tracking for Birthmark-authenticated images
- Manually log Level 1 (minor) or Level 2 (heavy) edits
- View tracking status with modification level
- Export with modification record (sidecar JSON file)
- Submit modification records to aggregation server
- Validate plugin integrity against SSA on each use

## Requirements

- **GIMP 2.10** (with Python-Fu support)
- **Python 2.7** (bundled with GIMP 2.10)
- **Running infrastructure:**
  - Blockchain aggregation server (port 8545)
  - SSA validation server (port 8002)
  - Provisioned software certificate

## Installation

### Step 1: Locate GIMP Plugins Directory

**Windows:**
```
%APPDATA%\GIMP\2.10\plug-ins\
```

**Linux:**
```
~/.config/GIMP/2.10/plug-ins/
```

**macOS:**
```
~/Library/Application Support/GIMP/2.10/plug-ins/
```

Or check in GIMP: `Edit -> Preferences -> Folders -> Plug-ins`

### Step 2: Copy Plugin File

```bash
# Copy the plugin to GIMP's plug-ins directory
cp birthmark_gimp_plugin.py <GIMP_PLUGINS_DIR>/
```

### Step 3: Make Executable (Linux/macOS only)

```bash
chmod +x <GIMP_PLUGINS_DIR>/birthmark_gimp_plugin.py
```

### Step 4: Provision the Plugin with SSA

Before the plugin can validate itself, it must be provisioned with the SSA:

```bash
# Navigate to SSA package
cd ../../ssa/

# Generate CA certificates (if not done)
python generate_ca.py

# Provision the GIMP plugin
python provision_software.py \
    --software-id "GIMP-Wrapper-POC-001" \
    --wrapper-path ../verifier/gimp/birthmark_gimp_plugin.py \
    --version "1.0.0"
```

This creates:
- `provisioned_software/gimp-wrapper-poc-001/software_certificate.pem`
- `provisioned_software/gimp-wrapper-poc-001/software_private_key.pem`
- `provisioned_software/gimp-wrapper-poc-001/certificate_chain.pem`

### Step 5: Install Certificates

Create Birthmark config directory and copy certificates:

```bash
# Create config directory
mkdir -p ~/.birthmark

# Copy certificates
cp provisioned_software/gimp-wrapper-poc-001/software_certificate.pem ~/.birthmark/
cp provisioned_software/gimp-wrapper-poc-001/software_private_key.pem ~/.birthmark/
```

### Step 6: Restart GIMP

Close and reopen GIMP to load the plugin.

### Step 7: Verify Installation

1. Open any image in GIMP
2. Look for **"Birthmark"** menu under the main menu bar
3. You should see:
   - Initialize Tracking
   - Log Level 1 Operation
   - Log Level 2 Operation
   - Show Status
   - Export with Record

## Configuration

The plugin uses environment variables for server URLs:

```bash
export BIRTHMARK_AGG_URL=http://localhost:8545
export BIRTHMARK_SSA_URL=http://localhost:8002
```

Or edit the plugin file directly to change:
- `AGGREGATION_SERVER_URL`
- `SSA_SERVER_URL`

## Usage Workflow

### 1. Start Required Services

```bash
# Terminal 1: Start blockchain aggregation server
cd packages/blockchain
uvicorn src.main:app --port 8545

# Terminal 2: Start SSA validation server
cd packages/ssa
python ssa_server.py

# Terminal 3: (Optional) Start SMA for camera authentication
cd packages/sma
uvicorn src.main:app --port 8001
```

### 2. Capture an Authenticated Image

Use the camera-pi package to capture and authenticate an image:

```bash
cd packages/camera-pi
python -m camera_pi capture --output test_image.jpg
```

This submits the image hash to the blockchain.

### 3. Open Image in GIMP

1. Open GIMP
2. Load your authenticated image
3. **Important:** Save it as XCF format first!

### 4. Initialize Tracking

1. Go to **Birthmark -> Initialize Tracking**
2. Plugin validates itself with SSA
3. Plugin checks if image is authenticated
4. Tracking parasite attached to image
5. You'll see confirmation message

### 5. Edit Your Image

Make edits using GIMP tools as normal. Examples:

**Level 1 Operations (minor):**
- Adjust exposure/brightness/contrast
- Color balance/white balance
- Crop or rotate
- Sharpening
- Noise reduction

**Level 2 Operations (heavy):**
- Clone stamp / healing brush
- Content-aware fill
- Layer compositing
- Adding/removing objects
- Text overlays

### 6. Log Operations

After making edits:

**For minor edits:**
- Go to **Birthmark -> Log Level 1 Operation**
- Modification level updates to 1

**For heavy edits:**
- Go to **Birthmark -> Log Level 2 Operation**
- Modification level updates to 2

**Note:** Levels only go up, never down:
- Level 0 → 1 (first minor edit)
- Level 1 → 2 (first heavy edit)
- Level 2 stays at 2 (sticky)

### 7. Check Status (Anytime)

- Go to **Birthmark -> Show Status**
- View current modification level
- See original hash and metadata

### 8. Export with Record

When finished editing:

1. Save your XCF file first!
2. Go to **Birthmark -> Export with Record**
3. Plugin creates sidecar JSON file
4. Plugin submits record to aggregation server
5. Sidecar saved as: `your_image.xcf.birthmark.json`

### 9. Export Final Image

Export as JPEG/PNG using **File -> Export As**

The sidecar file will remain next to your XCF file.

## Modification Level Classification

### Level 1: Minor Modifications

Standard photojournalism-compliant edits:
- Brightness/contrast adjustment
- Color balance/white balance
- Exposure correction
- Cropping (any amount)
- Rotation/flipping
- Sharpening
- Noise reduction
- Lens correction

### Level 2: Heavy Modifications

Content-altering operations:
- Clone stamp / healing brush
- Content-aware fill
- Layer compositing
- Adding/removing objects
- Text overlay
- Significant filters
- AI-powered editing tools

**When in doubt:** Log the highest level of operation performed.

## Sidecar File Format

The `.birthmark.json` sidecar file contains:

```json
{
  "original_image_hash": "abc123...",
  "final_image_hash": "def456...",
  "modification_level": 1,
  "authenticated": true,
  "original_dimensions": [4000, 3000],
  "final_dimensions": [4000, 3000],
  "software_id": "GIMP-Wrapper-POC-001",
  "plugin_version": "1.0.0",
  "initialized_at": "2025-11-15T10:00:00",
  "exported_at": "2025-11-15T10:30:00",
  "authority_type": "software"
}
```

This record proves:
- The original authenticated image
- What editing software was used
- The modification level (0, 1, or 2)
- When the edit was made

## Testing

### Test with Mock Image

You can test tracking on any image (doesn't need to be authenticated):

1. Open any JPEG in GIMP
2. Save as XCF
3. Run **Initialize Tracking**
4. It will show "NOT authenticated" but tracking still works
5. Make edits, log operations, export record

### Test with Authenticated Image

For full workflow testing:

1. Capture image with camera-pi
2. Verify it's on blockchain: `curl http://localhost:8545/api/v1/verify/{hash}`
3. Open in GIMP and track modifications
4. Export with record
5. Verify modification record on blockchain

## Troubleshooting

### "Birthmark" Menu Not Appearing

**Solutions:**
- Ensure file is executable (Linux/macOS)
- Check GIMP plugin path is correct
- Restart GIMP after installing
- Check GIMP error console: **Filters -> Python-Fu -> Console**

### "Software certificate not found"

**Error:** `ERROR: Software certificate not found at: ~/.birthmark/software_certificate.pem`

**Solution:**
1. Provision the plugin with SSA first
2. Copy certificates to `~/.birthmark/`

### "Plugin validation failed"

**Error:** `ERROR: Plugin validation failed`

**Solutions:**
- Ensure SSA server is running on port 8002
- Check plugin version matches provisioned version
- Re-provision if plugin code changed

### "Authentication check failed"

**Error:** `Authentication check failed: ...`

**Solutions:**
- Ensure blockchain aggregation server is running on port 8545
- Check server URL is correct
- Test server: `curl http://localhost:8545/health`

### "Image has not been saved yet"

**Error when exporting:** `ERROR: Image has not been saved yet`

**Solution:** Save your image as XCF first, then run Export with Record.

## Limitations (POC)

This proof-of-concept demonstrates the trust architecture but has limitations:

### Manual Logging
- User must manually invoke "Log Operation" commands
- Easy to forget or misclassify operations
- Production would track automatically

### Image Hashing
- Current hash method is simplified
- Not optimized for performance
- May not be consistent across format conversions

### Offline Operation
- Server submission may fail offline
- Sidecar file still created locally
- No automatic retry mechanism

### Security
- No runtime integrity monitoring
- No anti-tamper protections
- Plugin could be modified after provisioning (next run would fail validation)

## Production Path

This POC demonstrates the concept for partnership pitches. Production implementation would:

### Automatic Tracking
- Integrate directly into editing software
- Hook into internal tool invocation
- Track operations automatically without user intervention
- Zero manual logging required

### Better Hashing
- Consistent hash across saves/loads
- Optimized for performance
- Handle format conversions properly

### Native Integration
- Adobe Photoshop/Lightroom native plugin
- Capture One integration
- Affinity Photo support
- Seamless user experience

## API Integration

The plugin integrates with:

### SSA Validation Server (port 8002)
- **POST /api/v1/validate/software** - Validate plugin on initialization

### Blockchain Aggregation Server (port 8545)
- **GET /api/v1/verify/{hash}** - Check image authentication
- **POST /api/v1/modifications** - Submit modification record

## Development

### Updating Plugin Code

If you modify the plugin:

1. **Increment version constant:**
   ```python
   PLUGIN_VERSION = "1.0.1"
   ```

2. **Add version to SSA:**
   ```bash
   curl -X POST http://localhost:8002/api/v1/versions/add \
     -H "Content-Type: application/json" \
     -d '{"software_id": "GIMP-Wrapper-POC-001", "version": "1.0.1"}'
   ```

3. **Restart GIMP** to load updated plugin

### Testing Changes

```bash
# Copy updated plugin to GIMP
cp birthmark_gimp_plugin.py <GIMP_PLUGINS_DIR>/

# Restart GIMP
# Run Initialize Tracking to test validation
```

## Related Documentation

- Phase 3 Plan: `docs/phase-plans/Birthmark_Phase_3_Plan_Image_Editor_Wrapper_SSA.md`
- SSA Package: `packages/ssa/README.md`
- Blockchain API: `packages/blockchain/README.md`

## Support

For issues and questions, see the main Birthmark repository.

---

**Status:** Phase 3 Proof of Concept
**Purpose:** Demonstrate editing workflow provenance tracking for partnerships
**Not for production use** - Manual logging POC only
