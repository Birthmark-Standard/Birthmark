# SMA Key Tables

This module implements the key table generation and management system for the Simulated Manufacturer Authority (SMA).

## Overview

The key table system uses a hierarchical key derivation approach:

1. **Master Keys**: Each table has one 256-bit master key stored securely
2. **Derived Keys**: Individual encryption keys are derived on-demand using HKDF-SHA256
3. **Privacy**: Cameras use rotating keys from multiple tables to prevent tracking

## Files

- `generate.py` - Master key generation script
- `test_key_derivation_simple.py` - Comprehensive test suite (no external dependencies)
- `test_key_tables.py` - Full integration tests (requires cryptography library)
- `README.md` - This file

## Quick Start

### Generate Key Tables (Phase 1)

```bash
# Generate 10 tables × 100 keys (Phase 1 default)
python3 generate.py

# Output: ../data/key_tables_phase1.json
```

### Generate Key Tables (Phase 2)

```bash
# Generate 2,500 tables × 1,000 keys
python3 generate.py --phase2

# Output: ../data/key_tables_phase2.json
```

### Custom Configuration

```bash
# Custom number of tables and keys
python3 generate.py --tables 50 --keys 500 --output custom.json
```

### Verify Key Tables

```bash
# Verify integrity of generated key tables
python3 generate.py --verify ../data/key_tables_phase1.json
```

### Test Key Derivation

```bash
# Run comprehensive test suite
python3 test_key_derivation_simple.py
```

### Derive Sample Keys

```bash
# Show sample derived keys from a master key
python3 generate.py --sample-keys 04c02192e3b2f2c0a9fc55175d65f299374c6998813b37ec502fa545f726d0ce
```

## Key Table Structure

The generated JSON file contains:

```json
{
  "schema_version": "1.0",
  "created_at": "2025-11-14T22:00:56.887075Z",
  "configuration": {
    "num_tables": 10,
    "keys_per_table": 100,
    "key_size_bits": 256,
    "derivation_function": "HKDF-SHA256"
  },
  "key_tables": [
    {
      "table_id": 0,
      "master_key": "04c02192e3b2f2c0a9fc55175d65f299374c6998813b37ec502fa545f726d0ce",
      "status": "active"
    },
    ...
  ],
  "metadata": {
    "phase": "Phase 1",
    "generated_by": "generate.py",
    "generator_version": "1.0"
  }
}
```

## How It Works

### Key Derivation

Each table supports 100 keys (Phase 1) or 1,000 keys (Phase 2). Keys are derived using HKDF-SHA256:

```python
from shared.crypto.key_derivation import derive_key

# Load master key from JSON
master_key = bytes.fromhex("04c02192...")

# Derive encryption key for index 42
encryption_key = derive_key(master_key, 42)

# Use encryption_key with AES-256-GCM to encrypt NUC hash
```

### Camera Workflow

1. Camera is assigned 3 random tables during provisioning (e.g., tables 2, 5, 8)
2. For each photo, camera:
   - Randomly selects one of its 3 assigned tables
   - Randomly selects a key index (0-99 for Phase 1)
   - Derives encryption key from its stored master key
   - Encrypts NUC hash using AES-256-GCM
   - Sends: `(encrypted_nuc, table_id, key_index, nonce)` to aggregation server

### SMA Validation Workflow

1. Aggregation server forwards validation request to SMA
2. SMA:
   - Looks up master key for the specified table_id
   - Derives the same encryption key using the key_index
   - Decrypts the NUC hash
   - Queries database for matching NUC hash
   - Returns PASS (if found) or FAIL (if not found)

### Privacy Guarantees

- **SMA cannot track cameras**: Each camera uses 3 different tables, rotated randomly
- **SMA never sees image hash**: Only encrypted NUC hash is sent
- **Manufacturer cannot forge**: Only devices with correct NUC hash can generate valid tokens

## Storage Requirements

### Phase 1 (10 tables × 100 keys)
- JSON file: ~2 KB
- In-memory: ~320 bytes (10 master keys)
- Total derivable keys: 1,000

### Phase 2 (2,500 tables × 1,000 keys)
- JSON file: ~160 KB
- In-memory: ~80 KB (2,500 master keys)
- Total derivable keys: 2,500,000

**Note**: We store only master keys, not derived keys. This saves storage and prevents key leakage.

## Security Considerations

### Master Key Security

⚠️ **CRITICAL**: The `key_tables_phase1.json` file contains sensitive cryptographic material.

- Store in secure location (not in git repository)
- Encrypt at rest
- Restrict file permissions: `chmod 600 key_tables_phase1.json`
- In production: Use Hardware Security Module (HSM) or cloud key management

### Key Derivation Stability

⚠️ **NEVER modify** the key derivation algorithm (`shared/crypto/key_derivation.py`):

- Any change breaks compatibility with all existing devices
- Test vectors ensure cross-platform consistency
- If changes are needed, implement as a new schema version

### Key Rotation

Master keys should be rotated periodically:

1. Generate new key tables
2. Provision new devices with new tables
3. Maintain old tables for existing devices
4. Gradually phase out old tables as devices are reprovisioned

## Testing

### Unit Tests

```bash
# Run key derivation tests (no dependencies)
python3 test_key_derivation_simple.py
```

Expected output: All 6 tests pass

### Integration Tests

```bash
# Run full integration tests (requires cryptography library)
python3 test_key_tables.py
```

Expected output: All tests pass with encryption/decryption verification

### Test Vectors

The system includes known test vectors for cross-platform verification:

- All-zero master key, index 0: `28cef44dfd1eb717...`
- All-zero master key, index 1: `913254cdbff968d6...`
- All-FF master key, index 0: `a9395e32133165a8...`

These vectors **must remain stable** across all implementations.

## Scaling to Phase 2

To generate Phase 2 key tables (2,500 tables × 1,000 keys):

```bash
python3 generate.py --phase2
```

Changes from Phase 1:
- 10 tables → 2,500 tables
- 100 keys per table → 1,000 keys per table
- 1,000 total keys → 2,500,000 total keys
- JSON file size: ~2 KB → ~160 KB

The key derivation algorithm remains identical; only the configuration changes.

## Troubleshooting

### "Key tables file not found"

Run `python3 generate.py` to create the key tables first.

### "ModuleNotFoundError: No module named 'crypto'"

Make sure you're running from the `packages/sma` directory, or add the `shared` directory to your Python path.

### "Verification failed"

This indicates corrupted key table data. Regenerate with `python3 generate.py`.

### Keys don't match across camera and SMA

Ensure both use the same:
- Master key (from the same table_id)
- Key index
- Key derivation implementation (same HKDF algorithm)

## References

- HKDF specification: RFC 5869
- AES-GCM specification: NIST SP 800-38D
- Key derivation implementation: `shared/crypto/key_derivation.py`
- SMA architecture: `docs/phase-plans/Birthmark_Phase_1-2_Plan_SMA.md`

## Next Steps

After generating key tables:

1. **Store securely**: Move JSON file to secure location
2. **Configure SMA server**: Use key tables in validation server
3. **Provision devices**: Assign 3 random tables to each device
4. **Test end-to-end**: Verify camera → SMA validation flow

---

*Part of the Birthmark Standard - Open-source photo authentication system*
