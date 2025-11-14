# Camera Pi Package

**Phase:** Phase 1 (Hardware Prototype)
**Status:** In Development
**Hardware:** Raspberry Pi 4 + HQ Camera + LetsTrust TPM

## Overview

The camera-pi package implements the Raspberry Pi-based camera prototype for the Birthmark Standard. This package handles raw sensor data capture, hashing, and submission to the aggregation server.

## Key Components

### `src/sensor_capture.py`
Captures raw Bayer sensor data from the Raspberry Pi HQ Camera (Sony IMX477, 12.3MP). Uses picamera2 to access the raw sensor array.

### `src/hash_pipeline.py`
Computes SHA-256 hash of raw Bayer data. Target performance: <500ms using TPM acceleration.

### `src/tpm_interface.py`
Interfaces with the LetsTrust TPM module for:
- Secure key storage
- Device certificate management
- Cryptographic signing of authentication bundles

### `src/submission.py`
Sends authentication bundles to the aggregation server. Handles:
- Bundle construction
- Network communication
- Retry logic

## Performance Targets

- **Total capture time:** <650ms
- **Parallel hashing overhead:** <5% CPU
- **User-perceivable latency:** Zero
- **Sustained capture rate:** 1 photo/second

## Hardware Requirements

- Raspberry Pi 4 Model B (4GB RAM)
- Raspberry Pi HQ Camera (Sony IMX477, 12.3MP)
- LetsTrust TPM Module (Infineon SLB 9670)
- 64GB microSD (A2 rated)
- Optional: GPS Module (Neo-6M), RTC (DS3231)

## Setup

```bash
cd packages/camera-pi
pip install -r requirements.txt
python scripts/provision_device.py  # First time only
python src/main.py
```

## Testing

```bash
pytest tests/
```

## Related Documentation

- Hardware setup: `docs/phase-plans/Birthmark_Phase_1_Plan_Simulated_Camera.md`
- Security architecture: `docs/specs/Birthmark_Camera_Security_Architecture.md`
