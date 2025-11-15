# SMA Scripts

This directory contains utility scripts for setting up and testing the SMA.

## Scripts

### `generate_key_tables.py`

**Purpose:** Generate and populate the 2,500 master keys for HKDF-based key derivation.

**When to use:** Run once during initial SMA setup.

**Usage:**
```bash
cd packages/sma
python scripts/generate_key_tables.py
```

**Environment variables:**
- `DATABASE_URL`: PostgreSQL connection string (default: `postgresql://postgres:postgres@localhost/sma`)

**Notes:**
- This script will fail if key tables already exist
- To regenerate, you must first delete existing tables from the database
- In production, master keys should be stored in an HSM

---

### `test_validation.py`

**Purpose:** Test the validation endpoint end-to-end.

**What it does:**
1. Initializes a test database
2. Generates 2,500 master keys
3. Registers a test Raspberry Pi device
4. Encrypts a NUC token (simulating camera behavior)
5. Validates the token through the SMA endpoint
6. Tests failure cases (wrong keys, wrong tables)

**Usage:**
```bash
cd packages/sma
python scripts/test_validation.py
```

**Requirements:**
- PostgreSQL running on localhost
- Database named `sma_test` (will be created automatically)

**What success looks like:**
```
==============================================================
SMA VALIDATION ENDPOINT TEST
==============================================================
Initializing test database...
✓ Key tables populated

Registering test device...
✓ Device registered: TEST-RPI-001

Testing validation...
✓ Retrieved master keys for tables: [42, 1337, 2001]
✓ Derived encryption keys for indices: [7, 99, 512]
✓ Encrypted NUC token (156 bytes)
✓ VALIDATION PASSED - Device authenticated successfully!

Testing with wrong key indices (should fail)...
✓ VALIDATION CORRECTLY FAILED for wrong keys

Testing with wrong table references (should fail)...
✓ VALIDATION CORRECTLY FAILED for wrong tables

==============================================================
✓ ALL TESTS PASSED
==============================================================
```

---

## Setup Instructions

### 1. Install Dependencies

```bash
cd packages/sma
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Optional, for development
```

### 2. Set Up PostgreSQL

Create a database for the SMA:

```bash
# Using psql
createdb sma

# Or using SQL
psql -c "CREATE DATABASE sma;"
```

### 3. Configure Environment

Copy the example environment file and edit it:

```bash
cp .env.example .env
# Edit .env with your database credentials
```

### 4. Generate Key Tables

```bash
python scripts/generate_key_tables.py
```

### 5. Start the SMA Server

```bash
uvicorn src.main:app --port 8001 --reload
```

The SMA will be available at `http://localhost:8001`.

API documentation: `http://localhost:8001/docs`

### 6. Test the Validation Endpoint

```bash
python scripts/test_validation.py
```

---

## Database Schema

The SMA uses two main tables:

### `key_tables`
- `table_id` (INTEGER PRIMARY KEY): Table ID (0-2499)
- `master_key` (BYTEA): 32-byte master key for HKDF

### `registered_devices`
- `device_serial` (VARCHAR PRIMARY KEY): Unique device serial number
- `nuc_hash` (BYTEA): 32-byte SHA-256 hash of NUC map
- `table_assignments` (INTEGER[]): List of 3 assigned table IDs
- `device_certificate` (TEXT): PEM-encoded X.509 certificate
- `device_public_key` (TEXT): PEM-encoded public key
- `device_family` (VARCHAR): Device type ('Raspberry Pi', 'iOS', etc.)

---

## API Endpoints

### POST `/api/v1/validate`

Validate a single camera authentication token.

**Request:**
```json
{
  "encrypted_token": "base64_encoded_token",
  "table_references": [42, 1337, 2001],
  "key_indices": [7, 99, 512]
}
```

**Response:**
```json
{
  "valid": true
}
```

### POST `/api/v1/validate/batch`

Validate multiple tokens in a single request.

### GET `/api/v1/health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "registered_devices": 42
}
```

---

## Troubleshooting

### "Key tables already exist" error

If you need to regenerate key tables:

```sql
-- WARNING: This will delete all master keys
DROP TABLE key_tables CASCADE;
DROP TABLE registered_devices CASCADE;
```

Then run `generate_key_tables.py` again.

### Database connection errors

Check your `DATABASE_URL` environment variable:
```bash
echo $DATABASE_URL
```

Make sure PostgreSQL is running:
```bash
pg_isready
```

### Import errors

Make sure you're running scripts from the correct directory:
```bash
cd packages/sma
python scripts/test_validation.py
```

---

## Security Notes

- Master keys are stored unencrypted in PostgreSQL for Phase 1
- In production (Phase 3), master keys must be stored in an HSM
- Never commit `.env` files with real credentials
- The SMA never sees or logs image hashes
- Failed validations are logged but never reveal why they failed
