# SMA (Simulated Manufacturer Authority) Package

**Phase:** Phase 1-2
**Status:** In Development
**Technology:** FastAPI + PostgreSQL

## Overview

The SMA (Simulated Manufacturer Authority) package simulates the role that camera manufacturers will play in the production Birthmark system. It validates camera authenticity without ever seeing image content.

## Key Responsibility

**Validate camera legitimacy, NOT image content.**

The SMA receives encrypted NUC tokens from the aggregator and returns a simple PASS/FAIL response. It **never** receives or processes image hashes.

## Architecture

### Key Table System

- **2,500 key tables** with 1,000 keys each
- Each camera assigned 3 random tables at provisioning
- Keys rotated using HKDF derivation
- 256-bit AES-GCM encryption keys

### Privacy Design

```
Camera encrypts NUC hash → Aggregator forwards encrypted token → SMA validates → Returns PASS/FAIL
                                                                                           ↓
                                                                        (SMA never sees image hash)
```

## Key Components

### `src/key_tables/`
Manages the 2,500 × 1,000 key table system:
- Key generation and storage
- HKDF-based key derivation
- Table assignment to devices

### `src/provisioning/`
Device provisioning and certificate issuance:
- Generate device certificates (X.509, ECDSA P-256)
- Assign key tables to new devices
- Store NUC hashes securely
- Issue device credentials

### `src/validation/`
Validates authentication tokens from aggregator:
- Decrypt NUC tokens using assigned key tables
- Compare against registered NUC hashes
- Return PASS/FAIL (never sees image hash)

### `src/identity/`
Device identity management:
- NUC hash records
- Device certificate chains
- Device family classification (Raspberry Pi, iOS, etc.)

## Database Schema

### `key_tables`
2,500 rows, each containing a master key for HKDF derivation.

### `registered_devices`
Records for each provisioned camera:
- Device serial number
- NUC hash (SHA-256, 32 bytes)
- Assigned key tables (3 table IDs)
- Device certificate and public key

## Security Considerations

- Master keys stored securely (HSM in production)
- NUC hashes are one-way (cannot reverse to raw sensor data)
- Key tables provide plausible deniability
- No logging of image-related data

## Performance Targets

- Validation response: <50ms
- 100% accuracy (valid tokens pass, invalid fail)
- Support for 100,000+ registered devices

## Setup

```bash
cd packages/sma
pip install -r requirements.txt
python scripts/generate_key_tables.py  # First time only
uvicorn src.main:app --port 8001 --reload
```

## Testing

```bash
pytest tests/
```

## Phase 2 Enhancements

- Increased key tables for iOS devices
- Time-based key rotation
- Multi-region deployment
- Production HSM integration

## Related Documentation

- SMA architecture: `docs/phase-plans/Birthmark_Phase_1-2_Plan_SMA.md`
- Security model: `docs/specs/Birthmark_Camera_Security_Architecture.md`
- Validation API: `shared/protocols/aggregator_to_sma.yaml`
