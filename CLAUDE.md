Birthmark Standard - Phase 1 Development Context

**Last Updated:** December 11, 2025  
**Current Status:** Camera authentication pipeline validated ✅  
**Next:** Building Submission Server and Simulated Manufacturer Authority  
**Repository:** github.com/Birthmark-Standard/Birthmark

---

## Project Overview

The Birthmark Standard is open-source infrastructure that proves images originated from legitimate camera hardware rather than AI generation. Unlike C2PA (which embeds metadata that gets stripped by social media), Birthmark stores authentication records on an independent blockchain operated by journalism organizations, surviving all forms of metadata loss.

**Phase 1 Goal:** Build working prototype with Raspberry Pi camera proving complete authentication pipeline from sensor capture through blockchain verification.

**Organization:** The Birthmark Standard Foundation (501(c)(3) pending)  
**Founder:** Samuel C. Ryan (samryan.pdx@proton.me)

---

## Core Innovation

**Problem:** C2PA metadata is stripped when images are shared on social media (95% of authenticated images lose their credentials).

**Solution:** Store authentication records on blockchain independent of image files. Anyone can hash an image and query the blockchain to verify provenance, regardless of compression, conversion, or platform sharing.

**Key Differentiator:** Blockchain operated by journalism organizations (NPPA, IFCN, CPJ, Bellingcat), not tech companies. Trust distributed across aligned institutions with reputational stakes in credibility.

---

## System Architecture (Phase 1)
```
         ┌─────────────────┐
         │  Camera (Pi 4)  │
         │  + HQ Camera    │
         │  + Simulated SE │
         └────────┬────────┘
                  │ POST /submit
                  ▼
         ┌─────────────────────────┐        ┌───────────────────┐
         │  Submission Server      │◀──────▶│ Manufacturer      │
         │  (FastAPI + PostgreSQL) │ validate│ Authority (SMA)   │
         └─────────────┬───────────┘  cert  └───────────────────┘
                       │                            PASS/FAIL
                       │ (if PASS)
                       ▼
            ┌──────────────────────┐
            │ Birthmark Media      │
            │ Registry             │
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │  Web Verifier        │
            │  (React app)         │
            └──────────────────────┘
```

### Data Flow

1. **Camera captures image**
   - Hash raw Bayer sensor data (SHA-256)
   - Process through ISP, hash processed image
   - Generate simulated NUC hash
   - Encrypt NUC hash with random table/key selection
   - Create manufacturer certificate
   - Submit to Submission Server

2. **Submission Server receives submission**
   - Extract manufacturer certificate
   - Route certificate to Manufacturer Authority
   - Authority validates camera authenticity (returns PASS/FAIL)
   - If PASS: post image hashes to Birthmark Media Registry

3. **Registry stores record**
   - Coalition blockchain nodes validate and store
   - Record becomes permanent and queryable
   - Survives all metadata stripping

4. **Public verification**
   - User hashes image locally
   - Query Birthmark Media Registry
   - Returns: validated/modified status + provenance chain

---

## Phase 1 Scope

### ✅ Completed (December 11, 2025)

**Camera Package:**
- Raw Bayer capture from Sony IMX477 (4056x3040)
- ISP-processed image capture
- SHA-256 hashing of both raw and processed
- Simulated Secure Element with AES-256-GCM
- HKDF key derivation (3 master keys: tables 847, 1203, 1654)
- Manufacturer certificate generation
- Complete authentication pipeline validated

**Test Results:**
```
Raw hash: a9d1dbb063ffd40ed3da020e14aa994a...
Processed hash: 29d6c8498815c58cb274cb4878cd3f4f...
Certificate: Table 1203, Key 452, encrypted NUC hash
```

### 🚧 Current Work

**Submission Server:** FastAPI server accepting camera/software submissions
**SMA:** Validation endpoint for camera tokens
**Integration:** End-to-end flow from camera to validation

### 📋 Remaining Phase 1

- Birthmark Media Registry (Cosmos SDK single-node testnet)
- Web verification interface (React app)
- Complete end-to-end demonstration
- Documentation for Phase 2 handoff

---

## Repository Structure
```
birthmark/
├── packages/
│   ├── camera-pi/              # Raspberry Pi camera implementation
│   │   ├── src/
│   │   │   ├── capture.py              # Camera capture & hashing
│   │   │   ├── secure_element.py       # Simulated SE (Phase 1)
│   │   │   ├── certificate.py          # Certificate generation
│   │   │   └── submit.py               # Submission Server client
│   │   ├── tests/
│   │   └── README.md
│   │
│   ├── submission-server/      # Entry point for authentications
│   │   ├── src/
│   │   │   ├── api.py                  # FastAPI endpoints
│   │   │   ├── validation.py           # Authority routing
│   │   │   ├── blockchain.py           # Registry posting
│   │   │   └── database.py             # PostgreSQL models
│   │   ├── tests/
│   │   └── README.md
│   │
│   ├── sma/                    # Simulated Manufacturer Authority
│   │   ├── src/
│   │   │   ├── server.py               # Validation API
│   │   │   ├── keys.py                 # Key table management
│   │   │   ├── crypto.py               # Decryption & validation
│   │   │   └── provision.py            # Camera provisioning
│   │   ├── tests/
│   │   └── README.md
│   │
│   ├── registry/               # Birthmark Media Registry
│   │   ├── node/                       # Cosmos SDK setup
│   │   ├── contracts/                  # Smart contract logic
│   │   ├── scripts/                    # Deployment scripts
│   │   └── README.md
│   │
│   └── verifier/               # Verification interface
│       ├── web/                        # React application
│       ├── api/                        # Query library
│       └── README.md
│
├── shared/                     # Common code across packages
│   ├── types/                          # Data structures
│   ├── crypto/                         # Cryptographic utilities
│   └── protocols/                      # API specifications
│
├── docs/
│   ├── architecture/                   # Technical diagrams
│   ├── specs/                          # Detailed specifications
│   └── phase1/                         # Phase 1 documentation
│
├── CLAUDE.md                   # This file - Phase 1 context
├── README.md                   # Project overview
└── PHASE1_SUCCESS.md           # Milestone tracking
```

---

## Hardware Configuration

### Raspberry Pi 4 Setup

**Components:**
- Raspberry Pi 4 Model B (4GB RAM)
- Sony IMX477 HQ Camera (12.3 MP, 7.9mm sensor)
- 6mm CS-mount lens
- LetsTrust TPM SLB 9670 (deferred - hardware issue)
- 32GB microSD card (A2 rated)

**Camera Connection:**
- **CSI Port 2** (near Ethernet jack) ✅ CORRECT
- Port 1 is for displays only
- 15-pin ribbon cable

**TPM Status:**
- Hardware communication issue (deferred)
- Using Simulated Secure Element for Phase 1
- Same cryptographic algorithms and data structures
- Production migration path: swap SimulatedSecureElement → HardwareSecureElement

**Software:**
- Raspberry Pi OS (64-bit, Bookworm)
- Python 3.11
- picamera2 library
- libcamera v0.6.0+rpt20251202

---

## Data Structures

### Camera Submission (GPS Disabled - Default)
```python
{
    "submission_type": "camera",
    "image_hashes": [
        {
            "image_hash": "a9d1dbb063ffd40ed3da020e14aa994a...",  # Raw
            "modification_level": 0,
            "parent_image_hash": None
        },
        {
            "image_hash": "29d6c8498815c58cb274cb4878cd3f4f...",  # Processed
            "modification_level": 1,
            "parent_image_hash": "a9d1dbb063ffd40ed3da020e14aa994a..."
        }
    ],
    "manufacturer_cert": {
        "authority_id": "SIMULATED_CAMERA_001",
        "validation_endpoint": "http://localhost:8001/validate",
        "camera_token": {
            "ciphertext": "2f358ac4a60fe6726e8a853161c8c4d8...",
            "nonce": "6acb56f767fc4f1f52428f0a..."
        },
        "key_reference": {
            "table_id": 1203,
            "key_index": 452
        }
    },
    "timestamp": 1699564800
}
```

### Registry Record
```python
{
    "image_hash": "sha256_hex_64_chars",
    "submission_type": "camera" | "software",
    "modification_level": 0 | 1 | 2,  # Raw | Validated | Modified
    "modification_display": "Validated Raw" | "Validated" | "Modified",
    "parent_image_hash": "sha256_hex_64_chars" | None,
    "authority_id": "SIMULATED_CAMERA_001",
    "submission_server_id": "server_public_key",
    "timestamp": 1699564800,  # When server processed, not capture time
    "block_number": 12345
}
```

---

## API Specifications

### Submission Server

**POST /submit**
```json
// Camera submission
{
    "submission_type": "camera",
    "image_hashes": [...],
    "manufacturer_cert": {...},
    "timestamp": 1699564800
}

// Response
{
    "submission_id": "uuid",
    "status": "pending_validation"
}
```

**GET /status/{submission_id}**
```json
{
    "submission_id": "uuid",
    "status": "validated" | "rejected" | "pending",
    "authority_response": "PASS" | "FAIL" | null,
    "blockchain_posted": true | false
}
```

### Simulated Manufacturer Authority

**POST /validate**
```json
// Request (from Submission Server)
{
    "camera_token": {
        "ciphertext": "hex_string",
        "nonce": "hex_string"
    },
    "key_reference": {
        "table_id": 1203,
        "key_index": 452
    }
}

// Response
{
    "valid": true | false,
    "authority_validation": "PASS" | "FAIL",
    "failure_reason": null | "Invalid token" | "Unknown camera"
}
```

### Birthmark Media Registry

**POST /submit-batch** (from Submission Server)
```json
{
    "image_hashes": [
        {
            "hash": "sha256_hex",
            "modification_level": 0,
            "parent_hash": null,
            "authority_id": "SIMULATED_CAMERA_001",
            "timestamp": 1699564800
        }
    ]
}
```

**GET /verify/{image_hash}** (public)
```json
{
    "verified": true,
    "modification_level": 1,
    "modification_display": "Validated",
    "authority_id": "SIMULATED_CAMERA_001",
    "timestamp": 1699564800,
    "block_number": 12345,
    "provenance_chain": [...]
}
```

---

## Cryptographic Standards

### Hashing
- Algorithm: SHA-256
- Input: Raw Bayer sensor data OR processed image bytes
- Output: 64 character hex string
- Performance: <100ms on Raspberry Pi 4

### Key Tables (SMA)
- Total tables: 2,500
- Keys per table: 1,000
- Key size: 256-bit
- Derivation: HKDF-SHA256 from master keys
- Camera assignment: 3 random tables per device

### Encryption
- Algorithm: AES-256-GCM (authenticated encryption)
- Purpose: Encrypt NUC hash for transmission
- Authentication tag: 16 bytes (prevents tampering)
- Nonce: 12 bytes (unique per encryption)

---

## Database Schemas

### Submission Server (PostgreSQL)
```sql
-- Pending submissions awaiting validation
CREATE TABLE submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_type VARCHAR(20) NOT NULL,  -- 'camera' or 'software'
    image_hashes JSONB NOT NULL,           -- Array of hash objects
    certificate JSONB NOT NULL,            -- Manufacturer/developer cert
    timestamp BIGINT NOT NULL,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Validation status
    validation_status VARCHAR(20) DEFAULT 'pending',  -- pending/validated/rejected
    authority_response JSONB,
    blockchain_posted BOOLEAN DEFAULT FALSE,
    blockchain_block BIGINT
);

CREATE INDEX idx_validation_status ON submissions(validation_status);
CREATE INDEX idx_timestamp ON submissions(timestamp);
```

### SMA (PostgreSQL)
```sql
-- Key tables (2,500 tables with master keys)
CREATE TABLE key_tables (
    table_id INTEGER PRIMARY KEY CHECK (table_id >= 0 AND table_id < 2500),
    master_key BYTEA NOT NULL  -- 256-bit key for HKDF
);

-- Registered cameras (provisioned during manufacturing)
CREATE TABLE cameras (
    serial_number VARCHAR(50) PRIMARY KEY,
    nuc_hash BYTEA NOT NULL,                 -- SHA-256 of NUC map (32 bytes)
    table_ids INTEGER[3] NOT NULL,           -- 3 assigned tables
    provisioned_at TIMESTAMP NOT NULL,
    camera_model VARCHAR(100),
    firmware_version VARCHAR(50)
);

-- Validation audit log
CREATE TABLE validation_log (
    id SERIAL PRIMARY KEY,
    encrypted_token BYTEA NOT NULL,
    table_id INTEGER NOT NULL,
    key_index INTEGER NOT NULL,
    validation_result VARCHAR(10) NOT NULL,  -- 'PASS' or 'FAIL'
    failure_reason TEXT,
    validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Privacy Architecture

### What Different Parties See

**Camera Manufacturer (via SMA):**
- ✅ "One of my cameras authenticated a photo"
- ✅ Authentication frequency per camera (usage statistics)
- ❌ Which specific camera (table shared by ~12,000 devices)
- ❌ Image content or hashes
- ❌ Precise capture timestamp
- ❌ GPS location

**Submission Server:**
- ✅ Image hashes (to post to Registry)
- ✅ Certificate table/key reference
- ✅ Manufacturer validation result (PASS/FAIL)
- ❌ Which specific camera (table anonymity)
- ❌ NUC hash (encrypted, cannot decrypt)
- ❌ Image content

**Registry (Blockchain Nodes):**
- ✅ Image hashes (SHA-256, irreversible)
- ✅ Modification levels
- ✅ Authority IDs
- ✅ Timestamps (server processing time, not capture time)
- ❌ Image content
- ❌ Photographer identity
- ❌ Specific camera serial numbers

**Public Verifier:**
- ✅ "This hash was authenticated by this manufacturer on this date"
- ❌ Who took the photo
- ❌ Where (unless GPS-enabled version and they have that image)
- ❌ Which specific camera unit

### Privacy Mechanisms

1. **Key Table Anonymity:** Camera randomly selects from 3 tables shared by ~12,000 devices
2. **Encrypted Tokens:** NUC hash encrypted, never transmitted in plaintext
3. **Hash-Only Storage:** Image content never transmitted or stored anywhere
4. **Separated Concerns:** No single entity has complete information
5. **Timestamp Obfuscation:** Registry timestamps reflect server processing, not photo capture
6. **GPS Opt-In:** Location hashing disabled by default, user must explicitly enable

---

## Testing Requirements

### Unit Tests
- Cryptographic operations (hash, encrypt, decrypt)
- Database operations (CRUD, queries)
- API endpoint validation
- Certificate parsing and validation
- Key derivation consistency

### Integration Tests
- Camera → Submission Server flow
- Submission Server → SMA validation
- Submission Server → Registry posting
- End-to-end verification query

### Performance Benchmarks
- Camera capture + hash: <100ms
- Submission Server response: <200ms
- SMA validation: <100ms
- Registry query: <500ms
- End-to-end camera to verified: <5s

---

## Development Conventions

### Code Style
- Python: Black formatter, type hints required
- Docstrings: Google style for all public functions
- Classes: PascalCase, Functions: snake_case
- Constants: UPPER_SNAKE_CASE

### Git Workflow
- Feature branches from `main`
- Descriptive commit messages (Conventional Commits)
- Pull requests with code review
- Semantic versioning (v0.x.x for Phase 1)

### Security Practices
- No secrets in code (use environment variables)
- Input validation on all APIs
- Rate limiting on public endpoints
- Audit logging for sensitive operations
- Constant-time comparisons for crypto

---

## Common Development Tasks

### Running Submission Server
```bash
cd packages/submission-server
pip install -e ".[dev]"
cp .env.example .env
# Edit .env with database credentials
alembic upgrade head
uvicorn src.api:app --reload --port 8000
```

### Running SMA
```bash
cd packages/sma
pip install -r requirements.txt
python scripts/generate_key_tables.py  # First time only
uvicorn src.server:app --reload --port 8001
```

### Running Camera
```bash
cd packages/camera-pi
pip install -r requirements.txt
python scripts/provision_camera.py  # First time only
python src/main.py
```

### Running Integration Tests
```bash
# Start all services first (submission-server, sma, registry)
pytest tests/integration/ -v
```

---

## Known Limitations (Phase 1)

### Hardware
- ❌ TPM hardware issue (using simulated SE)
- ❌ No GPS module installed
- ⚠️ Single camera system (no fleet management)

### Software
- ⚠️ Simulated SE keys stored in files (no physical tamper resistance)
- ⚠️ Local network only (no internet connectivity)
- ⚠️ Single-node blockchain (testnet)
- ⚠️ Mock provisioning (no real manufacturing integration)

### Scope
- Phase 1 proves concept with prototype hardware
- Phase 2 will address production deployment
- Phase 3 will integrate with real manufacturers

---

## Success Metrics (Phase 1)

### Technical Validation
- ✅ Camera captures raw Bayer and hashes correctly
- ✅ Complete authentication certificate generation
- [ ] Submission Server accepts and validates submissions
- [ ] SMA validates camera tokens without seeing image hashes
- [ ] Registry stores and returns verification results
- [ ] End-to-end flow: camera → submission → validation → registry → verification

### Performance
- [ ] Camera overhead <100ms
- [ ] Submission Server response <200ms
- [ ] SMA validation <100ms
- [ ] Registry query <500ms
- [ ] Zero false positives or negatives

### Documentation
- [ ] Complete API documentation
- [ ] Architecture diagrams
- [ ] Deployment guides
- [ ] Security threat model
- [ ] Phase 2 handoff documentation

---

## Phase 2 Transition Plan

### What Moves to phase1 Branch
- Simulated Secure Element implementation
- Local-only testing infrastructure
- Mock provisioning scripts
- Single-node blockchain testnet
- Phase 1-specific documentation

### What Stays in main Branch
- Abstract secure element interface
- Core data structures
- API specifications
- Cryptographic utilities
- Architecture documentation

### Branching Strategy
```bash
# When Phase 1 complete:
git checkout -b phase1
git tag v1.0-phase1-complete
git push origin phase1 --tags

# Back to main for Phase 2:
git checkout main
# Refactor with hardware abstraction layer
# Add Android app package
# Add production blockchain deployment
```

---

## Resources & Documentation

### Technical Specifications
- Camera Security Architecture: `/mnt/project/Birthmark_Camera_Security_Architecture.docx`
- Registry Specs: `/mnt/project/Birthmark_Media_Registry_Specs.docx`
- Simulated Authorities: `/mnt/project/Simulated_Authorities_Specs.docx`
- Complete Architecture: `/mnt/project/Birthmark_Standard_Technical_Architecture.docx`

### Governance & Applications
- Registry Governance Charter: `/mnt/project/Birthmark_Media_Registry_Governance_Charter.docx`
- Mozilla Grant Application: `/mnt/project/Mozilla_Grant_Application.docx`
- Craig Newmark Application: `/mnt/project/Craig_Newmark_Application.docx`

### Contact
- Executive Director: Samuel C. Ryan
- Email: samryan.pdx@proton.me
- Website: birthmarkstandard.org
- GitHub: github.com/Birthmark-Standard/Birthmark

---

## Current Session Context (December 11, 2025)

### What We Just Accomplished
- ✅ Camera authentication pipeline fully validated
- ✅ Raw and processed image hashing working
- ✅ Simulated Secure Element encryption tested
- ✅ Certificate generation complete
- ✅ Test pipeline script created (`test_pipeline.py`)

### What We're Building Now
1. Submission Server (FastAPI + PostgreSQL)
2. Simulated Manufacturer Authority (validation endpoint)
3. Integration testing (camera → server → SMA → PASS/FAIL)

### Next Session Goals
- Complete Submission Server MVP
- Complete SMA validation logic
- Test end-to-end flow
- Begin blockchain testnet setup

---

**This document is the authoritative context for Phase 1 development. All code, architecture decisions, and implementation details should align with this specification.**
