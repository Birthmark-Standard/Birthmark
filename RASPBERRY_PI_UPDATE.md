# Raspberry Pi Update Guide - Owner Authentication Feature

## Prerequisites
- PowerShell or SSH access to your Raspberry Pi
- Git repository already cloned on the Pi

## Step 1: Connect to Raspberry Pi

```powershell
# From your Windows machine, connect via SSH
ssh pi@<your-pi-ip-address>
# Example: ssh pi@192.168.1.100

# Or if you're using a different username:
ssh <username>@<your-pi-ip-address>
```

## Step 2: Navigate to Birthmark Directory

```bash
cd /home/pi/Birthmark
# Or wherever you cloned the repository
```

## Step 3: Pull Latest Code

```bash
# Fetch the latest changes
git fetch origin

# Checkout the owner authentication branch
git checkout claude/add-owner-authentication-UpR2v

# Pull the latest changes
git pull origin claude/add-owner-authentication-UpR2v
```

**Expected Output:**
```
Switched to branch 'claude/add-owner-authentication-UpR2v'
Updating c52554b..xxxxxxx
Fast-forward
 packages/camera-pi/src/camera_pi/config.py              | 155 +++++++++++++++++++
 packages/camera-pi/src/camera_pi/main.py                |  45 ++++--
 packages/camera-pi/src/camera_pi/owner_attribution.py   | 245 +++++++++++++++++++++++++++++
 packages/camera-pi/src/camera_pi/submission_client.py   |  12 +-
 4 files changed, 445 insertions(+), 12 deletions(-)
```

## Step 4: (Optional) Install EXIF Libraries

**Only needed if you want to save JPEG/PNG files with embedded owner metadata. Skip if you only save JSON metadata.**

```bash
# Install EXIF writing libraries (optional)
pip3 install piexif pillow
```

**Note:** If you skip this, the system still works perfectly - it just won't write EXIF metadata to image files. Owner attribution will still be saved in the JSON metadata and submitted to the blockchain.

## Step 5: Verify Installation

```bash
# Test that the new modules import correctly
python3 -c "from camera_pi.config import CameraConfig; from camera_pi.owner_attribution import generate_owner_metadata; print('✓ Modules loaded successfully')"
```

**Expected Output:**
```
✓ Modules loaded successfully
```

## Step 6: Test Camera (Without Owner Attribution)

```bash
# Navigate to camera package
cd packages/camera-pi

# Test capture with mock camera (owner attribution is disabled by default)
python3 -m camera_pi capture --use-certificates --mock
```

**Expected Output:**
```
Loading provisioning data...
✓ Device: <your-device-serial>

Initializing camera components...
ℹ Owner attribution disabled
✓ Camera initialized

=== Capture #1 ===
ISP parameters: WB(R:1.25, B:1.15), Exp:+0.0, Sharp:0.5, NR:0.3
✓ Mock capture: (3040, 4056) in 0.015s
✓ Hash computed: <hash>... in 0.089s
✓ Mock processed capture: (3040, 4056, 3)
✓ Processed hash: <hash>...
✓ ISP variance: 0.0234
✓ Using embedded certificate (no token generation needed)
✓ Certificate bundle created (variance: 0.0234)
✓ Saved: IMG_<timestamp>.json
✓ Total time: 0.512s
```

## Step 7: (Optional) Configure Owner Attribution

**Only if you want to enable the owner attribution feature:**

```bash
# Run interactive configuration
python3 -m camera_pi.config
```

**Interactive Prompts:**
```
=== Owner Attribution Configuration ===

Owner attribution allows you to include verifiable attribution
in your photos using a hash-based system.

⚠ PRIVACY NOTE:
  - Owner name and random salt are stored in image EXIF
  - Only a hash of (name + salt) is stored on blockchain
  - Each photo gets a unique hash (even from same owner)
  - Blockchain records cannot be correlated without the image file

Enable owner attribution? (y/n):
```

**Type `y` and press Enter, then:**

```
Enter owner name/identifier. This can be:
  - Your name (e.g., 'Jane Smith')
  - Email (e.g., 'jane@example.com')
  - Organization + name (e.g., 'Jane Smith - Reuters')

Owner name:
```

**Type your name/identifier and press Enter.**

**Expected Output:**
```
✓ Owner attribution enabled
  Owner name: <your-name>

All future photos will include owner attribution.
You can change this anytime by running this configuration again.
```

## Step 8: Test Capture With Owner Attribution

**Only if you enabled owner attribution in Step 7:**

```bash
# Test capture with owner attribution enabled
python3 -m camera_pi capture --use-certificates --mock
```

**Expected Output:**
```
Loading provisioning data...
✓ Device: <your-device-serial>

Initializing camera components...
✓ Owner attribution enabled: <your-name>
✓ Camera initialized

=== Capture #1 ===
ISP parameters: WB(R:1.25, B:1.15), Exp:+0.0, Sharp:0.5, NR:0.3
✓ Mock capture: (3040, 4056) in 0.015s
✓ Hash computed: <hash>... in 0.089s
✓ Mock processed capture: (3040, 4056, 3)
✓ Processed hash: <hash>...
✓ ISP variance: 0.0234
✓ Owner attribution: <your-name>...                    <-- NEW LINE
✓ Using embedded certificate (no token generation needed)
✓ Certificate bundle created (variance: 0.0234)
✓ Saved: IMG_<timestamp>.json
✓ Total time: 0.512s
```

## Step 9: Check Saved Metadata

```bash
# View the saved metadata to see owner attribution
cat data/captures/IMG_*.json | tail -20
```

**If owner attribution is enabled, you'll see:**
```json
{
  "image_hash": "...",
  "timestamp": 1699564800,
  "device_serial": "...",
  "bundle": {...},
  "owner_attribution": {
    "owner_name": "<your-name>",
    "owner_salt_b64": "aGVsbG8gd29ybGQ...",
    "owner_hash": "7b2r4s91f3a8d6c2..."
  }
}
```

## Step 10: (Optional) Disable Owner Attribution

**If you want to disable owner attribution later:**

```bash
# Run configuration again
python3 -m camera_pi.config
```

**When prompted, type `n` to disable:**
```
Enable owner attribution? (y/n): n

✓ Owner attribution disabled
Photos will not include owner attribution.
```

## Configuration File Location

The owner attribution settings are stored in:
```
/home/pi/Birthmark/packages/camera-pi/data/camera_config.json
```

You can also edit this file directly:

```bash
# View current configuration
cat data/camera_config.json
```

**Example configuration file:**
```json
{
  "owner_attribution": {
    "enabled": true,
    "owner_name": "Jane Smith - Reuters"
  }
}
```

## Troubleshooting

### Issue: "Module not found" error

```bash
# Make sure you're in the right directory
cd /home/pi/Birthmark/packages/camera-pi

# Reinstall the package in development mode
pip3 install -e .
```

### Issue: Git conflicts when pulling

```bash
# If you have local changes that conflict
git stash
git pull origin claude/add-owner-authentication-UpR2v
git stash pop
```

### Issue: Permission denied

```bash
# Make sure you have write permissions
sudo chown -R pi:pi /home/pi/Birthmark
```

### Issue: Camera not working

```bash
# Test with mock camera first
python3 -m camera_pi capture --use-certificates --mock

# If mock works but real camera doesn't, check camera connection
vcgencmd get_camera
```

## Summary of Changes

**No breaking changes - existing workflows continue to work exactly as before.**

### New Files Added:
- `packages/camera-pi/src/camera_pi/config.py` - Configuration system
- `packages/camera-pi/src/camera_pi/owner_attribution.py` - Owner attribution logic

### Modified Files:
- `packages/camera-pi/src/camera_pi/main.py` - Integrated owner attribution
- `packages/camera-pi/src/camera_pi/submission_client.py` - Added owner_hash field

### Key Points:
✅ Owner attribution is **disabled by default**
✅ No new dependencies required (piexif/pillow are optional)
✅ Backward compatible - all existing code works unchanged
✅ Configuration is per-device (stored in `data/camera_config.json`)
✅ Can be enabled/disabled anytime without affecting existing photos

## Quick Command Reference

```bash
# Pull latest code
cd /home/pi/Birthmark && git checkout claude/add-owner-authentication-UpR2v && git pull

# Configure owner attribution
cd packages/camera-pi && python3 -m camera_pi.config

# Test capture (mock camera)
python3 -m camera_pi capture --use-certificates --mock

# Test capture (real camera)
python3 -m camera_pi capture --use-certificates

# View configuration
cat data/camera_config.json

# View saved metadata
cat data/captures/IMG_*.json | tail -20
```

## Done!

Your Raspberry Pi is now updated with the owner authentication feature. The system will work exactly as before unless you choose to enable owner attribution through the configuration.
