# Birthmark GIMP Plugin - User Guide

This guide explains how to use the Birthmark modification tracking plugin for GIMP 2.10.

## Overview

The Birthmark GIMP plugin tracks modification levels for authenticated images. It helps maintain provenance by recording what level of editing was performed:

- **Level 0**: Unmodified original (authenticated from camera)
- **Level 1**: Minor modifications (exposure, crop, color correction)
- **Level 2**: Heavy modifications (cloning, compositing, content-aware edits)

**Important:** This is a **proof of concept** with **manual operation logging**. You must manually log operations after performing them. In production, editing software would track operations automatically.

## Prerequisites

Before using the plugin:

1. ✅ Plugin is installed (see [install.md](install.md))
2. ✅ Aggregation server is running and accessible
3. ✅ SSA validation server is running and accessible
4. ✅ Software certificates are in `~/.birthmark/` directory
5. ✅ You have Birthmark-authenticated images to edit

## Menu Overview

The plugin adds a **Birthmark** menu to GIMP with five functions:

| Menu Item | Shortcut | Purpose |
|-----------|----------|---------|
| Initialize Tracking | None | Start tracking modifications for an authenticated image |
| Log Level 1 Operation | None | Record that you performed minor edits |
| Log Level 2 Operation | None | Record that you performed heavy edits |
| Show Status | None | View current tracking information |
| Export with Record | None | Create sidecar file and submit to server |

## Complete Workflow

### Step 1: Open an Authenticated Image

1. Open GIMP
2. **File → Open**
3. Select a Birthmark-authenticated image
   - This should be an image captured with a Birthmark-enabled camera
   - Or an image that was previously authenticated via the aggregation server

### Step 2: Initialize Tracking

1. **Birthmark → Initialize Tracking**
2. The plugin will:
   - Validate its own certificate with the SSA server ✓
   - Compute a hash of the current image ✓
   - Check if the image is authenticated via the aggregation server ✓
   - Attach tracking data to the image (stored in GIMP parasite) ✓

**Success message:**
```
Birthmark tracking initialized!

Image authenticated: YES
Current modification level: 0 (unmodified)

Use 'Log Level 1 Operation' or 'Log Level 2 Operation'
after making edits.
```

**If the image is not authenticated:**
```
Image is NOT authenticated.

Tracking will remain dormant.

Only Birthmark-authenticated images can be tracked.
```

**If already initialized:**
```
Tracking already initialized for this image.

Current level: 0
```

### Step 3: Edit the Image

Make your desired edits using GIMP's tools:

**Level 1 operations** (minor):
- Colors → Curves, Levels, Brightness-Contrast
- Colors → Hue-Saturation, Color Balance
- Image → Crop to Selection
- Image → Transform → Rotate, Flip
- Filters → Enhance → Sharpen, Unsharp Mask
- Filters → Enhance → Noise Reduction

**Level 2 operations** (heavy):
- Clone Tool, Healing Tool
- Filters → Enhance → Despeckle (content-aware)
- Layer compositing (multiple layers with blending)
- Adding text, shapes, or new content
- Filters that significantly alter appearance

See the [Level Classification Guide](level_classification.md) for detailed categorization.

### Step 4: Log Operations

**After performing edits**, manually log the highest level operation you used:

#### For Minor Edits (Level 1)

1. **Birthmark → Log Level 1 Operation**

**Messages:**
- If at Level 0: `Modification level updated: 0 -> 1`
- If already at Level 1: `Modification level remains: 1`
- If at Level 2: `Cannot reduce from Level 2`

#### For Heavy Edits (Level 2)

1. **Birthmark → Log Level 2 Operation**

**Messages:**
- If at Level 0 or 1: `Modification level updated: {current} -> 2`
- If already at Level 2: `Modification level remains: 2`

**Important:** Modification levels are **sticky upward only**:
- Level 0 can become Level 1 or 2
- Level 1 can become Level 2
- Level 2 cannot go back down

### Step 5: Check Status (Optional)

At any time, view the current tracking status:

1. **Birthmark → Show Status**

**Example output:**
```
Birthmark Tracking Status
==========================

Status: ACTIVE
Modification Level: 1 (Minor Modifications)
Software ID: GIMP-Wrapper-POC-001
Original Hash: a1b2c3d4e5f6g7h8...
Initialized: 2025-11-16T10:30:00.000Z
Original Size: 4056x3040
```

### Step 6: Save Your Work

Save the image in XCF format to preserve tracking data:

1. **File → Save As** (or Ctrl+Shift+E)
2. Choose **XCF** format
3. Save the file

**Important:** Tracking data is stored in GIMP parasites, which only persist in XCF format. If you export to JPEG/PNG without using "Export with Record" first, the tracking data will be lost from the exported file.

### Step 7: Export with Record

When you're ready to export the final image with its modification record:

1. **Birthmark → Export with Record**
2. If prompted, provide a filepath (or leave blank to use current file)
3. The plugin will:
   - Compute the final image hash ✓
   - Create a modification record ✓
   - Save a sidecar JSON file (`.birthmark.json`) ✓
   - Submit the record to the aggregation server ✓

**Success message (online):**
```
Birthmark Export Complete!
==========================

Modification Level: 1
Sidecar File: /path/to/image.xcf.birthmark.json
Server Status: recorded
Chain ID: abc123...
```

**Success message (offline):**
```
Birthmark Export Complete (Offline)
====================================

Modification Level: 1
Sidecar File: /path/to/image.xcf.birthmark.json

WARNING: Could not submit to server: [Errno 10061] Connection refused

Record saved locally only.
```

### Step 8: Export the Image

Now export the image in your desired format:

1. **File → Export As** (or Ctrl+Shift+E)
2. Choose format (JPEG, PNG, etc.)
3. Export the file

The sidecar `.birthmark.json` file will remain alongside your XCF file, documenting the modification history.

## Sidecar File Format

The `.birthmark.json` file contains:

```json
{
  "original_image_hash": "abc123...",
  "final_image_hash": "def456...",
  "modification_level": 1,
  "original_dimensions": [4056, 3040],
  "final_dimensions": [4056, 3040],
  "software_id": "GIMP-Wrapper-POC-001",
  "timestamp": "2025-11-16T10:45:00.000Z",
  "authority_type": "software",
  "plugin_version": "1.0.0"
}
```

This record can be:
- Verified against the blockchain via the aggregation server
- Shared with viewers to prove the modification level
- Used for provenance auditing

## Common Workflows

### Workflow 1: Quick Crop and Color Correction

1. Open authenticated image
2. **Birthmark → Initialize Tracking**
3. Crop to desired framing
4. Adjust exposure and white balance
5. **Birthmark → Log Level 1 Operation**
6. **File → Save As** (XCF)
7. **Birthmark → Export with Record**
8. **File → Export As** (JPEG)

**Result:** Image marked as Level 1 (Minor Modifications)

### Workflow 2: Photojournalism Edit

1. Open authenticated image
2. **Birthmark → Initialize Tracking**
3. Straighten horizon (rotate)
4. Adjust brightness/contrast
5. **Birthmark → Log Level 1 Operation**
6. Sharpen for print
7. **File → Save As** (XCF)
8. **Birthmark → Export with Record**
9. **File → Export As** (JPEG)

**Result:** Image marked as Level 1 (compliant with photojournalism standards)

### Workflow 3: Creative Composite

1. Open authenticated image
2. **Birthmark → Initialize Tracking**
3. Create multiple layers
4. Use clone tool to remove distractions
5. **Birthmark → Log Level 2 Operation**
6. Composite with another image
7. **File → Save As** (XCF)
8. **Birthmark → Export with Record**
9. **File → Export As** (JPEG)

**Result:** Image marked as Level 2 (Heavy Modifications)

### Workflow 4: Multi-Session Editing

**Day 1:**
1. Open authenticated image
2. **Birthmark → Initialize Tracking**
3. Basic color correction
4. **Birthmark → Log Level 1 Operation**
5. **File → Save As** (XCF)

**Day 2:**
1. Open saved XCF file (tracking data preserved!)
2. **Birthmark → Show Status** (verify: Level 1)
3. Add text overlay
4. **Birthmark → Log Level 2 Operation**
5. **File → Save As** (XCF)
6. **Birthmark → Export with Record**
7. **File → Export As** (JPEG)

**Result:** Image marked as Level 2 (highest level used across sessions)

## Troubleshooting

### "Tracking not initialized" error

**Problem:** You tried to log an operation before initializing tracking.

**Solution:** Run **Birthmark → Initialize Tracking** first.

### "Image is NOT authenticated" message

**Problem:** The image is not recognized by the aggregation server.

**Solution:**
- Verify the image was captured with a Birthmark-enabled camera
- Check that the aggregation server is running
- Ensure the image hash matches a record in the server

### "Plugin failed SSA validation" error

**Problem:** The plugin's certificate could not be validated.

**Solution:**
- Verify SSA server is running at `http://localhost:8001`
- Check that certificate files exist in `~/.birthmark/`
- Ensure the plugin version matches SSA's valid versions list

### "Failed to compute image hash" error

**Problem:** The plugin couldn't hash the image data.

**Solution:**
- Make sure the image has at least one layer
- Try flattening the image (Image → Flatten Image)
- Check GIMP console for detailed error messages

### Tracking data lost after export

**Problem:** You exported to JPEG/PNG and the tracking data is gone.

**Explanation:** GIMP parasites only persist in XCF format. This is expected.

**Solution:**
- Always save as XCF to preserve tracking data
- Use "Export with Record" to create the sidecar JSON file
- The sidecar file contains the modification record permanently

### Server connection refused

**Problem:** Plugin cannot connect to aggregation server or SSA server.

**Solution:**
- Verify servers are running
- Test with browser: `http://localhost:8000/api/v1/health`
- Test with browser: `http://localhost:8001/health`
- Check firewall settings
- Update server URLs in plugin configuration if needed

## Best Practices

### 1. Initialize Early

Initialize tracking as soon as you open an authenticated image, before making any edits. This ensures you capture the original state.

### 2. Log Honestly

Always log the highest level operation you performed. The modification level system only works if users are honest about their edits.

### 3. Save Frequently in XCF

Save your work in XCF format to preserve tracking data across sessions. You can always export to other formats later.

### 4. Export with Record Before Final Export

Run "Export with Record" before exporting to JPEG/PNG. This creates the sidecar file and submits to the server while you still have the tracking data.

### 5. Keep Sidecar Files

Don't delete the `.birthmark.json` sidecar files. They provide verifiable provenance for your exported images.

### 6. Understand the Sticky System

Once you use a Level 2 operation, the image is permanently marked as Level 2 for that editing session. Plan your workflow accordingly.

## Limitations

This proof of concept has several limitations:

1. **Manual logging required**: You must manually invoke logging commands
2. **XCF only for tracking**: Parasites don't persist in JPEG/PNG (use sidecar files)
3. **No undo for level changes**: Modification level only goes up, never down
4. **Single software authority**: Plugin only validates against one SSA instance
5. **No automatic operation detection**: GIMP's plugin API doesn't support automatic PDB interception

These limitations are acceptable for a proof of concept demonstrating the architecture to potential partners. Production implementations would integrate tracking directly into editing software.

## What's Next?

After mastering the plugin workflow:

1. **Test with real images**: Use images from your Birthmark camera prototype
2. **Verify on blockchain**: Check that modification records appear on zkSync testnet
3. **Share with photographers**: Gather feedback on the Level 1/2 classification
4. **Document edge cases**: Note any operations that are hard to classify
5. **Prepare demos**: Create compelling demos for partnership pitches

## Additional Resources

- **Installation Guide**: [install.md](install.md)
- **Level Classification**: [level_classification.md](level_classification.md)
- **Phase 3 Plan**: `docs/phase-plans/Birthmark_Phase_3_Plan_Image_Editor_Wrapper_SSA.md`
- **GitHub Repository**: https://github.com/Birthmark-Standard/Birthmark

## Support

For questions or issues:

1. Check GIMP's Python-Fu Console: **Filters → Python-Fu → Console**
2. Review server logs (aggregation server and SSA server)
3. Verify certificate installation
4. Consult the main Birthmark documentation

---

**Remember:** This plugin demonstrates the Birthmark modification tracking architecture. It shows potential partners that the standard addresses the complete image lifecycle, not just capture authentication. The manual workflow is intentional for this proof of concept - production integrations would be seamless and automatic.
