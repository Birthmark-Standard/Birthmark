# Birthmark Camera Pi Package

**Phase:** Phase 1 (Hardware Prototype)
**Status:** Implementation Complete
**Hardware:** Raspberry Pi 4 + HQ Camera + LetsTrust TPM

## Overview

The camera-pi package implements the Raspberry Pi-based camera prototype for the Birthmark Standard. This package demonstrates **zero-latency photo authentication** through parallel processing of raw sensor data with hardware-backed security.

## Architecture

```
Camera Sensor → Raw Bayer Data → ┌─ ISP Processing → User Image
                                 └─ TPM Hashing → Authentication Bundle → Aggregator
```

**Key Innovation:** Authentication happens in parallel with image processing, eliminating user-facing latency.

## Key Components

### Core Modules

- **`raw_capture.py`** - Raw Bayer data capture from Raspberry Pi HQ Camera (Sony IMX477)
- **`camera_token.py`** - Encrypted NUC token generation for SMA validation
- **`tpm_interface.py`** - TPM integration for hashing and signing
- **`aggregation_client.py`** - HTTP client for submitting authentication bundles
- **`provisioning_client.py`** - Loads device provisioning data from SMA
- **`main.py`** - Main CLI application

### Crypto Modules

- **`crypto/key_derivation.py`** - HKDF-SHA256 (MUST match SMA exactly)
- **`crypto/encryption.py`** - AES-256-GCM for NUC token encryption
- **`crypto/signing.py`** - ECDSA P-256 for bundle signing

## Installation

### Dependencies

```bash
cd packages/camera-pi
pip install -e .
```

### Development Dependencies

```bash
pip install -e ".[dev]"
```

## Usage

### Device Provisioning

First, provision the device with the SMA:

```bash
# Run SMA provisioning script
cd packages/sma
python scripts/provision_device.py

# This creates: packages/camera-pi/data/provisioning.json
```

### Command Line Interface

```bash
# Single capture
python -m camera_pi capture

# Timelapse (30 second interval, 100 photos)
python -m camera_pi timelapse --interval 30 --count 100

# Continuous timelapse
python -m camera_pi timelapse --interval 10

# Test aggregation server connection
python -m camera_pi test

# Show device info
python -m camera_pi info
```

### Using Mock Camera (Development)

For testing without Raspberry Pi hardware:

```bash
python -m camera_pi capture --mock
```

### Python API

```python
from camera_pi import BirthmarkCamera

# Initialize camera
camera = BirthmarkCamera(
    provisioning_path="./data/provisioning.json",
    aggregation_url="https://api.birthmarkstandard.org",
    output_dir="./captures",
    use_mock_camera=False  # Set True for testing
)

# Capture single photo
result = camera.capture_photo()

# Capture timelapse
camera.capture_timelapse(interval=30, count=100)

# Cleanup
camera.close()
```

## Performance Targets

- **Raw capture:** <500ms
- **SHA-256 hash:** <100ms (TPM/software)
- **Token generation:** <20ms (HKDF + AES-GCM)
- **Bundle signing:** <30ms (ECDSA)
- **Total background:** <150ms (parallel processing)
- **ISP processing:** <600ms (user-facing)
- **Total user wait:** <700ms
- **Sustained rate:** 1 photo/second

## Hardware Requirements

### Required

- Raspberry Pi 4 Model B (4GB RAM minimum)
- Raspberry Pi HQ Camera (Sony IMX477, 12.3MP)
- 64GB microSD (A2 rated for performance)
- 5V/3A USB-C power supply

### Optional

- LetsTrust TPM Module (Infineon SLB 9670) - Phase 2 hardware crypto
- GPS Module (Neo-6M) - For GPS hashing
- RTC Module (DS3231) - Accurate timestamps offline
- Battery pack - Field testing

### Total Cost

- **Minimum:** ~$120 (Pi + Camera + SD card)
- **Recommended:** ~$200 (includes TPM and GPS)

## Testing

### Run Tests

```bash
# All tests
pytest tests/ -v

# Specific test module
pytest tests/test_key_derivation.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

### Validate SMA Compatibility

**CRITICAL:** Key derivation must match SMA exactly

```bash
# Generate test vectors (camera side)
python -m camera_pi.crypto.key_derivation

# Generate test vectors (SMA side)
cd packages/sma
python -m src.key_tables.key_derivation

# Compare outputs - derived keys must match byte-for-byte
```

## Project Structure

```
packages/camera-pi/
├── src/camera_pi/          # Main package
│   ├── crypto/             # Cryptographic utilities
│   │   ├── key_derivation.py
│   │   ├── encryption.py
│   │   └── signing.py
│   ├── raw_capture.py      # Camera interface
│   ├── camera_token.py     # Token generation
│   ├── tpm_interface.py    # TPM integration
│   ├── aggregation_client.py
│   ├── provisioning_client.py
│   └── main.py             # CLI application
├── tests/                  # Test suite
│   ├── test_key_derivation.py
│   └── ...
├── configs/                # Configuration files
├── scripts/                # Setup and utility scripts
├── data/                   # Runtime data (gitignored)
│   ├── provisioning.json
│   └── captures/
├── pyproject.toml          # Package metadata
├── PLAN.md                 # Implementation plan
└── README.md               # This file
```

## Configuration

### Provisioning Data Format

```json
{
  "device_serial": "RaspberryPi-Prototype-001",
  "device_certificate": "-----BEGIN CERTIFICATE-----\n...",
  "certificate_chain": "-----BEGIN CERTIFICATE-----\n...",
  "device_private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "device_public_key": "-----BEGIN PUBLIC KEY-----\n...",
  "table_assignments": [3, 7, 9],
  "nuc_hash": "a1b2c3d4...",
  "device_family": "Raspberry Pi",
  "master_keys": {
    "3": "0123456789abcdef...",
    "7": "fedcba9876543210...",
    "9": "abcdef0123456789..."
  }
}
```

## Security Considerations

### Phase 1 (Current)

- **Software crypto:** Uses Python cryptography library
- **File-based keys:** Provisioning data stored in JSON (600 permissions)
- **No hardware TPM:** Software signing and hashing
- **Development only:** Not production-ready

### Phase 2 (Future)

- **Hardware TPM:** LetsTrust SLB 9670 integration
- **Secure storage:** Keys in TPM NVRAM
- **Hardware crypto:** TPM-accelerated hashing and signing
- **Production ready:** Full security stack

## Integration Points

### SMA (Simulated Manufacturer Authority)

- **Provisioning:** Receives device certificate and table assignments
- **Validation:** SMA validates encrypted NUC tokens
- **Key Derivation:** MUST match SMA implementation exactly

### Aggregation Server

- **Submission:** POST /api/v1/submit
- **Format:** JSON authentication bundle
- **Response:** 202 Accepted with receipt ID

### zkSync Blockchain

- **Indirect:** Aggregator posts to blockchain
- **Camera:** Never interacts with blockchain directly

## Troubleshooting

### Camera Not Found

```bash
# Check camera connection
vcgencmd get_camera

# Should show: supported=1 detected=1

# Enable camera interface
sudo raspi-config
# Interface Options → Camera → Enable
```

### picamera2 Not Available

```bash
# Install picamera2
sudo apt update
sudo apt install -y python3-picamera2

# Or use mock camera for testing
python -m camera_pi capture --mock
```

### Provisioning File Not Found

```bash
# Create example provisioning file
python -m camera_pi.provisioning_client create-example

# Or provision with SMA
cd packages/sma
python scripts/provision_device.py
```

### Key Derivation Mismatch

```bash
# Validate implementation
python -m camera_pi.crypto.key_derivation

# Compare with SMA test vectors
cd packages/sma
python -m src.key_tables.key_derivation

# Derived keys must match byte-for-byte
```

## Development

### Mock Components

For development without hardware:

- **MockCaptureManager:** Synthetic Bayer data generation
- **Software TPM:** Python cryptography (no hardware)
- **Mock Aggregator:** Local testing server

### Running Without Hardware

```bash
# Use --mock flag
python -m camera_pi capture --mock

# Or set in Python API
camera = BirthmarkCamera(use_mock_camera=True)
```

## Related Documentation

- **Implementation Plan:** `PLAN.md` (comprehensive architecture)
- **Hardware Setup:** `docs/phase-plans/Birthmark_Phase_1_Plan_Simulated_Camera.md`
- **SMA Integration:** `docs/phase-plans/Birthmark_Phase_1-2_Plan_SMA.md`
- **Project Overview:** `CLAUDE.md` (root)

## License

TBD - See LICENSE file in repository root

## Status

- [x] Core modules implemented
- [x] Crypto utilities (key derivation, encryption, signing)
- [x] Raw capture with mock camera
- [x] Camera token generation
- [x] Aggregation client
- [x] CLI application
- [x] Basic tests
- [ ] Hardware TPM integration (Phase 2)
- [ ] GPS integration (optional)
- [ ] Full test coverage
- [ ] SMA validation testing
- [ ] Photography club demo
