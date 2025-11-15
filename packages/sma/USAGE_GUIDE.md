# SMA Device Provisioning - Usage Guide

This guide explains how to use the device provisioning functionality for the Birthmark SMA (Simulated Manufacturer Authority).

## Quick Start

### 1. Setup the SMA

First, initialize the SMA with CA certificates and key tables:

```bash
cd packages/sma
python scripts/setup_sma.py
```

This will create:
- Root CA and Intermediate CA certificates
- 10 key tables (Phase 1) with master keys
- Empty device registry

**Options:**
```bash
# For Phase 2 (2,500 key tables)
python scripts/setup_sma.py --phase2

# Force regeneration of existing files
python scripts/setup_sma.py --force

# Custom data directory
python scripts/setup_sma.py --data-dir /path/to/data
```

### 2. Start the SMA Service

```bash
uvicorn src.main:app --port 8001 --reload
```

Access the API docs at: http://localhost:8001/docs

### 3. Provision a Device

#### Option A: Using the Script (Phase 1)

```bash
python scripts/provision_device.py --serial DEVICE001
```

This will:
1. Generate a device certificate
2. Assign 3 random key tables
3. Generate a simulated NUC hash
4. Save provisioning data to `provisioned_devices/provisioning_DEVICE001.json`

**Advanced Options:**
```bash
# Specify device family
python scripts/provision_device.py --serial PI-12345 --family "Raspberry Pi"

# Provide custom NUC hash (64 hex chars)
python scripts/provision_device.py --serial DEVICE002 \
  --nuc-hash "a1b2c3d4e5f6789012345678901234567890123456789012345678901234abcd"

# Custom output directory
python scripts/provision_device.py --serial DEVICE003 --output-dir ./my_devices
```

#### Option B: Using the API (Phase 2)

```bash
curl -X POST "http://localhost:8001/api/v1/devices/provision" \
  -H "Content-Type: application/json" \
  -d '{
    "device_serial": "API-DEVICE001",
    "device_family": "iOS"
  }'
```

## Provisioning Workflow

### What Happens During Provisioning

1. **Device Keypair Generation**
   - ECDSA P-256 keypair is generated
   - Private key stored in provisioning file
   - Public key embedded in certificate

2. **Table Assignment**
   - 3 random tables selected from available pool
   - No duplicates within same device
   - Assignment tracked for validation

3. **Certificate Generation**
   - Device certificate signed by Intermediate CA
   - 2-year validity period
   - Contains device serial and family

4. **NUC Hash**
   - Phase 1: Simulated (random 32-byte hash)
   - Production: Actual sensor fingerprint

5. **Registration**
   - Device info stored in registry
   - Table assignments saved
   - NUC hash recorded

### Provisioning Response

The provisioning response contains:

```json
{
  "device_serial": "DEVICE001",
  "device_certificate": "-----BEGIN CERTIFICATE-----\n...",
  "certificate_chain": "-----BEGIN CERTIFICATE-----\n...",
  "device_private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "device_public_key": "-----BEGIN PUBLIC KEY-----\n...",
  "table_assignments": [2, 5, 8],
  "nuc_hash": "a1b2c3d4...",
  "device_family": "Raspberry Pi"
}
```

**⚠️ SECURITY WARNING:**
- The provisioning file contains the **private key**
- Store it securely and transfer over secure channels only
- Set file permissions to 600 (owner read/write only)

## API Endpoints

### Health Check

```bash
GET /health
```

Returns service status and statistics.

### Get Statistics

```bash
GET /stats
```

Returns detailed provisioning statistics.

### Provision Device

```bash
POST /api/v1/devices/provision
```

**Request:**
```json
{
  "device_serial": "string",
  "device_family": "string",
  "nuc_hash": "string (optional, 64 hex chars)"
}
```

**Response:** 201 Created with provisioning data

### Get Device Info

```bash
GET /api/v1/devices/{device_serial}
```

Returns non-sensitive device information.

### List Devices

```bash
GET /api/v1/devices?device_family=Raspberry Pi
```

Returns list of all provisioned devices (optionally filtered).

## File Structure

After setup and provisioning, you'll have:

```
packages/sma/
├── data/                          # SMA data directory (gitignored)
│   ├── root-ca.crt                # Root CA certificate
│   ├── root-ca.key                # Root CA private key (secure!)
│   ├── intermediate-ca.crt        # Intermediate CA certificate
│   ├── intermediate-ca.key        # Intermediate CA private key (secure!)
│   ├── key_tables.json            # Key tables with master keys (secure!)
│   └── device_registry.json       # Device registrations
│
├── provisioned_devices/           # Provisioning files (gitignored)
│   ├── provisioning_DEVICE001.json
│   └── provisioning_DEVICE002.json
│
├── src/                           # Source code
│   ├── provisioning/              # Certificate & provisioning logic
│   ├── key_tables/                # Key derivation & table management
│   ├── identity/                  # Device registry
│   └── main.py                    # FastAPI application
│
├── scripts/                       # Setup & provisioning scripts
│   ├── setup_sma.py               # Initialize SMA
│   └── provision_device.py        # Manual device provisioning
│
└── tests/                         # Unit tests
    ├── test_provisioning.py
    └── test_key_derivation.py
```

## Security Best Practices

1. **Protect Private Keys**
   - CA private keys (root-ca.key, intermediate-ca.key)
   - Device private keys (in provisioning files)
   - Set file permissions to 600

2. **Secure Key Tables**
   - key_tables.json contains master keys
   - Never commit to version control
   - Backup securely

3. **Device Registry**
   - Contains NUC hashes (sensor fingerprints)
   - Privacy-sensitive data
   - Backup regularly

4. **Provisioning Files**
   - Contain device private keys
   - Transfer over secure channels (HTTPS, SCP)
   - Delete from server after transfer

## Testing

Run unit tests:

```bash
cd packages/sma
pytest tests/ -v
```

Validate key derivation:

```bash
python -m src.key_tables.key_derivation
```

## Troubleshooting

### CA certificates not found

**Error:** `CA certificates not found. Run setup_sma.py first.`

**Solution:**
```bash
python scripts/setup_sma.py
```

### Device already provisioned

**Error:** `Device DEVICE001 already provisioned`

**Solution:** Use a different serial number or delete the device from the registry.

### Key tables not found

**Error:** `Key tables not found. Run setup_sma.py first.`

**Solution:**
```bash
python scripts/setup_sma.py
```

## Phase 1 vs Phase 2

| Feature | Phase 1 | Phase 2 |
|---------|---------|---------|
| **Key Tables** | 10 tables | 2,500 tables |
| **Storage** | JSON files | PostgreSQL database |
| **Provisioning** | Manual script | Automated API |
| **NUC Hash** | Simulated | Actual sensor data |
| **Devices** | ~5-10 (photography club) | 100,000+ |

## Next Steps

After provisioning a device:

1. **Transfer provisioning file to device**
   ```bash
   scp provisioned_devices/provisioning_DEVICE001.json pi@device:/home/pi/
   ```

2. **Install credentials on device**
   - Store private key in TPM/Secure Element
   - Store certificate and table assignments
   - Store NUC hash for validation

3. **Test device submission**
   - Capture image
   - Hash with NUC token
   - Submit to Aggregation Server

## Support

For questions or issues:
- Check the main README: `packages/sma/README.md`
- Review the architecture: `docs/specs/Birthmark_Camera_Security_Architecture.md`
- GitHub Issues: https://github.com/Birthmark-Standard/Birthmark/issues
