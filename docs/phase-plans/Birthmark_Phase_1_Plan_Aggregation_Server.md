# Birthmark Phase 1 Plan - Aggregation Server

**Version:** 1.0  
**Date:** November 2025  
**Phase:** Phase 1 (Mock Backend)  
**Timeline:** 6-8 weeks

---

## Purpose

This document specifies the Aggregation Server component for Phase 1 development. The aggregation server is the central coordination point that:

1. Receives authentication bundles from cameras AND software editors
2. Validates tokens with the appropriate authority (SMA for cameras, SSA for software)
3. Accumulates validated submissions into batches
4. Generates Merkle trees for efficient verification
5. Simulates blockchain posting (mock transactions in Phase 1)
6. Provides verification API for querying image authenticity
7. Maintains provenance chain through parent_image_hash references

**Two Input Types:**
- **Camera submissions**: Raw/processed image hashes with camera token and manufacturer cert
- **Software submissions**: Edited image hashes with program token and developer cert

**Phase 1 Goal:** Prove the complete pipeline works without real blockchain integration. Include both camera and software submission paths to avoid code refactoring risks later. Early testing focuses on camera side, but integrated architecture supports full provenance chain.

---

## System Architecture

```
Camera (Raspberry Pi)              Software (Lightroom, etc.)
    │                                    │
    │ POST /api/v1/submit                │ POST /api/v1/submit
    │ {image_hashes[], camera_token,     │ {image_hash, program_token,
    │  manufacturer_cert, mod_levels[]}  │  developer_cert, parent_hash}
    │                                    │
    └──────────────┬─────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│      AGGREGATION SERVER                 │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │   Submission API                 │  │
│  │   - Receive bundles              │  │
│  │   - Validate format              │  │
│  │   - Detect submission type       │  │
│  │   - Store in queue               │  │
│  └────────────┬─────────────────────┘  │
│               │                         │
│               │ Route by submission type│
│               ▼                         │
│  ┌──────────────────────────────────┐  │
│  │   Authority Integration          │  │
│  │   - Camera → SMA                 │  │
│  │   - Software → SSA               │  │
│  │   - Update submission status     │  │
│  └────────────┬─────────────────────┘  │
│               │                         │
│               │ When 1,000 validated    │
│               ▼                         │
│  ┌──────────────────────────────────┐  │
│  │   Batch Accumulator              │  │
│  │   - Group submissions            │  │
│  │   - Create batch record          │  │
│  └────────────┬─────────────────────┘  │
│               │                         │
│               ▼                         │
│  ┌──────────────────────────────────┐  │
│  │   Merkle Tree Generator          │  │
│  │   - Build tree from hashes       │  │
│  │   - Generate proofs              │  │
│  │   - Store root & proofs          │  │
│  └────────────┬─────────────────────┘  │
│               │                         │
│               ▼                         │
│  ┌──────────────────────────────────┐  │
│  │   Mock Blockchain                │  │
│  │   - Generate fake tx hash        │  │
│  │   - Mark batch as "posted"       │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │   Verification API               │  │
│  │   - Query by image hash          │  │
│  │   - Return proof & mod level     │  │
│  │   - Trace provenance chain       │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │   PostgreSQL Database            │  │
│  │   - submissions (unified)        │  │
│  │   - batches                      │  │
│  │   - merkle_proofs                │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

## Component 1: Submission API

### Endpoint: POST /api/v1/submit

**Purpose:** Receive authentication bundles from cameras OR software editors and queue for validation. Single endpoint handles both submission types.

### Camera Submission Format

Camera submits 4 image hashes in a single transaction (raw, processed, raw+GPS, processed+GPS).

**Headers:**
```
Content-Type: application/json
X-API-Version: 1.0
```

**Body:**
```json
{
  "submission_type": "camera",
  "image_hashes": [
    {
      "image_hash": "abc123def456...",
      "modification_level": 0,
      "parent_image_hash": null
    },
    {
      "image_hash": "789abc012def...",
      "modification_level": 1,
      "parent_image_hash": "abc123def456..."
    },
    {
      "image_hash": "345678901234...",
      "modification_level": 0,
      "parent_image_hash": null
    },
    {
      "image_hash": "567890123456...",
      "modification_level": 1,
      "parent_image_hash": "345678901234..."
    }
  ],
  "camera_token": {
    "ciphertext": "789abc...",
    "auth_tag": "def012...",
    "nonce": "345678...",
    "table_id": 147,
    "key_index": 523
  },
  "manufacturer_cert": {
    "authority_id": "CANON_001",
    "validation_endpoint": "https://canon.birthmark-authority.com/validate"
  },
  "timestamp": 1699564800
}
```

**Field Specifications:**

**submission_type:**
- Required: "camera" or "software"

**image_hashes (array for camera submissions):**
- `image_hash`: SHA-256 hash (64 hex characters)
- `modification_level`: 0 (raw) or 1 (processed)
- `parent_image_hash`: null for raw images, points to raw hash for processed images

**camera_token:**
- `ciphertext`: AES-GCM encrypted NUC hash (hex string)
- `auth_tag`: AES-GCM authentication tag (32 hex chars)
- `nonce`: AES-GCM nonce (24 hex chars)
- `table_id`: Integer 0-249 (which key table)
- `key_index`: Integer 0-999 (which key in table)

**manufacturer_cert:**
- `authority_id`: Unique identifier for the manufacturer (e.g., "CANON_001")
- `validation_endpoint`: URL to manufacturer's validation server

**timestamp:**
- Unix timestamp in seconds (when image was captured)

### Software Submission Format

Software submits a single edited image hash with reference to parent.

**Body:**
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
    "validation_endpoint": "https://adobe.birthmark-authority.com/validate"
  }
}
```

**Field Specifications:**

**submission_type:**
- Required: "software"

**image_hash:**
- SHA-256 hash of the edited image (64 hex characters)

**modification_level:**
- 1 (slight modifications) or 2 (significant modifications)
- Inherits from parent if parent was modified, or set based on tools used in this session

**parent_image_hash:**
- Required for software submissions
- SHA-256 hash of the image that was loaded into the editor
- Creates forensic trail linking back to original capture

**program_token:**
- SHA256(program_hash || version_string)
- Where program_hash is the software's secret identifier assigned during developer registration
- 64 hex characters

**developer_cert:**
- `authority_id`: Unique identifier for the software developer (e.g., "ADOBE_LIGHTROOM")
- `version_string`: Exact version of software (e.g., "Adobe Lightroom Classic 14.1.0")
- `validation_endpoint`: URL to developer's validation server

### Response Format

**Success (202 Accepted):**
```json
{
  "status": "accepted",
  "submission_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "550e8400-e29b-41d4-a716-446655440001",
    "550e8400-e29b-41d4-a716-446655440002",
    "550e8400-e29b-41d4-a716-446655440003"
  ],
  "queue_position": 42,
  "estimated_batch_time": "2025-11-10T15:30:00Z"
}
```

For software submissions (single hash):
```json
{
  "status": "accepted",
  "submission_ids": ["550e8400-e29b-41d4-a716-446655440004"],
  "queue_position": 46,
  "estimated_batch_time": "2025-11-10T15:30:00Z"
}
```

**Error (400 Bad Request):**
```json
{
  "status": "error",
  "error_code": "INVALID_HASH_FORMAT",
  "message": "image_hash must be 64-character hex string",
  "field": "image_hashes[0].image_hash"
}
```

### Validation Rules

**Common Validations:**
- `submission_type`: Required, must be "camera" or "software"
- All image hashes: Must be exactly 64 hexadecimal characters (case-insensitive)
- `modification_level`: Integer in valid range (0-1 for camera, 1-2 for software)

**Camera-Specific Validations:**
- `image_hashes`: Array required, 1-4 entries
- `camera_token`: All nested fields required
- `camera_token.auth_tag`: Exactly 32 hex characters
- `camera_token.nonce`: Exactly 24 hex characters
- `camera_token.table_id`: Integer in range [0, 249]
- `camera_token.key_index`: Integer in range [0, 999]
- `manufacturer_cert`: Required with authority_id and validation_endpoint
- `timestamp`: Required, within ±24 hours of server time
- `modification_level`: Must be 0 or 1

**Software-Specific Validations:**
- `image_hash`: Single hash required
- `parent_image_hash`: Required (64 hex characters)
- `program_token`: Required (64 hex characters)
- `developer_cert`: Required with authority_id, version_string, and validation_endpoint
- `modification_level`: Must be 1 or 2

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_SUBMISSION_TYPE` | 400 | submission_type not "camera" or "software" |
| `INVALID_HASH_FORMAT` | 400 | Hash is not 64 hex chars |
| `INVALID_MODIFICATION_LEVEL` | 400 | Modification level out of range for submission type |
| `INVALID_TOKEN_FORMAT` | 400 | Camera token fields malformed |
| `INVALID_PROGRAM_TOKEN` | 400 | Program token not 64 hex chars |
| `INVALID_TABLE_ID` | 400 | table_id not in range 0-249 |
| `INVALID_KEY_INDEX` | 400 | key_index not in range 0-999 |
| `MISSING_PARENT_HASH` | 400 | Software submission missing parent_image_hash |
| `MISSING_AUTHORITY_CERT` | 400 | Manufacturer or developer cert missing |
| `MISSING_VERSION_STRING` | 400 | Developer cert missing version_string |
| `TIMESTAMP_OUT_OF_RANGE` | 400 | Timestamp too far from server time |
| `DUPLICATE_SUBMISSION` | 409 | image_hash already submitted |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `SERVER_ERROR` | 500 | Internal server error |

### Rate Limiting

**Phase 1 (Development):**
- Per IP: 100 requests/minute
- No API key required

**Phase 2+ (Production):**
- Per IP: 1000 requests/hour
- API key optional for high-volume users
- Burst allowance: 10 requests/second

### Database Storage

```sql
CREATE TABLE submissions (
    submission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_type VARCHAR(10) NOT NULL CHECK (submission_type IN ('camera', 'software')),
    image_hash CHAR(64) NOT NULL,
    modification_level INTEGER NOT NULL CHECK (modification_level >= 0 AND modification_level <= 2),
    parent_image_hash CHAR(64),
    
    -- Camera-specific fields (NULL for software submissions)
    camera_token_ciphertext TEXT,
    camera_token_auth_tag CHAR(32),
    camera_token_nonce CHAR(24),
    table_id INTEGER CHECK (table_id IS NULL OR (table_id >= 0 AND table_id < 250)),
    key_index INTEGER CHECK (key_index IS NULL OR (key_index >= 0 AND key_index < 1000)),
    manufacturer_authority_id VARCHAR(100),
    manufacturer_validation_endpoint TEXT,
    
    -- Software-specific fields (NULL for camera submissions)
    program_token CHAR(64),
    developer_authority_id VARCHAR(100),
    developer_version_string VARCHAR(200),
    developer_validation_endpoint TEXT,
    
    -- Common fields
    timestamp BIGINT,
    received_at TIMESTAMP NOT NULL DEFAULT NOW(),
    validation_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    validation_error TEXT,
    validated_at TIMESTAMP,
    batch_id UUID REFERENCES batches(batch_id),
    
    -- Transaction grouping (all hashes from same camera submission share this)
    transaction_id UUID,
    
    INDEX idx_image_hash (image_hash),
    INDEX idx_validation_status (validation_status),
    INDEX idx_received_at (received_at),
    INDEX idx_batch_id (batch_id),
    INDEX idx_parent_hash (parent_image_hash),
    INDEX idx_transaction_id (transaction_id),
    INDEX idx_modification_level (modification_level)
);

-- Constraint: camera submissions must have camera fields
-- Constraint: software submissions must have software fields
-- These are enforced in application logic for flexibility
```

**Notes on Schema:**
- `submission_type`: Differentiates camera vs software submissions
- `modification_level`: 0 (raw), 1 (processed/slight mods), 2 (significant mods)
- `parent_image_hash`: Creates provenance chain (NULL for raw images)
- `transaction_id`: Groups multiple hashes from single camera submission (e.g., raw, processed, raw+GPS, processed+GPS all share same transaction_id and thus same camera_token validation)
- Camera-specific fields are NULL for software submissions and vice versa

### Implementation Pseudocode

```python
@app.post("/api/v1/submit")
async def submit_authentication_bundle(request: SubmissionRequest):
    # 1. Validate submission type
    if request.submission_type not in ["camera", "software"]:
        return error_response("INVALID_SUBMISSION_TYPE", 400)
    
    # 2. Route to appropriate handler
    if request.submission_type == "camera":
        return await handle_camera_submission(request)
    else:
        return await handle_software_submission(request)

async def handle_camera_submission(request: CameraSubmissionRequest):
    # 1. Validate camera-specific fields
    validate_camera_token(request.camera_token)
    validate_manufacturer_cert(request.manufacturer_cert)
    validate_timestamp(request.timestamp)
    
    # 2. Validate image hashes array
    for entry in request.image_hashes:
        validate_image_hash(entry.image_hash)
        if entry.modification_level not in [0, 1]:
            return error_response("INVALID_MODIFICATION_LEVEL", 400)
        if entry.modification_level == 1 and entry.parent_image_hash is None:
            return error_response("MISSING_PARENT_HASH", 400)
    
    # 3. Check for duplicates
    for entry in request.image_hashes:
        existing = await db.query(
            "SELECT submission_id FROM submissions WHERE image_hash = $1",
            entry.image_hash
        )
        if existing:
            return error_response("DUPLICATE_SUBMISSION", 409)
    
    # 4. Generate transaction_id for this camera submission
    transaction_id = uuid4()
    
    # 5. Store all image hashes (share same camera_token and transaction_id)
    submission_ids = []
    for entry in request.image_hashes:
        submission_id = await db.execute(
            """INSERT INTO submissions (
                submission_type, image_hash, modification_level, parent_image_hash,
                camera_token_ciphertext, camera_token_auth_tag, camera_token_nonce,
                table_id, key_index, manufacturer_authority_id, manufacturer_validation_endpoint,
                timestamp, transaction_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            RETURNING submission_id""",
            "camera", entry.image_hash, entry.modification_level, entry.parent_image_hash,
            request.camera_token.ciphertext, request.camera_token.auth_tag,
            request.camera_token.nonce, request.camera_token.table_id,
            request.camera_token.key_index, request.manufacturer_cert.authority_id,
            request.manufacturer_cert.validation_endpoint, request.timestamp,
            transaction_id
        )
        submission_ids.append(submission_id)
    
    # 6. Queue transaction for validation (validates once for all hashes)
    await queue_camera_transaction_for_validation(transaction_id)
    
    # 7. Return accepted response
    return {
        "status": "accepted",
        "submission_ids": submission_ids,
        "queue_position": await get_queue_position(),
        "estimated_batch_time": estimate_batch_time()
    }

async def handle_software_submission(request: SoftwareSubmissionRequest):
    # 1. Validate software-specific fields
    validate_image_hash(request.image_hash)
    validate_image_hash(request.parent_image_hash)  # Must be valid hash format
    validate_program_token(request.program_token)
    validate_developer_cert(request.developer_cert)
    
    # 2. Validate modification level
    if request.modification_level not in [1, 2]:
        return error_response("INVALID_MODIFICATION_LEVEL", 400)
    
    # 3. Check for duplicate
    existing = await db.query(
        "SELECT submission_id FROM submissions WHERE image_hash = $1",
        request.image_hash
    )
    if existing:
        return error_response("DUPLICATE_SUBMISSION", 409)
    
    # 4. Store submission
    submission_id = await db.execute(
        """INSERT INTO submissions (
            submission_type, image_hash, modification_level, parent_image_hash,
            program_token, developer_authority_id, developer_version_string,
            developer_validation_endpoint
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING submission_id""",
        "software", request.image_hash, request.modification_level,
        request.parent_image_hash, request.program_token,
        request.developer_cert.authority_id, request.developer_cert.version_string,
        request.developer_cert.validation_endpoint
    )
    
    # 5. Queue for validation
    await queue_software_submission_for_validation(submission_id)
    
    # 6. Return accepted response
    return {
        "status": "accepted",
        "submission_ids": [submission_id],
        "queue_position": await get_queue_position(),
        "estimated_batch_time": estimate_batch_time()
    }
```

---

## Component 2: Authority Integration (SMA & SSA)

### Purpose

Before batching images, validate tokens with the appropriate authority:
- **Camera submissions** → Simulated Manufacturer Authority (SMA)
- **Software submissions** → Simulated Software Authority (SSA)

This ensures only legitimate cameras and authorized software can authenticate images.

### Validation Worker

**Background Process:**
- Runs continuously, checking for pending submissions every 10 seconds
- Fetches submissions with `validation_status = 'pending'`
- Routes to appropriate authority based on `submission_type`
- Updates submission status based on authority response

### Camera Token Validation (SMA)

Camera submissions are validated by transaction (all hashes from same camera submission share validation).

**Endpoint:** `POST /sma/validate` (internal, on same server in Phase 1)

**Request:**
```json
{
  "validation_requests": [
    {
      "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
      "camera_token": {
        "ciphertext": "789abc...",
        "auth_tag": "def012...",
        "nonce": "345678...",
        "table_id": 147,
        "key_index": 523
      },
      "manufacturer_authority_id": "CANON_001"
    }
  ]
}
```

**Response:**
```json
{
  "validation_results": [
    {
      "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "pass",
      "manufacturer": "Canon",
      "validated_at": "2025-11-10T14:30:00Z"
    }
  ]
}
```

**SMA Status Values:**
- `pass` - Token valid, camera authenticated
- `fail_invalid_token` - Decryption failed
- `fail_unknown_camera` - NUC hash not in database
- `fail_wrong_table` - Camera not assigned this table

### Software Token Validation (SSA)

Software submissions are validated individually.

**Endpoint:** `POST /ssa/validate` (internal, on same server in Phase 1)

**Request:**
```json
{
  "validation_requests": [
    {
      "submission_id": "550e8400-e29b-41d4-a716-446655440004",
      "program_token": "sha256_hex_64_chars...",
      "developer_authority_id": "ADOBE_LIGHTROOM",
      "version_string": "Adobe Lightroom Classic 14.1.0"
    }
  ]
}
```

**Response:**
```json
{
  "validation_results": [
    {
      "submission_id": "550e8400-e29b-41d4-a716-446655440004",
      "status": "pass",
      "developer": "Adobe",
      "software_name": "Lightroom Classic",
      "version": "14.1.0",
      "validated_at": "2025-11-10T14:35:00Z"
    }
  ]
}
```

**SSA Status Values:**
- `pass` - Token valid, software version authenticated
- `fail_invalid_token` - Token hash doesn't match expected value
- `fail_unknown_software` - Developer/software not registered
- `fail_invalid_version` - Version string not recognized

### Status Updates

**On Success (`pass`):**
```sql
UPDATE submissions 
SET validation_status = 'validated',
    validated_at = NOW()
WHERE submission_id = ?
```

For camera transactions (update all submissions in transaction):
```sql
UPDATE submissions 
SET validation_status = 'validated',
    validated_at = NOW()
WHERE transaction_id = ?
```

**On Failure:**
```sql
UPDATE submissions 
SET validation_status = 'validation_failed',
    validation_error = ?
WHERE submission_id = ?
```

For camera transactions:
```sql
UPDATE submissions 
SET validation_status = 'validation_failed',
    validation_error = ?
WHERE transaction_id = ?
```

### Implementation Pseudocode

```python
async def validation_worker():
    """Background worker that validates pending submissions"""
    while True:
        # Process camera transactions
        await validate_pending_camera_transactions()
        
        # Process software submissions
        await validate_pending_software_submissions()
        
        await asyncio.sleep(10)

async def validate_pending_camera_transactions():
    """Validate pending camera transactions with SMA"""
    
    # Get unique transaction_ids with pending status
    pending_transactions = await db.query(
        """SELECT DISTINCT transaction_id, camera_token_ciphertext, 
           camera_token_auth_tag, camera_token_nonce, table_id, key_index,
           manufacturer_authority_id
           FROM submissions 
           WHERE submission_type = 'camera' 
           AND validation_status = 'pending'
           AND transaction_id IS NOT NULL
           ORDER BY received_at ASC 
           LIMIT 100"""
    )
    
    if not pending_transactions:
        return
    
    # Build validation request
    validation_requests = [
        {
            "transaction_id": str(txn.transaction_id),
            "camera_token": {
                "ciphertext": txn.camera_token_ciphertext,
                "auth_tag": txn.camera_token_auth_tag,
                "nonce": txn.camera_token_nonce,
                "table_id": txn.table_id,
                "key_index": txn.key_index
            },
            "manufacturer_authority_id": txn.manufacturer_authority_id
        }
        for txn in pending_transactions
    ]
    
    # Call SMA
    response = await http_client.post(
        "/sma/validate",
        json={"validation_requests": validation_requests}
    )
    
    # Update statuses for all submissions in each transaction
    for result in response.json()["validation_results"]:
        if result["status"] == "pass":
            await db.execute(
                "UPDATE submissions SET validation_status = 'validated', "
                "validated_at = NOW() WHERE transaction_id = $1",
                result["transaction_id"]
            )
        else:
            await db.execute(
                "UPDATE submissions SET validation_status = 'validation_failed', "
                "validation_error = $1 WHERE transaction_id = $2",
                result["status"], result["transaction_id"]
            )

async def validate_pending_software_submissions():
    """Validate pending software submissions with SSA"""
    
    pending = await db.query(
        """SELECT submission_id, program_token, developer_authority_id,
           developer_version_string
           FROM submissions 
           WHERE submission_type = 'software' 
           AND validation_status = 'pending'
           ORDER BY received_at ASC 
           LIMIT 100"""
    )
    
    if not pending:
        return
    
    # Build validation request
    validation_requests = [
        {
            "submission_id": str(sub.submission_id),
            "program_token": sub.program_token,
            "developer_authority_id": sub.developer_authority_id,
            "version_string": sub.developer_version_string
        }
        for sub in pending
    ]
    
    # Call SSA
    response = await http_client.post(
        "/ssa/validate",
        json={"validation_requests": validation_requests}
    )
    
    # Update statuses
    for result in response.json()["validation_results"]:
        if result["status"] == "pass":
            await db.execute(
                "UPDATE submissions SET validation_status = 'validated', "
                "validated_at = NOW() WHERE submission_id = $1",
                result["submission_id"]
            )
        else:
            await db.execute(
                "UPDATE submissions SET validation_status = 'validation_failed', "
                "validation_error = $1 WHERE submission_id = $2",
                result["status"], result["submission_id"]
            )
```

---

## Component 3: Batch Accumulator

### Purpose

Group validated submissions into batches of 1,000 images for efficient Merkle tree generation and blockchain posting.

### Batch Criteria

**Phase 1 (Simplified):**
- **Target size:** 1,000 images
- **Trigger:** When 1,000+ validated submissions exist
- **No time-based batching** (added in Phase 2)

**Phase 2+ (Production):**
- Target size: 5,000 images
- Minimum size: 1,000 images
- Maximum wait: 6 hours
- Force-post if 1,000+ images and 6+ hours since oldest

### Database Schema

```sql
CREATE TABLE batches (
    batch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    image_count INTEGER NOT NULL,
    merkle_root CHAR(64) NOT NULL,
    tree_depth INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    zksync_tx_hash CHAR(66),
    zksync_block_number BIGINT,
    confirmed_at TIMESTAMP,
    
    INDEX idx_status (status),
    INDEX idx_merkle_root (merkle_root),
    INDEX idx_created_at (created_at),
    UNIQUE (merkle_root)
);
```

**Status Values:**
- `pending` - Batch created, Merkle tree not yet generated
- `merkle_complete` - Merkle tree generated, ready for blockchain
- `posted` - Submitted to blockchain (mock in Phase 1)
- `finalized` - Blockchain transaction confirmed (Phase 2+)

### Batch Creation Logic

```python
async def batch_accumulator_worker():
    """Background worker that creates batches when threshold reached"""
    while True:
        # Count validated submissions not yet in batch
        count = await db.query_scalar(
            "SELECT COUNT(*) FROM submissions "
            "WHERE validation_status = 'validated' AND batch_id IS NULL"
        )
        
        if count >= 1000:
            await create_batch()
        
        await asyncio.sleep(60)  # Check every minute

async def create_batch():
    """Create a new batch from validated submissions"""
    # Lock rows to prevent race conditions
    submissions = await db.query(
        "SELECT submission_id, image_hash FROM submissions "
        "WHERE validation_status = 'validated' AND batch_id IS NULL "
        "ORDER BY received_at ASC "
        "LIMIT 1000 "
        "FOR UPDATE SKIP LOCKED"
    )
    
    if len(submissions) < 1000:
        return  # Not enough submissions
    
    # Create batch record
    batch_id = await db.execute(
        "INSERT INTO batches (image_count, merkle_root, tree_depth, status) "
        "VALUES ($1, $2, $3, $4) RETURNING batch_id",
        len(submissions),
        "0" * 64,  # Placeholder, will update after Merkle tree generation
        calculate_tree_depth(len(submissions)),
        "pending"
    )
    
    # Update submissions with batch_id
    submission_ids = [s.submission_id for s in submissions]
    await db.execute(
        "UPDATE submissions SET batch_id = $1, validation_status = 'in_batch' "
        "WHERE submission_id = ANY($2)",
        batch_id, submission_ids
    )
    
    # Trigger Merkle tree generation
    await generate_merkle_tree(batch_id)
    
    return batch_id

def calculate_tree_depth(image_count: int) -> int:
    """Calculate Merkle tree depth for given number of images"""
    import math
    return math.ceil(math.log2(image_count))
```

---

## Component 4: Merkle Tree Generator

### Purpose

Generate cryptographic Merkle trees from batches of image hashes. Store the root hash and all proof paths for efficient verification.

### Merkle Tree Algorithm

**Structure:**
- Binary tree where each leaf is an image hash
- Each parent node is SHA-256(left_child || right_child)
- Tree is balanced (pad to power of 2 if needed)
- Root hash represents entire batch

**Example Tree (8 images):**
```
                    ROOT
                   /    \
                  /      \
                 /        \
            H(01,23)    H(45,67)
            /    \      /    \
         H(0,1) H(2,3) H(4,5) H(6,7)
         /  \   /  \   /  \   /  \
        H0  H1 H2  H3 H4  H5 H6  H7
```

### Implementation

```python
import hashlib
from typing import List, Dict, Tuple

def generate_merkle_tree(image_hashes: List[str]) -> Tuple[str, Dict[str, List]]:
    """
    Generate Merkle tree from image hashes.
    
    Args:
        image_hashes: List of SHA-256 hashes (hex strings)
    
    Returns:
        merkle_root: Root hash (hex string)
        proofs: Dict mapping image_hash -> proof_path
    """
    # Convert to bytes
    leaves = [bytes.fromhex(h) for h in image_hashes]
    n = len(leaves)
    
    # Calculate tree depth and pad to power of 2
    depth = (n - 1).bit_length() if n > 0 else 0
    padded_size = 2 ** depth
    padding = [b'\x00' * 32] * (padded_size - n)
    leaves.extend(padding)
    
    # Build tree bottom-up
    tree = [leaves]  # Level 0 (leaves)
    
    current_level = leaves
    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1]
            parent = hashlib.sha256(left + right).digest()
            next_level.append(parent)
        tree.append(next_level)
        current_level = next_level
    
    merkle_root = tree[-1][0].hex()
    
    # Generate proofs for each original image (not padding)
    proofs = {}
    for idx in range(n):
        proof_path = []
        current_idx = idx
        
        for level in range(depth):
            sibling_idx = current_idx ^ 1  # XOR flips last bit
            if sibling_idx < len(tree[level]):
                sibling = tree[level][sibling_idx]
                proof_path.append({
                    "hash": sibling.hex(),
                    "position": "right" if current_idx % 2 == 0 else "left"
                })
            current_idx //= 2
        
        proofs[image_hashes[idx]] = proof_path
    
    return merkle_root, proofs

def verify_merkle_proof(image_hash: str, proof_path: List[Dict], merkle_root: str) -> bool:
    """
    Verify that image_hash is included in tree with given merkle_root.
    
    Args:
        image_hash: SHA-256 hash to verify (hex string)
        proof_path: List of {"hash": hex_string, "position": "left"|"right"}
        merkle_root: Expected root hash (hex string)
    
    Returns:
        True if proof is valid, False otherwise
    """
    current_hash = bytes.fromhex(image_hash)
    
    for step in proof_path:
        sibling = bytes.fromhex(step["hash"])
        if step["position"] == "left":
            current_hash = hashlib.sha256(sibling + current_hash).digest()
        else:
            current_hash = hashlib.sha256(current_hash + sibling).digest()
    
    return current_hash.hex() == merkle_root
```

### Proof Storage

```sql
CREATE TABLE merkle_proofs (
    proof_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID NOT NULL REFERENCES batches(batch_id) ON DELETE CASCADE,
    image_hash CHAR(64) NOT NULL,
    leaf_index INTEGER NOT NULL,
    proof_path JSONB NOT NULL,
    
    INDEX idx_image_hash (image_hash),
    INDEX idx_batch_id (batch_id),
    UNIQUE (batch_id, image_hash)
);
```

**Proof Path Format (JSONB):**
```json
[
  {"hash": "789abc...", "position": "right"},
  {"hash": "def012...", "position": "left"},
  {"hash": "345678...", "position": "right"}
]
```

### Integration with Batch Creation

```python
async def generate_merkle_tree_for_batch(batch_id: UUID):
    """Generate Merkle tree and store proofs for a batch"""
    # Get all image hashes in this batch
    submissions = await db.query(
        "SELECT image_hash FROM submissions WHERE batch_id = $1 ORDER BY received_at",
        batch_id
    )
    image_hashes = [s.image_hash for s in submissions]
    
    # Generate Merkle tree
    merkle_root, proofs = generate_merkle_tree(image_hashes)
    
    # Update batch with merkle_root
    await db.execute(
        "UPDATE batches SET merkle_root = $1, status = 'merkle_complete' "
        "WHERE batch_id = $2",
        merkle_root, batch_id
    )
    
    # Store all proofs
    for idx, image_hash in enumerate(image_hashes):
        await db.execute(
            "INSERT INTO merkle_proofs (batch_id, image_hash, leaf_index, proof_path) "
            "VALUES ($1, $2, $3, $4)",
            batch_id, image_hash, idx, json.dumps(proofs[image_hash])
        )
    
    # Verify random samples (quality check)
    import random
    samples = random.sample(image_hashes, min(10, len(image_hashes)))
    for sample_hash in samples:
        proof = proofs[sample_hash]
        assert verify_merkle_proof(sample_hash, proof, merkle_root), \
            f"Proof verification failed for {sample_hash}"
    
    # Trigger mock blockchain posting
    await mock_blockchain_post(batch_id, merkle_root)
```

---

## Component 5: Mock Blockchain

### Purpose

Simulate blockchain posting in Phase 1 without real zkSync integration. Generate fake transaction hashes and mark batches as "posted."

### Mock Transaction Generation

```python
async def mock_blockchain_post(batch_id: UUID, merkle_root: str):
    """
    Simulate posting Merkle root to blockchain.
    Generate fake transaction hash and update batch.
    """
    # Generate fake zkSync transaction hash
    # Format: 0xMOCK_ + first 60 chars of merkle_root
    mock_tx_hash = f"0xMOCK_{merkle_root[:60]}"
    
    # Generate fake block number (incrementing counter)
    last_block = await db.query_scalar(
        "SELECT MAX(zksync_block_number) FROM batches WHERE zksync_block_number IS NOT NULL"
    )
    mock_block_number = (last_block or 1000000) + 1
    
    # Update batch
    await db.execute(
        "UPDATE batches SET "
        "status = 'posted', "
        "zksync_tx_hash = $1, "
        "zksync_block_number = $2, "
        "confirmed_at = NOW() "
        "WHERE batch_id = $3",
        mock_tx_hash, mock_block_number, batch_id
    )
    
    print(f"Mock blockchain post: batch {batch_id} -> tx {mock_tx_hash}")
```

### Phase 2 Transition

In Phase 2, replace `mock_blockchain_post()` with real zkSync integration:

```python
# Phase 2: Real blockchain posting
async def zkSync_post_batch(batch_id: UUID, merkle_root: str):
    """Post Merkle root to zkSync smart contract"""
    from web3 import Web3
    
    w3 = Web3(Web3.HTTPProvider(ZKSYNC_RPC))
    contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=BIRTHMARK_ABI)
    
    # Build transaction
    tx = contract.functions.submitBatch(
        bytes.fromhex(merkle_root),
        image_count
    ).build_transaction({...})
    
    # Sign and send
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    
    # Update database
    await db.execute(
        "UPDATE batches SET zksync_tx_hash = $1, status = 'submitted' "
        "WHERE batch_id = $2",
        tx_hash.hex(), batch_id
    )
    
    return tx_hash.hex()
```

---

## Component 6: Verification API

### Endpoint: GET /api/v1/verify

**Purpose:** Query image authenticity by hash and return verification proof, modification level, and provenance information.

### Request

```
GET /api/v1/verify?image_hash=abc123def456...
```

**Parameters:**
- `image_hash` (required): SHA-256 hash of image (64 hex chars)

### Response Formats

**Verified Camera Image (Raw):**
```json
{
  "status": "verified",
  "image_hash": "abc123def456...",
  "submission_type": "camera",
  "modification_level": 0,
  "modification_level_description": "raw",
  "parent_image_hash": null,
  "authority": {
    "type": "manufacturer",
    "authority_id": "CANON_001",
    "name": "Canon"
  },
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "batch_index": 42,
  "timestamp": 1699564800,
  "merkle_root": "789abcdef012...",
  "merkle_proof": [
    {"hash": "345678...", "position": "right"},
    {"hash": "9abcde...", "position": "left"}
  ],
  "blockchain": {
    "network": "zkSync Era (Mock)",
    "tx_hash": "0xMOCK_789abcdef012...",
    "block_number": 1000042,
    "confirmed_at": "2025-11-10T14:35:00Z"
  }
}
```

**Verified Camera Image (Processed):**
```json
{
  "status": "verified",
  "image_hash": "789abc012def...",
  "submission_type": "camera",
  "modification_level": 1,
  "modification_level_description": "processed",
  "parent_image_hash": "abc123def456...",
  "authority": {
    "type": "manufacturer",
    "authority_id": "CANON_001",
    "name": "Canon"
  },
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "batch_index": 43,
  "timestamp": 1699564800,
  "merkle_root": "789abcdef012...",
  "merkle_proof": [...],
  "blockchain": {...}
}
```

**Verified Software Edit (Slight Modifications):**
```json
{
  "status": "verified",
  "image_hash": "fedcba987654...",
  "submission_type": "software",
  "modification_level": 1,
  "modification_level_description": "slight_modifications",
  "parent_image_hash": "789abc012def...",
  "authority": {
    "type": "developer",
    "authority_id": "ADOBE_LIGHTROOM",
    "version_string": "Adobe Lightroom Classic 14.1.0"
  },
  "batch_id": "550e8400-e29b-41d4-a716-446655440005",
  "batch_index": 12,
  "timestamp": null,
  "merkle_root": "def456abc789...",
  "merkle_proof": [...],
  "blockchain": {...}
}
```

**Verified Software Edit (Significant Modifications):**
```json
{
  "status": "verified",
  "image_hash": "012345abcdef...",
  "submission_type": "software",
  "modification_level": 2,
  "modification_level_description": "significant_modifications",
  "parent_image_hash": "fedcba987654...",
  "authority": {
    "type": "developer",
    "authority_id": "ADOBE_PHOTOSHOP",
    "version_string": "Adobe Photoshop 2025 26.0.0"
  },
  "batch_id": "550e8400-e29b-41d4-a716-446655440010",
  "batch_index": 88,
  "timestamp": null,
  "merkle_root": "111222333444...",
  "merkle_proof": [...],
  "blockchain": {...}
}
```

**Pending (Not Yet Batched):**
```json
{
  "status": "pending",
  "image_hash": "abc123def456...",
  "submission_type": "camera",
  "modification_level": 0,
  "message": "Image submitted but not yet posted to blockchain",
  "validation_status": "validated",
  "estimated_batch_time": "2025-11-10T16:00:00Z"
}
```

**Not Found:**
```json
{
  "status": "not_found",
  "image_hash": "abc123def456...",
  "message": "This image hash has not been authenticated via Birthmark Protocol"
}
```

**Validation Failed:**
```json
{
  "status": "validation_failed",
  "image_hash": "abc123def456...",
  "submission_type": "camera",
  "message": "Authentication failed",
  "error": "fail_unknown_camera"
}
```

### Modification Level Descriptions

| Level | Submission Type | Description |
|-------|----------------|-------------|
| 0 | camera | `raw` - Unprocessed sensor data |
| 1 | camera | `processed` - Camera-processed (JPEG/HEIC) |
| 1 | software | `slight_modifications` - Minor edits (white balance, exposure) |
| 2 | software | `significant_modifications` - Major edits (compositing, retouching) |

### Implementation

```python
@app.get("/api/v1/verify")
async def verify_image(image_hash: str):
    """Verify image authenticity and return proof with provenance"""
    # Validate hash format
    if not re.match(r'^[0-9a-fA-F]{64}$', image_hash):
        return error_response("INVALID_HASH_FORMAT", 400)
    
    image_hash = image_hash.lower()
    
    # Query database
    submission = await db.query_one(
        """SELECT s.*, b.merkle_root, b.zksync_tx_hash, 
           b.zksync_block_number, b.confirmed_at 
           FROM submissions s 
           LEFT JOIN batches b ON s.batch_id = b.batch_id 
           WHERE s.image_hash = $1""",
        image_hash
    )
    
    # Not found
    if not submission:
        return {
            "status": "not_found",
            "image_hash": image_hash,
            "message": "This image hash has not been authenticated via Birthmark Protocol"
        }
    
    # Validation failed
    if submission.validation_status == "validation_failed":
        return {
            "status": "validation_failed",
            "image_hash": image_hash,
            "submission_type": submission.submission_type,
            "message": "Authentication failed",
            "error": submission.validation_error
        }
    
    # Pending (not yet batched)
    if submission.batch_id is None:
        return {
            "status": "pending",
            "image_hash": image_hash,
            "submission_type": submission.submission_type,
            "modification_level": submission.modification_level,
            "message": "Image submitted but not yet posted to blockchain",
            "validation_status": submission.validation_status,
            "estimated_batch_time": estimate_batch_time()
        }
    
    # Get Merkle proof
    proof = await db.query_one(
        "SELECT proof_path, leaf_index FROM merkle_proofs WHERE image_hash = $1",
        image_hash
    )
    
    # Build authority info based on submission type
    if submission.submission_type == "camera":
        authority = {
            "type": "manufacturer",
            "authority_id": submission.manufacturer_authority_id,
            "name": submission.manufacturer_authority_id.split("_")[0]  # Extract manufacturer name
        }
    else:
        authority = {
            "type": "developer",
            "authority_id": submission.developer_authority_id,
            "version_string": submission.developer_version_string
        }
    
    # Map modification level to description
    mod_level_descriptions = {
        (0, "camera"): "raw",
        (1, "camera"): "processed",
        (1, "software"): "slight_modifications",
        (2, "software"): "significant_modifications"
    }
    mod_description = mod_level_descriptions.get(
        (submission.modification_level, submission.submission_type),
        "unknown"
    )
    
    # Return verified response
    return {
        "status": "verified",
        "image_hash": image_hash,
        "submission_type": submission.submission_type,
        "modification_level": submission.modification_level,
        "modification_level_description": mod_description,
        "parent_image_hash": submission.parent_image_hash,
        "authority": authority,
        "batch_id": str(submission.batch_id),
        "batch_index": proof.leaf_index,
        "timestamp": submission.timestamp,
        "merkle_root": submission.merkle_root,
        "merkle_proof": json.loads(proof.proof_path),
        "blockchain": {
            "network": "zkSync Era (Mock)" if submission.zksync_tx_hash.startswith("0xMOCK_") else "zkSync Era",
            "tx_hash": submission.zksync_tx_hash,
            "block_number": submission.zksync_block_number,
            "confirmed_at": submission.confirmed_at.isoformat() + "Z"
        }
    }
```

### Batch Verification Endpoint

**POST /api/v1/verify/batch**

Verify multiple images at once for efficiency.

**Request:**
```json
{
  "image_hashes": [
    "abc123...",
    "def456...",
    "789abc..."
  ]
}
```

**Response:**
```json
{
  "results": [
    {
      "image_hash": "abc123...",
      "status": "verified",
      // ... full verification data
    },
    {
      "image_hash": "def456...",
      "status": "not_found"
    }
  ]
}
```

**Implementation:**
```python
@app.post("/api/v1/verify/batch")
async def verify_batch(request: BatchVerifyRequest):
    """Verify multiple images at once"""
    if len(request.image_hashes) > 100:
        return error_response("BATCH_TOO_LARGE", 400, "Maximum 100 hashes per request")
    
    results = []
    for image_hash in request.image_hashes:
        result = await verify_image(image_hash)
        results.append(result)
    
    return {"results": results}
```

### Provenance Chain Tracking

**Purpose:** Trace the complete history of an image from original capture through all edits.

**Endpoint:** `GET /api/v1/provenance?image_hash=abc123def456...`

**Response:**
```json
{
  "image_hash": "012345abcdef...",
  "provenance_chain": [
    {
      "image_hash": "abc123def456...",
      "submission_type": "camera",
      "modification_level": 0,
      "modification_level_description": "raw",
      "authority": {
        "type": "manufacturer",
        "authority_id": "CANON_001"
      },
      "timestamp": 1699564800,
      "parent_image_hash": null
    },
    {
      "image_hash": "789abc012def...",
      "submission_type": "camera",
      "modification_level": 1,
      "modification_level_description": "processed",
      "authority": {
        "type": "manufacturer",
        "authority_id": "CANON_001"
      },
      "timestamp": 1699564800,
      "parent_image_hash": "abc123def456..."
    },
    {
      "image_hash": "fedcba987654...",
      "submission_type": "software",
      "modification_level": 1,
      "modification_level_description": "slight_modifications",
      "authority": {
        "type": "developer",
        "authority_id": "ADOBE_LIGHTROOM",
        "version_string": "Adobe Lightroom Classic 14.1.0"
      },
      "timestamp": null,
      "parent_image_hash": "789abc012def..."
    },
    {
      "image_hash": "012345abcdef...",
      "submission_type": "software",
      "modification_level": 2,
      "modification_level_description": "significant_modifications",
      "authority": {
        "type": "developer",
        "authority_id": "ADOBE_PHOTOSHOP",
        "version_string": "Adobe Photoshop 2025 26.0.0"
      },
      "timestamp": null,
      "parent_image_hash": "fedcba987654..."
    }
  ],
  "chain_length": 4,
  "original_capture": {
    "image_hash": "abc123def456...",
    "timestamp": 1699564800,
    "manufacturer": "CANON_001"
  },
  "total_modification_level": 2
}
```

**Implementation:**
```python
@app.get("/api/v1/provenance")
async def get_provenance_chain(image_hash: str):
    """Trace the complete provenance chain for an image"""
    
    # Build chain by following parent_image_hash references
    chain = []
    current_hash = image_hash
    max_depth = 100  # Prevent infinite loops
    
    for _ in range(max_depth):
        submission = await db.query_one(
            """SELECT image_hash, submission_type, modification_level,
               parent_image_hash, timestamp, manufacturer_authority_id,
               developer_authority_id, developer_version_string
               FROM submissions WHERE image_hash = $1""",
            current_hash
        )
        
        if not submission:
            break
        
        # Build entry
        if submission.submission_type == "camera":
            authority = {
                "type": "manufacturer",
                "authority_id": submission.manufacturer_authority_id
            }
        else:
            authority = {
                "type": "developer",
                "authority_id": submission.developer_authority_id,
                "version_string": submission.developer_version_string
            }
        
        chain.append({
            "image_hash": submission.image_hash,
            "submission_type": submission.submission_type,
            "modification_level": submission.modification_level,
            "modification_level_description": get_mod_description(
                submission.modification_level, submission.submission_type
            ),
            "authority": authority,
            "timestamp": submission.timestamp,
            "parent_image_hash": submission.parent_image_hash
        })
        
        # Move to parent
        if submission.parent_image_hash is None:
            break
        current_hash = submission.parent_image_hash
    
    # Reverse to show oldest first (original capture at top)
    chain.reverse()
    
    # Extract original capture info
    original = chain[0] if chain else None
    
    return {
        "image_hash": image_hash,
        "provenance_chain": chain,
        "chain_length": len(chain),
        "original_capture": {
            "image_hash": original["image_hash"],
            "timestamp": original["timestamp"],
            "manufacturer": original["authority"]["authority_id"]
        } if original and original["submission_type"] == "camera" else None,
        "total_modification_level": chain[-1]["modification_level"] if chain else None
    }
```

**Use Cases:**
- Verify image hasn't been modified beyond claimed level
- Trace back to original raw capture
- Identify all software that touched the image
- Detect if provenance chain is broken (missing parent)

---

## Database Schema Summary

### Complete Schema

```sql
-- Submissions table (unified for camera and software)
CREATE TABLE submissions (
    submission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_type VARCHAR(10) NOT NULL CHECK (submission_type IN ('camera', 'software')),
    image_hash CHAR(64) NOT NULL,
    modification_level INTEGER NOT NULL CHECK (modification_level >= 0 AND modification_level <= 2),
    parent_image_hash CHAR(64),
    
    -- Camera-specific fields (NULL for software submissions)
    camera_token_ciphertext TEXT,
    camera_token_auth_tag CHAR(32),
    camera_token_nonce CHAR(24),
    table_id INTEGER CHECK (table_id IS NULL OR (table_id >= 0 AND table_id < 250)),
    key_index INTEGER CHECK (key_index IS NULL OR (key_index >= 0 AND key_index < 1000)),
    manufacturer_authority_id VARCHAR(100),
    manufacturer_validation_endpoint TEXT,
    
    -- Software-specific fields (NULL for camera submissions)
    program_token CHAR(64),
    developer_authority_id VARCHAR(100),
    developer_version_string VARCHAR(200),
    developer_validation_endpoint TEXT,
    
    -- Common fields
    timestamp BIGINT,
    received_at TIMESTAMP NOT NULL DEFAULT NOW(),
    validation_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    validation_error TEXT,
    validated_at TIMESTAMP,
    batch_id UUID REFERENCES batches(batch_id),
    
    -- Transaction grouping (all hashes from same camera submission share this)
    transaction_id UUID,
    
    INDEX idx_image_hash (image_hash),
    INDEX idx_validation_status (validation_status),
    INDEX idx_received_at (received_at),
    INDEX idx_batch_id (batch_id),
    INDEX idx_parent_hash (parent_image_hash),
    INDEX idx_transaction_id (transaction_id),
    INDEX idx_modification_level (modification_level)
);

-- Batches table
CREATE TABLE batches (
    batch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    image_count INTEGER NOT NULL,
    merkle_root CHAR(64) NOT NULL,
    tree_depth INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    zksync_tx_hash CHAR(66),
    zksync_block_number BIGINT,
    confirmed_at TIMESTAMP,
    
    INDEX idx_status (status),
    INDEX idx_merkle_root (merkle_root),
    INDEX idx_created_at (created_at),
    UNIQUE (merkle_root)
);

-- Merkle proofs table
CREATE TABLE merkle_proofs (
    proof_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID NOT NULL REFERENCES batches(batch_id) ON DELETE CASCADE,
    image_hash CHAR(64) NOT NULL,
    leaf_index INTEGER NOT NULL,
    proof_path JSONB NOT NULL,
    
    INDEX idx_image_hash (image_hash),
    INDEX idx_batch_id (batch_id),
    UNIQUE (batch_id, image_hash)
);

-- SMA cameras table (see SMA specification)
CREATE TABLE sma_cameras (
    camera_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    camera_serial VARCHAR(100) UNIQUE NOT NULL,
    manufacturer VARCHAR(50) NOT NULL,
    nuc_hash CHAR(64) NOT NULL UNIQUE,
    table_ids INTEGER[3] NOT NULL,
    provisioned_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CHECK (array_length(table_ids, 1) = 3),
    INDEX idx_nuc_hash (nuc_hash)
);

-- SSA software table (see SSA specification)
CREATE TABLE ssa_software (
    software_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    authority_id VARCHAR(100) UNIQUE NOT NULL,
    developer_name VARCHAR(100) NOT NULL,
    software_name VARCHAR(100) NOT NULL,
    program_hash CHAR(64) NOT NULL,
    registered_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    INDEX idx_authority_id (authority_id)
);

-- SSA software versions table
CREATE TABLE ssa_software_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    software_id UUID NOT NULL REFERENCES ssa_software(software_id),
    version_string VARCHAR(200) NOT NULL,
    expected_token CHAR(64) NOT NULL,  -- SHA256(program_hash || version_string)
    registered_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    INDEX idx_software_id (software_id),
    UNIQUE (software_id, version_string)
);
```

---

## Technology Stack

### Backend Framework

**Recommended: Python with FastAPI**

**Rationale:**
- Async/await support for high concurrency
- Automatic API documentation (OpenAPI/Swagger)
- Fast development with type hints
- Excellent libraries for cryptography

**Alternative: Node.js with Express**
- Better zkSync SDK for Phase 2
- Good for real-time applications
- Large ecosystem

### Database

**PostgreSQL 14+**
- JSONB support for Merkle proofs
- Excellent indexing performance
- ACID compliance
- Strong community

### Libraries

**Python:**
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
asyncpg==0.29.0
pydantic==2.5.0
cryptography==41.0.7
```

**Cryptography:**
- `hashlib` (SHA-256, built-in)
- `cryptography` (AES-GCM)

### Development Tools

- **Testing:** pytest, pytest-asyncio
- **Linting:** ruff or pylint
- **Formatting:** black
- **Type checking:** mypy

---

## API Documentation

### OpenAPI/Swagger

FastAPI automatically generates interactive API documentation at:
- `/docs` - Swagger UI
- `/redoc` - ReDoc interface
- `/openapi.json` - OpenAPI schema

### Example Configuration

```python
from fastapi import FastAPI

app = FastAPI(
    title="Birthmark Protocol Aggregation Server",
    version="1.0.0",
    description="Phase 1 Mock Backend",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
```

---

## Testing Strategy

### Unit Tests

**Target Coverage:** 70%+

**Test Categories:**
- Request validation (all error cases)
- Merkle tree generation and verification
- Database queries
- Token validation logic

**Example Test:**
```python
def test_merkle_tree_generation():
    """Test Merkle tree generation with 1000 images"""
    image_hashes = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(1000)]
    merkle_root, proofs = generate_merkle_tree(image_hashes)
    
    # Root should be 64 hex chars
    assert len(merkle_root) == 64
    assert re.match(r'^[0-9a-f]{64}$', merkle_root)
    
    # Should have proofs for all images
    assert len(proofs) == 1000
    
    # Verify random samples
    for i in random.sample(range(1000), 10):
        image_hash = image_hashes[i]
        proof = proofs[image_hash]
        assert verify_merkle_proof(image_hash, proof, merkle_root)
```

### Integration Tests

**End-to-End Scenarios:**

**Camera Submission Tests:**
1. Submit camera bundle (4 hashes) → all validated → batch → verify each
2. Submit invalid camera token → SMA rejects → all 4 hashes not batched
3. Submit 250 camera submissions (1,000 hashes) → batch created automatically
4. Query verified camera image → returns correct proof and modification level
5. Query non-existent image → returns not_found

**Software Submission Tests:**
6. Submit software edit → SSA validates → batch → verify
7. Submit invalid program token → SSA rejects → not batched
8. Submit software edit with non-existent parent → stored (provenance broken)
9. Query verified software edit → returns correct authority and version string

**Provenance Chain Tests:**
10. Camera raw → Camera processed → Software edit → verify provenance chain
11. Query provenance for edited image → returns full chain to original capture
12. Modification levels increase correctly through chain

**Example Test:**
```python
@pytest.mark.asyncio
async def test_camera_submission_workflow():
    """Test complete camera submission workflow with 4 hashes"""
    
    # 1. Submit camera authentication bundle (raw, processed, raw+GPS, processed+GPS)
    response = await client.post("/api/v1/submit", json={
        "submission_type": "camera",
        "image_hashes": [
            {
                "image_hash": "abc123..." * 4,  # 64 chars
                "modification_level": 0,
                "parent_image_hash": None
            },
            {
                "image_hash": "def456..." * 4,
                "modification_level": 1,
                "parent_image_hash": "abc123..." * 4
            },
            {
                "image_hash": "789abc..." * 4,
                "modification_level": 0,
                "parent_image_hash": None
            },
            {
                "image_hash": "012def..." * 4,
                "modification_level": 1,
                "parent_image_hash": "789abc..." * 4
            }
        ],
        "camera_token": valid_camera_token,
        "manufacturer_cert": {
            "authority_id": "TEST_MFG_001",
            "validation_endpoint": "http://localhost:8000/sma/validate"
        },
        "timestamp": int(time.time())
    })
    assert response.status_code == 202
    submission_ids = response.json()["submission_ids"]
    assert len(submission_ids) == 4
    
    # 2. Wait for validation (all share same transaction_id)
    await asyncio.sleep(2)
    
    # 3. Check all are validated
    for sub_id in submission_ids:
        submission = await db.query_one(
            "SELECT validation_status FROM submissions WHERE submission_id = $1",
            sub_id
        )
        assert submission.validation_status == "validated"
    
    # 4. Verify image
    response = await client.get(f"/api/v1/verify?image_hash={'abc123...' * 4}")
    result = response.json()
    assert result["status"] == "verified" or result["status"] == "pending"
    assert result["modification_level"] == 0
    assert result["submission_type"] == "camera"

@pytest.mark.asyncio
async def test_software_submission_workflow():
    """Test software submission with provenance chain"""
    
    # Prerequisite: Camera image already submitted and validated
    parent_hash = "def456..." * 4  # Processed camera image
    
    # 1. Submit software edit
    response = await client.post("/api/v1/submit", json={
        "submission_type": "software",
        "image_hash": "fedcba..." * 4,
        "modification_level": 2,
        "parent_image_hash": parent_hash,
        "program_token": "abcdef..." * 4,
        "developer_cert": {
            "authority_id": "ADOBE_LIGHTROOM",
            "version_string": "Adobe Lightroom Classic 14.1.0",
            "validation_endpoint": "http://localhost:8000/ssa/validate"
        }
    })
    assert response.status_code == 202
    submission_id = response.json()["submission_ids"][0]
    
    # 2. Wait for validation
    await asyncio.sleep(2)
    
    # 3. Verify software edit
    response = await client.get(f"/api/v1/verify?image_hash={'fedcba...' * 4}")
    result = response.json()
    assert result["modification_level"] == 2
    assert result["submission_type"] == "software"
    assert result["authority"]["type"] == "developer"
    assert result["parent_image_hash"] == parent_hash

@pytest.mark.asyncio
async def test_provenance_chain():
    """Test complete provenance chain tracking"""
    
    # Setup: Camera → Software chain already submitted
    final_hash = "fedcba..." * 4
    
    # Get provenance
    response = await client.get(f"/api/v1/provenance?image_hash={final_hash}")
    result = response.json()
    
    assert result["chain_length"] >= 2
    assert result["original_capture"]["manufacturer"] == "TEST_MFG_001"
    assert result["provenance_chain"][0]["modification_level"] == 0
    assert result["provenance_chain"][-1]["modification_level"] == 2
```
### Load Tests

**Goals:**
- 100 concurrent camera submissions (400 hashes) without errors
- <100ms response time for verification queries
- 250 camera submissions (1,000 hashes) batched within 5 minutes

**Tool:** `locust` or `wrk`

**Example Locust Test:**
```python
from locust import HttpUser, task, between
import random
import hashlib
import time

class BirthmarkUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def submit_camera_image(self):
        """Simulate camera submission with 4 hashes"""
        raw_hash = hashlib.sha256(os.urandom(32)).hexdigest()
        processed_hash = hashlib.sha256(os.urandom(32)).hexdigest()
        raw_gps_hash = hashlib.sha256(os.urandom(32)).hexdigest()
        processed_gps_hash = hashlib.sha256(os.urandom(32)).hexdigest()
        
        self.client.post("/api/v1/submit", json={
            "submission_type": "camera",
            "image_hashes": [
                {"image_hash": raw_hash, "modification_level": 0, "parent_image_hash": None},
                {"image_hash": processed_hash, "modification_level": 1, "parent_image_hash": raw_hash},
                {"image_hash": raw_gps_hash, "modification_level": 0, "parent_image_hash": None},
                {"image_hash": processed_gps_hash, "modification_level": 1, "parent_image_hash": raw_gps_hash}
            ],
            "camera_token": self.get_valid_token(),
            "manufacturer_cert": {
                "authority_id": "TEST_MFG_001",
                "validation_endpoint": "http://localhost:8000/sma/validate"
            },
            "timestamp": int(time.time())
        })
    
    @task(1)
    def verify_image(self):
        self.client.get(f"/api/v1/verify?image_hash={self.known_hash}")
```

---

## Deployment

### Local Development

```bash
# 1. Install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Set up database
createdb birthmark_dev
psql birthmark_dev < schema.sql

# 3. Configure environment
cp .env.example .env
# Edit .env

# 4. Run server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 5. Run tests
pytest tests/ -v

# 6. Check coverage
pytest --cov=. --cov-report=html
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/birthmark
    depends_on:
      - postgres
  
  postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=birthmark
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Cloud Deployment

**Phase 1 (Testing):**
- Single server instance
- Managed PostgreSQL (AWS RDS, GCP Cloud SQL, or Digital Ocean)
- Simple deployment (no load balancing)

**Example: Digital Ocean**
- App Platform for API (auto-scaling)
- Managed PostgreSQL database
- ~$50/month for testing

---

## Monitoring & Operations

### Logging

**Log Levels:**
- INFO: Normal operations (submission received, batch created)
- WARNING: Non-critical issues (validation failed, retry needed)
- ERROR: Critical failures (database error, SMA down)

**Example Logging:**
```python
import logging

logger = logging.getLogger("birthmark")

@app.post("/api/v1/submit")
async def submit(...):
    logger.info(f"Received submission: {image_hash[:16]}...")
    
    try:
        # ... processing
        logger.info(f"Submission accepted: {submission_id}")
    except Exception as e:
        logger.error(f"Submission failed: {str(e)}", exc_info=True)
```

### Metrics

**Key Metrics to Track:**
- Submissions per minute
- Validation success rate
- Batch creation frequency
- Average time from submission to batch
- API response times (p50, p95, p99)

**Simple Metrics (Phase 1):**
```python
from collections import Counter

metrics = {
    "submissions_total": 0,
    "validations_passed": 0,
    "validations_failed": 0,
    "batches_created": 0
}

@app.get("/metrics")
async def get_metrics():
    return metrics
```

### Health Checks

```python
@app.get("/health")
async def health_check():
    # Check database connectivity
    try:
        await db.execute("SELECT 1")
        db_healthy = True
    except:
        db_healthy = False
    
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected",
        "timestamp": datetime.now().isoformat()
    }
```

---

## Next Steps for Implementation

### Week 1: Foundation
1. Set up FastAPI project structure
2. Create database schema (unified submissions table)
3. Implement submission API endpoint (both camera and software types)
4. Write unit tests for validation (both submission types)

### Week 2: Authority Integration (SMA & SSA)
1. Implement SMA validation endpoint (see SMA spec)
2. Implement SSA validation endpoint (software authority)
3. Create validation worker (routes by submission type)
4. Write integration tests for both authorities

### Week 3-4: Batching & Merkle Trees
1. Implement batch accumulation worker
2. Implement Merkle tree generation
3. Store proofs in database
4. Add mock blockchain posting
5. Test mixed batches (camera + software submissions)

### Week 5-6: Verification & Provenance
1. Implement verification API (with modification levels)
2. Implement provenance chain tracking endpoint
3. Create simple web UI for testing
4. Write comprehensive integration tests
5. Load testing

### Week 7-8: Deployment & Photography Club
1. Deploy to cloud
2. Set up monitoring
3. Raspberry Pi integration (camera submissions)
4. Software wrapper testing (software submissions)
5. Photography club testing

---

## Success Criteria

**Technical:**
- [ ] API accepts both camera and software submissions correctly
- [ ] Camera submissions store 4 hashes with single token validation
- [ ] 100% of valid camera tokens pass SMA validation
- [ ] 100% of valid program tokens pass SSA validation
- [ ] Batches created automatically at 1,000 image hashes
- [ ] Merkle proofs verify correctly 100% of time
- [ ] Verification API returns modification level and authority info
- [ ] Provenance chain tracking works end-to-end
- [ ] Verification API returns results in <100ms
- [ ] System handles 100 concurrent camera submissions (400 hashes)

**User Validation:**
- [ ] Photography club can capture and verify images
- [ ] Workflow takes <5 minutes per session
- [ ] Users understand modification levels (raw vs processed vs edited)
- [ ] Users can trace provenance back to original capture
- [ ] 80%+ satisfaction from user survey

**Authority Demo:**
- [ ] Can demonstrate complete Camera → Software flow in 5-minute video
- [ ] SMA code is clean and ready to share with manufacturers
- [ ] SSA code demonstrates software integration path
- [ ] Architecture clearly shows how both authorities validate independently

---

## Phase 2 Transition

**Ready for Phase 2 when:**
- All Phase 1 deliverables complete
- Photography club validates concept
- No critical bugs
- Database handles 10,000+ submissions (includes both camera and software)
- Both SMA and SSA demonstrate authority integration pattern
- Provenance chain tracking works reliably
- Team confident in architecture

**Phase 2 Changes:**
- Replace mock blockchain with real zkSync
- Add time-based batching (6-hour timeout)
- Increase batch size to 5,000 images
- Add Redis caching
- Implement load balancing
- Integrate with real manufacturer authorities (if partnerships secured)
- Expand software authority registration

---

**Document Status:** Ready for Implementation  
**Version:** 1.1 (Updated November 2025 - Added dual submission support)  
**Owner:** Samuel C. Ryan, The Birthmark Protocol Foundation  
**Next Review:** After Week 2 completion

**Key Changes in v1.1:**
- Added software submission support alongside camera submissions
- Unified submissions table with submission_type field
- Camera now submits 4 hashes (raw, processed, raw+GPS, processed+GPS) in single transaction
- Added modification_level tracking (0=raw, 1=processed/slight, 2=significant)
- Added parent_image_hash for provenance chain tracking
- Added SSA (Simulated Software Authority) integration
- Added developer_cert with version_string for software validation
- Added provenance chain tracking API endpoint
- Updated verification response to include modification level and authority info
- Updated testing strategy for both submission types
