# Birthmark Aggregation Server

**Phase:** Phase 1 (Mock Backend)
**Status:** Ready for Testing
**Technology:** FastAPI + PostgreSQL + SQLAlchemy

## Overview

The aggregation server is the central hub of the Birthmark Protocol. It:

- Receives authentication bundles from **cameras** (4 hashes: raw, processed, raw+GPS, processed+GPS)
- Receives authentication bundles from **software** editors (single edited hash with parent reference)
- Validates tokens with appropriate authorities (SMA for cameras, SSA for software)
- Batches validated submissions into Merkle trees
- Posts Merkle roots to blockchain (mock in Phase 1)
- Provides verification API for querying image authenticity

## Architecture

```
Camera (Raspberry Pi)              Software (Lightroom, etc.)
    │                                    │
    │ POST /api/v1/submit                │ POST /api/v1/submit
    │ {image_hashes[], camera_token,     │ {image_hash, program_token,
    │  manufacturer_cert, timestamp}     │  developer_cert, parent_hash}
    │                                    │
    └──────────────┬─────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│      AGGREGATION SERVER                 │
│  ┌──────────────────────────────────┐  │
│  │   Submission API                 │  │
│  │   POST /api/v1/submit            │  │
│  └────────────┬─────────────────────┘  │
│               │                         │
│               ▼                         │
│  ┌──────────────────────────────────┐  │
│  │   Authority Integration          │  │
│  │   /sma/validate (camera)         │  │
│  │   /ssa/validate (software)       │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │   Verification API               │  │
│  │   GET /api/v1/verify             │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

## Features

### Dual Submission Types

**Camera Submissions:**
- 4 image hashes in one transaction (raw, processed, raw+GPS, processed+GPS)
- Camera token validated by SMA (Simulated Manufacturer Authority)
- Modification levels: 0 (raw), 1 (processed)

**Software Submissions:**
- Single edited image hash with parent reference
- Program token validated by SSA (Simulated Software Authority)
- Modification levels: 1 (slight mods), 2 (significant mods)

### Provenance Chain Tracking

- Parent-child relationships between images
- Full forensic trail from original capture to final edit
- Modification level tracking through the chain

### Mock Authorities (Phase 1)

**SMA (Simulated Manufacturer Authority):**
- `/sma/provision` - Provision new cameras
- `/sma/validate` - Validate camera tokens
- Actual validation logic (not just pass-through)

**SSA (Simulated Software Authority):**
- `/ssa/register-software` - Register new software
- `/ssa/register-version` - Register software versions
- `/ssa/validate` - Validate program tokens
- Token generation: SHA256(program_hash || version_string)

## Quick Start

### 1. Prerequisites

- Python 3.11+
- PostgreSQL 15+
- (Optional) Docker for PostgreSQL

### 2. Installation

```bash
cd packages/aggregator

# Install dependencies
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

### 3. Database Setup

**Option A: Using Docker Compose (Recommended)**

```bash
docker compose up -d
```

**Option B: Local PostgreSQL**

```bash
createdb birthmark_dev
```

### 4. Configuration

```bash
cp .env.example .env
# Edit .env if needed (defaults work for local development)
```

### 5. Run Migrations

```bash
alembic upgrade head
```

### 6. Start Server

```bash
# Development mode (with auto-reload)
uvicorn src.main:app --reload

# Or using Python
python -m src.main
```

Server will start at http://localhost:8000

### 7. Access API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

## API Endpoints

### Submission API

**POST /api/v1/submit** - Submit authentication bundle

Camera submission example:
```json
{
  "submission_type": "camera",
  "image_hashes": [
    {
      "image_hash": "abc123...",
      "modification_level": 0,
      "parent_image_hash": null
    },
    {
      "image_hash": "def456...",
      "modification_level": 1,
      "parent_image_hash": "abc123..."
    }
  ],
  "camera_token": {
    "ciphertext": "789abc...",
    "auth_tag": "def012...",
    "nonce": "345678...",
    "table_id": 42,
    "key_index": 523
  },
  "manufacturer_cert": {
    "authority_id": "CANON_001",
    "validation_endpoint": "http://localhost:8000/sma/validate"
  },
  "timestamp": 1699564800
}
```

Software submission example:
```json
{
  "submission_type": "software",
  "image_hash": "fedcba987654...",
  "modification_level": 2,
  "parent_image_hash": "789abc012def...",
  "program_token": "sha256_hex_64_chars...",
  "developer_cert": {
    "authority_id": "ADOBE_LIGHTROOM",
    "version_string": "Adobe Lightroom Classic 14.1.0",
    "validation_endpoint": "http://localhost:8000/ssa/validate"
  }
}
```

### Verification API

**GET /api/v1/verify?image_hash={hash}** - Verify image authenticity

**POST /api/v1/verify/batch** - Verify multiple images (max 100)

### SMA Mock Endpoints

**POST /sma/provision** - Provision a new camera

```json
{
  "camera_serial": "PI_CAM_001",
  "manufacturer": "Raspberry Pi Foundation",
  "nuc_data": "mock_sensor_calibration_data"
}
```

**GET /sma/cameras/{serial}** - Get camera info

### SSA Mock Endpoints

**POST /ssa/register-software** - Register new software

```json
{
  "authority_id": "ADOBE_LIGHTROOM",
  "developer_name": "Adobe",
  "software_name": "Lightroom Classic"
}
```

**POST /ssa/register-version** - Register software version

```json
{
  "authority_id": "ADOBE_LIGHTROOM",
  "version_string": "Adobe Lightroom Classic 14.1.0"
}
```

**GET /ssa/software/{authority_id}** - Get software info with all versions

## Testing Workflow

### 1. Provision a Camera (SMA)

```bash
curl -X POST http://localhost:8000/sma/provision \
  -H "Content-Type: application/json" \
  -d '{
    "camera_serial": "PI_CAM_001",
    "manufacturer": "Raspberry Pi Foundation",
    "nuc_data": "test_nuc_calibration_data_12345"
  }'
```

Save the `nuc_hash` and `table_ids` from the response.

### 2. Submit Camera Images

```bash
curl -X POST http://localhost:8000/api/v1/submit \
  -H "Content-Type: application/json" \
  -d '{
    "submission_type": "camera",
    "image_hashes": [
      {
        "image_hash": "<64-char-hex>",
        "modification_level": 0,
        "parent_image_hash": null
      }
    ],
    "camera_token": {
      "ciphertext": "<nuc_hash-from-step-1>",
      "auth_tag": "0123456789abcdef0123456789abcdef",
      "nonce": "0123456789abcdef01234567",
      "table_id": <first-table-id-from-step-1>,
      "key_index": 0
    },
    "manufacturer_cert": {
      "authority_id": "RASPBERRY_PI_001",
      "validation_endpoint": "http://localhost:8000/sma/validate"
    },
    "timestamp": '$(date +%s)'
  }'
```

### 3. Register Software (SSA)

```bash
# Register software
curl -X POST http://localhost:8000/ssa/register-software \
  -H "Content-Type: application/json" \
  -d '{
    "authority_id": "ADOBE_LIGHTROOM",
    "developer_name": "Adobe",
    "software_name": "Lightroom Classic"
  }'

# Save the program_hash

# Register version
curl -X POST http://localhost:8000/ssa/register-version \
  -H "Content-Type: application/json" \
  -d '{
    "authority_id": "ADOBE_LIGHTROOM",
    "version_string": "Adobe Lightroom Classic 14.1.0"
  }'

# Save the expected_token
```

### 4. Submit Software Edit

```bash
curl -X POST http://localhost:8000/api/v1/submit \
  -H "Content-Type: application/json" \
  -d '{
    "submission_type": "software",
    "image_hash": "<new-64-char-hex>",
    "modification_level": 2,
    "parent_image_hash": "<parent-hash-from-camera>",
    "program_token": "<expected_token-from-step-3>",
    "developer_cert": {
      "authority_id": "ADOBE_LIGHTROOM",
      "version_string": "Adobe Lightroom Classic 14.1.0",
      "validation_endpoint": "http://localhost:8000/ssa/validate"
    }
  }'
```

### 5. Verify Image

```bash
curl http://localhost:8000/api/v1/verify?image_hash=<hash>
```

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Formatting

```bash
black src/
ruff check src/
```

### Type Checking

```bash
mypy src/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Project Structure

```
packages/aggregator/
├── src/
│   ├── api/
│   │   ├── submissions.py       # Camera & software submission endpoints
│   │   ├── verification.py      # Verification & provenance queries
│   │   ├── sma.py               # SMA mock endpoints
│   │   └── ssa.py               # SSA mock endpoints
│   ├── config.py                # Configuration management
│   ├── database.py              # Database connection
│   ├── models.py                # SQLAlchemy models
│   ├── schemas.py               # Pydantic schemas
│   └── main.py                  # FastAPI app
├── alembic/
│   └── versions/                # Database migrations
├── tests/                       # Tests
├── .env.example                 # Example configuration
├── docker-compose.yml           # PostgreSQL container
├── pyproject.toml               # Dependencies
└── README.md                    # This file
```

## Database Schema

### submissions
Unified table for camera and software submissions with:
- `submission_type`: 'camera' or 'software'
- `modification_level`: 0 (raw), 1 (processed/slight), 2 (significant)
- `parent_image_hash`: Creates provenance chain
- `transaction_id`: Groups camera hashes from same submission

### batches
Merkle tree batches posted to blockchain

### merkle_proofs
Proof paths for verification

### sma_cameras
Provisioned cameras with NUC hashes

### sma_key_tables
Encryption key tables (0-249)

### ssa_software
Registered software packages

### ssa_software_versions
Software versions with expected tokens

## Phase 1 Limitations

- **No real blockchain**: Mock transaction hashes (0xMOCK_...)
- **No batching worker**: Manual batching for now
- **No validation worker**: Validation happens inline
- **Simplified encryption**: Camera tokens use NUC hash as ciphertext for testing
- **No rate limiting**: Simple 100 req/min limit

## Next Steps (Phase 2)

1. Background workers for validation and batching
2. Real zkSync blockchain integration
3. Time-based batching (6-hour timeout)
4. Redis caching
5. Production-grade encryption
6. Load balancing

## Troubleshooting

### Database Connection Error

```bash
# Check PostgreSQL is running
docker compose ps

# Or for local PostgreSQL
pg_isready
```

### Alembic Migration Error

```bash
# Reset database (WARNING: deletes all data)
alembic downgrade base
alembic upgrade head
```

### Import Errors

```bash
# Reinstall package in development mode
pip install -e .
```

## License

TBD - See LICENSE file

## Contact

The Birthmark Standard Foundation
https://github.com/Birthmark-Standard/Birthmark
