# Birthmark Phase 1 Plan - Blockchain Node (Updated)

**Version:** 2.0 (Certificate Architecture)
**Date:** November 2025
**Phase:** Phase 1 (Blockchain Prototype)
**Timeline:** Complete
**Status:** ✅ Implemented

---

## Purpose

This document specifies the Blockchain Node component for Phase 1 development. The blockchain node is a merged aggregator+validator that:

1. Receives authentication bundles from cameras (certificate-based or legacy)
2. Validates with manufacturer authorities (MA) using self-routing
3. Accumulates validated submissions into batches
4. Stores full SHA-256 hashes directly on blockchain (no Merkle trees)
5. Provides verification API for querying image authenticity
6. Operates as part of institutional validator network

**Key Architecture Decision:** Instead of separate aggregation server + blockchain, we merged them into a single node that institutions deploy. Institutions that aggregate ARE the validators, creating aligned trust model.

**Phase 1 Scope:** Camera-only validation. Software validation (SSA) deferred to Phase 2.

---

## System Architecture

### Certificate-Based Flow (NEW - Recommended)

```
Camera (Raspberry Pi)
    │
    │ POST /api/v1/submit-cert
    │ {
    │   image_hash: "abc123...",
    │   camera_cert: "base64_DER_cert",  ← Contains all auth data!
    │   timestamp: 1700000000,
    │   bundle_signature: "base64..."
    │ }
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│           BLOCKCHAIN NODE (Merged Architecture)          │
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Certificate Submission API                        │  │
│  │  - Parse camera certificate (DER)                  │  │
│  │  - Extract Birthmark extensions:                   │  │
│  │    • maEndpoint: "http://ma.sony.com/validate"     │  │
│  │    • encryptedNUC: 60 bytes                        │  │
│  │    • keyTableID: 42                                │  │
│  │    • keyIndex: 137                                 │  │
│  │  - Validate certificate signature                  │  │
│  │  - Queue for MA validation                         │  │
│  └──────────────────┬─────────────────────────────────┘  │
│                     │                                     │
│                     │ Route to MA (from cert!)            │
│                     ▼                                     │
│  ┌────────────────────────────────────────────────────┐  │
│  │  MA Validation (Self-Routing)                      │  │
│  │  POST {maEndpoint}/validate-cert                   │  │
│  │  {                                                  │  │
│  │    camera_cert: "base64...",                       │  │
│  │    image_hash: "abc123..."  ← Not used in logic    │  │
│  │  }                                                  │  │
│  │                                                     │  │
│  │  MA validates:                                      │  │
│  │  - Parse certificate extensions                     │  │
│  │  - Check table exists                              │  │
│  │  - Validate encrypted NUC format                   │  │
│  │  - Phase 2: Decrypt & compare to registry         │  │
│  │  Returns: PASS/FAIL                                │  │
│  └──────────────────┬─────────────────────────────────┘  │
│                     │                                     │
│                     │ If PASS                             │
│                     ▼                                     │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Batch Accumulator                                 │  │
│  │  - Accumulate validated hashes                     │  │
│  │  - Batch when: 100+ hashes OR 30s timeout          │  │
│  │  - Validate transaction (no duplicates, etc.)      │  │
│  └──────────────────┬─────────────────────────────────┘  │
│                     │                                     │
│                     ▼                                     │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Consensus Engine (Single-Node / PoA)              │  │
│  │  - Phase 1: Auto-accept (single node)              │  │
│  │  - Phase 2+: Multi-node voting                     │  │
│  └──────────────────┬─────────────────────────────────┘  │
│                     │                                     │
│                     ▼                                     │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Block Storage                                     │  │
│  │  - Store full SHA-256 hashes (NOT Merkle roots!)   │  │
│  │  - Create block with transactions                  │  │
│  │  - Direct hash lookup (no proof needed)            │  │
│  └──────────────────┬─────────────────────────────────┘  │
│                     │                                     │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Verification API                                  │  │
│  │  GET /api/v1/verify/{image_hash}                   │  │
│  │  Returns:                                           │  │
│  │    - verified: true/false                          │  │
│  │    - timestamp: when stored                        │  │
│  │    - block_height: which block                     │  │
│  │    - aggregator: which institution                 │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │  PostgreSQL Database                               │  │
│  │  - blocks: blockchain blocks                       │  │
│  │  - transactions: batch transactions                │  │
│  │  - image_hashes: direct hash storage               │  │
│  │  - pending_submissions: validation queue           │  │
│  │  - node_state: blockchain state                    │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### Legacy Flow (Backward Compatible)

```
Camera (Raspberry Pi)
    │
    │ POST /api/v1/submit
    │ {
    │   image_hash: "abc123...",
    │   encrypted_nuc_token: "base64...",
    │   table_references: [1, 5, 9],
    │   key_indices: [42, 137, 891],
    │   timestamp: 1700000000,
    │   device_signature: "base64..."
    │ }
    │
    ▼
Blockchain Node → Fixed MA endpoint → PASS/FAIL → Same batching flow
```

---

## Key Architecture Changes from Original Plan

### What Changed

1. **Merged Aggregator + Blockchain**
   - Old: Separate aggregation server → zkSync smart contract
   - New: Single node combines aggregation + validation + block storage
   - Why: Institutions that aggregate ARE validators (aligned trust)

2. **Certificate-Based Authentication**
   - Old: Separate fields (encrypted_token, table_refs, key_indices)
   - New: Single X.509 certificate with Birthmark extensions
   - Why: Self-routing, self-contained, cleaner API

3. **Direct Hash Storage**
   - Old: Merkle trees → root on zkSync
   - New: Full SHA-256 hashes stored directly on blockchain
   - Why: Zero gas fees (institutions donate hosting), simpler verification

4. **Custom Blockchain**
   - Old: zkSync L2 with smart contracts
   - New: Python/PostgreSQL blockchain with PoA consensus
   - Why: Faster development, full control, zero fees

5. **Self-Routing to MA**
   - Old: Hardcoded MA endpoint in aggregator config
   - New: MA endpoint embedded in camera certificate
   - Why: Enables manufacturer federation, easier onboarding

### What Stayed the Same

1. **Privacy invariants**: MA never sees image hash in validation logic
2. **Batching**: Accumulate submissions before creating blocks
3. **Validation flow**: Camera → Aggregator → MA → Blockchain
4. **Verification**: Public API to query if hash exists on blockchain

---

## Database Schema

### PostgreSQL Tables

```sql
-- Blockchain blocks
CREATE TABLE blocks (
    block_height BIGINT PRIMARY KEY,
    block_hash CHAR(64) NOT NULL UNIQUE,
    previous_hash CHAR(64) NOT NULL,
    timestamp BIGINT NOT NULL,
    validator_id VARCHAR(255) NOT NULL,
    signature TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_block_hash (block_hash)
);

-- Batch transactions
CREATE TABLE transactions (
    tx_id SERIAL PRIMARY KEY,
    tx_hash CHAR(64) NOT NULL UNIQUE,
    block_height BIGINT REFERENCES blocks(block_height),
    aggregator_id VARCHAR(255) NOT NULL,
    batch_size INTEGER NOT NULL,
    signature TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Direct hash storage (no Merkle proofs!)
CREATE TABLE image_hashes (
    image_hash CHAR(64) PRIMARY KEY,
    tx_id INTEGER REFERENCES transactions(tx_id),
    block_height BIGINT REFERENCES blocks(block_height),
    timestamp BIGINT NOT NULL,
    gps_hash CHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_hash (image_hash),
    INDEX idx_timestamp (timestamp)
);

-- Pending submissions (pre-batching)
CREATE TABLE pending_submissions (
    id SERIAL PRIMARY KEY,
    image_hash CHAR(64) NOT NULL,
    encrypted_token BYTEA NOT NULL,
    table_references INTEGER[] NOT NULL,
    key_indices INTEGER[] NOT NULL,
    timestamp BIGINT NOT NULL,
    gps_hash CHAR(64),
    device_signature BYTEA,
    sma_validated BOOLEAN DEFAULT FALSE,
    validation_result VARCHAR(10),
    validation_attempted_at TIMESTAMP,
    batched BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_validated (sma_validated, batched)
);

-- Node state
CREATE TABLE node_state (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## API Endpoints

### Submission Endpoints

#### POST /api/v1/submit-cert (Certificate Format - NEW)

```json
Request:
{
  "image_hash": "abc123...",  // SHA-256 (64 hex chars)
  "camera_cert": "base64_DER_certificate",  // Contains all auth data
  "software_cert": null,  // Phase 2
  "timestamp": 1700000000,
  "gps_hash": "def456...",  // Optional
  "bundle_signature": "base64_ECDSA_signature"
}

Response (202 Accepted):
{
  "receipt_id": "uuid",
  "status": "pending_validation",
  "message": "Certificate submission received"
}
```

**Certificate Contains (via X.509 extensions):**
- `manufacturerID`: "sony_imaging"
- `maEndpoint`: "https://ma.sony.com/validate-cert"
- `encryptedNUC`: 60 bytes (AES-GCM encrypted NUC hash)
- `keyTableID`: 42 (single table ID)
- `keyIndex`: 137 (single key index)
- `deviceFamily`: "Sony IMX477 12MP"

#### POST /api/v1/submit (Legacy Format - Backward Compatible)

```json
Request:
{
  "image_hash": "abc123...",
  "encrypted_nuc_token": "base64...",  // 60 bytes
  "table_references": [1, 5, 9],  // 3 tables for privacy
  "key_indices": [42, 137, 891],  // Actual + 2 random
  "timestamp": 1700000000,
  "gps_hash": "def456...",
  "device_signature": "base64..."
}

Response (202 Accepted): Same as above
```

### Verification Endpoints

#### GET /api/v1/verify/{image_hash}

```json
Response (200 OK):
{
  "verified": true,
  "image_hash": "abc123...",
  "timestamp": 1700000000,
  "block_height": 12345,
  "aggregator": "university_of_oregon",
  "tx_hash": "def456...",
  "gps_hash": "ghi789..."  // If available
}

Response (404 Not Found):
{
  "verified": false,
  "image_hash": "abc123...",
  "timestamp": null,
  "block_height": null,
  "aggregator": null,
  "tx_hash": null
}
```

### Status Endpoints

#### GET /api/v1/status

```json
Response (200 OK):
{
  "node_id": "university_of_oregon",
  "block_height": 12345,
  "total_hashes": 1500000,
  "pending_submissions": 47,
  "last_block_time": "2025-11-17T10:30:00Z",
  "validator_nodes": 1,  // Phase 1
  "consensus_mode": "single",  // Phase 1
  "uptime": "99.9%"
}
```

---

## Certificate Extensions (NEW)

### Camera Certificate Structure

```
X.509 Certificate
├── Standard Fields
│   ├── Subject: CN=device_serial, O=Manufacturer
│   ├── Issuer: CN=Manufacturer CA
│   ├── Public Key: ECDSA P-256
│   ├── Validity: 2 years
│   └── Signature: CA signature
│
└── Birthmark Extensions (OID: 1.3.6.1.4.1.60000.1.*)
    ├── manufacturerID (1.1): UTF8String
    ├── maEndpoint (1.2): UTF8String (URL)
    ├── encryptedNUC (1.3): OCTET STRING (60 bytes)
    ├── keyTableID (1.4): INTEGER (0-2499)
    ├── keyIndex (1.5): INTEGER (0-999)
    └── deviceFamily (1.6): UTF8String
```

### Why Certificates?

1. **Self-Routing**: MA endpoint embedded in cert
2. **Self-Contained**: All auth data in one document
3. **Standard Format**: Industry-standard X.509
4. **Federation-Ready**: Each manufacturer specifies their MA
5. **Cleaner API**: Single field vs multiple fields

---

## Validation Flow

### Certificate-Based Validation

1. **Camera sends certificate bundle** to blockchain node
2. **Node parses certificate** (DER format)
3. **Node extracts extensions**:
   - MA endpoint: `https://ma.sony.com/validate-cert`
   - Encrypted NUC: 60 bytes
   - Key table ID: 42
   - Key index: 137
4. **Node routes to MA** (extracted from certificate!)
5. **MA validates**:
   - Parse certificate extensions
   - Check table 42 exists
   - Validate key index 137 in range (0-999)
   - Validate encrypted NUC is 60 bytes
   - Phase 2: Decrypt NUC and compare to registry
6. **MA returns** PASS/FAIL
7. **If PASS**: Queue for batching
8. **Every 30s or 100 hashes**: Create block and store

### Legacy Validation

1. Camera sends separate fields to blockchain node
2. Node routes to fixed MA endpoint
3. MA validates token (separate encrypted_nuc_token field)
4. Same batching and storage flow

---

## Batching and Consensus

### Batching Rules

- **Minimum batch size**: 1 (for testing)
- **Maximum batch size**: 1000
- **Timeout**: 30 seconds since first submission
- **Trigger**: Whichever comes first (100 hashes OR 30s)

### Phase 1 Consensus (Single Node)

```python
class SingleNodeConsensus:
    async def propose_block(self, batch):
        # Validate transaction
        is_valid, error = await validate_transaction(batch)
        if not is_valid:
            logger.error(f"Invalid transaction: {error}")
            return None

        # Auto-accept (no voting needed)
        block = await create_block(batch)
        return block
```

### Phase 2+ Consensus (Proof-of-Authority)

```python
class ProofOfAuthorityConsensus:
    async def propose_block(self, batch):
        # Validate transaction
        is_valid, error = await validate_transaction(batch)
        if not is_valid:
            return None

        # Broadcast to validator set
        votes = await broadcast_to_validators(batch)

        # Require 2/3+ majority
        if votes >= (total_validators * 2 // 3):
            block = await create_block(batch)
            return block

        return None
```

---

## Deployment

### Docker Compose

```yaml
version: '3.8'

services:
  blockchain-node:
    build: .
    ports:
      - "8545:8545"  # API
      - "26656:26656"  # P2P (Phase 2)
    environment:
      - NODE_ID=university_of_oregon
      - DATABASE_URL=postgresql://user:pass@db:5432/birthmark
      - SMA_VALIDATION_ENDPOINT=http://localhost:8001/validate-cert
      - BATCH_SIZE_MIN=1
      - BATCH_SIZE_MAX=1000
      - CONSENSUS_MODE=single
    depends_on:
      - db
    volumes:
      - blockchain-data:/app/data

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=birthmark_chain
      - POSTGRES_USER=birthmark
      - POSTGRES_PASSWORD=birthmark
    volumes:
      - postgres-data:/var/lib/postgresql/data

volumes:
  blockchain-data:
  postgres-data:
```

### Startup Commands

```bash
# Initialize database
alembic upgrade head

# Create genesis block (first time only)
python scripts/init_genesis.py

# Start node
uvicorn src.main:app --host 0.0.0.0 --port 8545
```

---

## Testing

### End-to-End Test Flow

```bash
# 1. Start SMA
cd packages/sma
uvicorn src.main:app --port 8001

# 2. Provision device (generates certificate with extensions)
curl -X POST http://localhost:8001/api/v1/devices/provision \
  -H "Content-Type: application/json" \
  -d '{"device_serial": "TEST-001", "device_family": "Raspberry Pi"}'

# Save provisioning data to camera-pi/data/provisioning.json

# 3. Start blockchain node
cd packages/blockchain
uvicorn src.main:app --port 8545

# 4. Capture image with certificate
cd packages/camera-pi
python -m camera_pi capture --use-certificates

# 5. Verify hash on blockchain
curl http://localhost:8545/api/v1/verify/{IMAGE_HASH}
```

### Expected Results

- ✅ Certificate generated with Birthmark extensions
- ✅ Camera submits certificate to blockchain
- ✅ Blockchain parses certificate and extracts MA endpoint
- ✅ Blockchain routes to MA for validation
- ✅ MA validates certificate format (Phase 1)
- ✅ Hash stored in pending_submissions
- ✅ After 30s, batch created and block stored
- ✅ Hash verifiable via /api/v1/verify endpoint

---

## Phase 1 Limitations

1. **Single node**: No distributed consensus yet
2. **Format validation only**: MA checks format, not cryptographic validity
3. **Camera-only**: No software (SSA) validation
4. **Local deployment**: No federation yet
5. **No CRL/OCSP**: Certificate revocation not implemented
6. **Test blockchain**: Will be replaced for production

---

## Phase 2 Upgrades

1. **Multi-node consensus**: PoA with 5-10 validator institutions
2. **Full cryptographic validation**: MA decrypts NUC and compares to registry
3. **Software validation**: SSA integration for edited images
4. **P2P networking**: Gossip protocol for block propagation
5. **Certificate revocation**: CRL/OCSP support
6. **Production blockchain**: Persistent chain for real deployments

---

## Success Metrics

### Phase 1 Targets

- ✅ 99%+ uptime for blockchain node
- ✅ <5 second submission to storage time
- ✅ Zero gas fees (institutions donate hosting)
- ✅ <100ms verification query response
- ✅ 100% of valid certificates pass validation
- ✅ 0% false positives/negatives

### Achieved

- ✅ Certificate infrastructure complete
- ✅ SMA generates certificates with extensions
- ✅ Blockchain accepts both formats
- ✅ MA validates certificates
- ✅ Direct hash storage and verification
- ✅ Ready for hardware testing

---

**Status**: Phase 1 blockchain node implementation complete. Certificate architecture fully integrated. Ready for hardware testing and Phase 2 multi-node consensus.
