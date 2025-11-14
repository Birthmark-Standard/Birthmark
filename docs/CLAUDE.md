# Birthmark Standard - Claude Code Context

**Last Updated:** November 2025  
**Current Phase:** Phase 1 (Hardware Prototype)  
**Repository:** github.com/Birthmark-Standard/Birthmark

---

## Project Overview

The Birthmark Standard is an open-source, hardware-backed photo authentication system that proves images originated from legitimate cameras rather than AI generation. It uses camera sensors' unique Non-Uniformity Correction (NUC) maps as hardware fingerprints, combined with blockchain verification on zkSync Layer 2.

**Target:** Deployment for 2028 Presidential Election  
**Organization:** The Birthmark Standard Foundation (501(c)(3) pending)

### Core Innovation

Unlike C2PA which embeds metadata that gets stripped by social media platforms, Birthmark authenticates images independently of metadata. The system proves an image hash was captured by a legitimate camera at a specific time, even after the image has been copied, shared, or had its metadata removed.

---

## System Architecture

### Component Overview

```
Camera Device          Aggregation Server              Blockchain
─────────────         ──────────────────              ──────────
│ Sensor     │        │ Server Queue    │  
│ Secure Elem│   ──►  │ Decision Gate   │────────►   zkSync L2
│ Wireless   │        │ Batch Accum     │            │ Smart Contract
                      │ Merkle Tree Gen │            │ Merkle Root Ledger
                      └────────┬────────┘            └─────────┬────────
                               │                                │
                               ▼                          Ethereum L1
                      Manufacturer (SMA)                 ────────────
                     ──────────────────                  │ Settlement Contract
                     │ Validation Server│                │ Immutable State Root
                     │ Key Tables       │
                     │ NUC Records      │
                     │ Identity Mapping │
```

**Data Flow:**
1. Camera sends authentication bundle to Aggregation Server only
2. Aggregation Server forwards encrypted token to SMA for validation
3. SMA returns PASS/FAIL (never sees image hash)
4. Aggregation Server batches validated hashes into Merkle trees
5. Merkle roots posted to zkSync smart contract

### Critical Privacy Invariants

- **SMA never sees image hashes** - only validates camera authenticity
- **Aggregator cannot track individual cameras** - rotating encrypted tokens
- **Images never stored** - only SHA-256 hashes of raw sensor data
- **Manufacturer validates device, not content**

---

## Development Phases

### Phase 1: Hardware Prototype (Current)
**Timeline:** 4-6 weeks  
**Goal:** Raspberry Pi camera proving parallel raw sensor hashing

**Components:**
- Raspberry Pi 4 + HQ Camera + LetsTrust TPM
- Aggregation Server (FastAPI + PostgreSQL)
- Simulated Manufacturer Authority (SMA)
- zkSync Testnet Smart Contract

**Key Deliverables:**
- Camera captures 12MP raw Bayer, hashes with TPM
- <5 second background processing, zero user latency
- Photography club validation (50-100 photographers)
- 500+ test images verified on testnet

### Phase 2: iOS App
**Timeline:** 3-4 months  
**Goal:** Validate architecture on consumer mobile devices

**Key Differences from Phase 1:**
- Hashes processed images (not raw sensor data)
- Device fingerprint instead of NUC map
- Same aggregation server infrastructure
- TestFlight closed beta (60-100 testers)

### Phase 3: Manufacturer Integration
**Timeline:** Negotiation phase  
**Goal:** Production camera partnerships

---

## Package Structure

```
birthmark/
├── packages/
│   ├── camera-pi/           # Raspberry Pi prototype
│   ├── aggregator/          # Aggregation server
│   ├── sma/                  # Simulated Manufacturer Authority
│   ├── contracts/           # zkSync smart contracts
│   ├── mobile-app/          # iOS app (Phase 2)
│   └── verifier/            # Image validation client
├── shared/
│   ├── types/               # Common data structures
│   ├── crypto/              # Shared cryptographic utilities
│   └── protocols/           # API contracts (source of truth)
└── docs/
    └── (architecture diagrams, phase plans)
```

---

## Interface Specifications

### Camera → Aggregator Submission

```python
@dataclass
class AuthenticationBundle:
    image_hash: str              # SHA-256 of raw Bayer data (64 hex chars)
    encrypted_nuc_token: bytes   # AES-GCM encrypted NUC hash
    table_references: List[int]  # 3 table IDs (0-2499)
    key_indices: List[int]       # 3 key indices (0-999)
    timestamp: int               # Unix timestamp
    gps_hash: Optional[str]      # SHA-256 of GPS coordinates (optional)
    device_signature: bytes      # TPM signature over bundle
```

**Endpoint:** `POST /api/v1/submit`  
**Response:** `202 Accepted` with receipt ID

### Aggregator → SMA Validation

```python
@dataclass
class ValidationRequest:
    encrypted_token: bytes
    table_references: List[int]
    key_indices: List[int]
    # Note: NO image hash - SMA never sees image content
```

**Response:** `PASS` or `FAIL` (boolean)  
**SMA decrypts token, validates against NUC records**

### Aggregator → Blockchain

```solidity
function postBatch(bytes32 merkleRoot, uint256 imageCount) external;
```

**Batching:** 1,000-5,000 images per batch  
**Cost target:** <$0.00003 per image on zkSync

### Verification Query

```python
@dataclass
class VerificationRequest:
    image_hash: str  # SHA-256 of image to verify

@dataclass  
class VerificationResponse:
    verified: bool
    timestamp: Optional[int]
    merkle_proof: Optional[List[str]]
    batch_id: Optional[int]
    blockchain_tx: Optional[str]
```

---

## Cryptographic Standards

### Hashing
- **Algorithm:** SHA-256
- **Input:** Raw Bayer sensor data (12MP = ~24MB)
- **Output:** 64 character hex string
- **Performance target:** <500ms on Raspberry Pi TPM

### Key Tables (SMA)
- **Total tables:** 2,500
- **Keys per table:** 1,000
- **Key size:** 256-bit
- **Derivation:** HKDF from master keys
- **Camera assignment:** 3 random tables per device

### Encryption
- **Algorithm:** AES-256-GCM
- **Purpose:** Encrypt NUC hash with rotating keys
- **Authentication tag:** 16 bytes
- **Nonce:** 12 bytes (unique per encryption)

### Device Certificates
- **Format:** X.509
- **Key type:** ECDSA P-256
- **Chain:** Device cert → Manufacturer CA → Root
- **Storage:** TPM/Secure Element

---

## Database Schemas

### Aggregation Server (PostgreSQL)

```sql
-- Pending submissions awaiting batching
CREATE TABLE pending_submissions (
    id SERIAL PRIMARY KEY,
    image_hash CHAR(64) NOT NULL,
    encrypted_token BYTEA NOT NULL,
    table_references INTEGER[] NOT NULL,
    key_indices INTEGER[] NOT NULL,
    timestamp BIGINT NOT NULL,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sma_validated BOOLEAN DEFAULT FALSE
);

-- Completed batches
CREATE TABLE batches (
    id SERIAL PRIMARY KEY,
    merkle_root CHAR(64) NOT NULL,
    image_count INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    blockchain_tx VARCHAR(66),  -- Transaction hash
    confirmed BOOLEAN DEFAULT FALSE
);

-- Image hash to batch mapping (for verification)
CREATE TABLE image_batch_map (
    image_hash CHAR(64) PRIMARY KEY,
    batch_id INTEGER REFERENCES batches(id),
    merkle_proof TEXT[],  -- Array of proof hashes
    leaf_index INTEGER
);
```

### SMA (PostgreSQL)

```sql
-- Key tables (2,500 tables with master keys)
CREATE TABLE key_tables (
    table_id INTEGER PRIMARY KEY CHECK (table_id >= 0 AND table_id < 2500),
    master_key BYTEA NOT NULL  -- 256-bit key for HKDF
);

-- Registered devices
CREATE TABLE registered_devices (
    device_serial VARCHAR(255) PRIMARY KEY,
    nuc_hash BYTEA NOT NULL,  -- SHA-256 (32 bytes)
    table_assignments INTEGER[3] NOT NULL,
    device_certificate TEXT NOT NULL,
    device_public_key TEXT NOT NULL,
    device_family VARCHAR(50)  -- 'Raspberry Pi', 'iOS', etc.
);
```

---

## Smart Contract (Solidity)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract BirthmarkRegistry {
    struct Batch {
        bytes32 merkleRoot;
        uint256 imageCount;
        uint256 timestamp;
        address aggregator;
    }
    
    mapping(uint256 => Batch) public batches;
    mapping(address => bool) public authorizedAggregators;
    uint256 public nextBatchId;
    address public owner;
    
    event BatchPosted(
        uint256 indexed batchId,
        bytes32 merkleRoot,
        uint256 imageCount,
        address aggregator
    );
    
    modifier onlyAggregator() {
        require(authorizedAggregators[msg.sender], "Not authorized");
        _;
    }
    
    function postBatch(bytes32 merkleRoot, uint256 imageCount) 
        external 
        onlyAggregator 
        returns (uint256) 
    {
        uint256 batchId = nextBatchId++;
        batches[batchId] = Batch({
            merkleRoot: merkleRoot,
            imageCount: imageCount,
            timestamp: block.timestamp,
            aggregator: msg.sender
        });
        
        emit BatchPosted(batchId, merkleRoot, imageCount, msg.sender);
        return batchId;
    }
    
    function verifyInclusion(
        uint256 batchId,
        bytes32 imageHash,
        bytes32[] calldata proof,
        uint256 leafIndex
    ) external view returns (bool) {
        Batch memory batch = batches[batchId];
        require(batch.timestamp > 0, "Batch does not exist");
        
        bytes32 computedRoot = imageHash;
        for (uint256 i = 0; i < proof.length; i++) {
            if (leafIndex % 2 == 0) {
                computedRoot = keccak256(abi.encodePacked(computedRoot, proof[i]));
            } else {
                computedRoot = keccak256(abi.encodePacked(proof[i], computedRoot));
            }
            leafIndex /= 2;
        }
        
        return computedRoot == batch.merkleRoot;
    }
}
```

---

## Hardware Specifications (Phase 1)

### Raspberry Pi 4 Setup

**Components:**
- Raspberry Pi 4 Model B (4GB RAM)
- Raspberry Pi HQ Camera (Sony IMX477, 12.3MP)
- LetsTrust TPM Module (Infineon SLB 9670)
- 64GB microSD (A2 rated)
- Optional: GPS Module (Neo-6M), RTC (DS3231)

**Total cost:** ~$200-250

### Camera Capture Pipeline

```python
from picamera2 import Picamera2
import hashlib

def capture_and_hash():
    """Capture raw Bayer and compute hash"""
    picam2 = Picamera2()
    config = picam2.create_still_configuration(
        raw={'format': 'SRGGB10', 'size': (4056, 3040)}
    )
    picam2.configure(config)
    picam2.start()
    
    raw_array = picam2.capture_array("raw")
    bayer_bytes = raw_array.tobytes()
    image_hash = hashlib.sha256(bayer_bytes).hexdigest()
    
    picam2.stop()
    return image_hash
```

### Performance Targets

- **Total capture time:** <650ms
- **Parallel hashing overhead:** <5% CPU
- **User-perceivable latency:** Zero
- **Sustained capture rate:** 1 photo/second
- **Reliability:** 100+ captures without failure

---

## API Endpoints (Aggregation Server)

### Submission API

```
POST /api/v1/submit
Content-Type: application/json

{
    "image_hash": "a1b2c3...",
    "encrypted_token": "base64...",
    "table_references": [42, 1337, 2001],
    "key_indices": [7, 99, 512],
    "timestamp": 1732000000,
    "gps_hash": "optional...",
    "signature": "base64..."
}

Response: 202 Accepted
{
    "receipt_id": "uuid",
    "status": "pending_validation"
}
```

### Verification API

```
GET /api/v1/verify/{image_hash}

Response: 200 OK
{
    "verified": true,
    "batch_id": 42,
    "timestamp": 1732000000,
    "merkle_proof": ["hash1", "hash2", ...],
    "blockchain_tx": "0x...",
    "confirmation_time": "2024-11-13T10:30:00Z"
}
```

### Health Check

```
GET /api/v1/health

Response: 200 OK
{
    "status": "healthy",
    "pending_submissions": 847,
    "last_batch": "2024-11-13T10:00:00Z",
    "sma_connection": "ok",
    "blockchain_connection": "ok"
}
```

---

## Testing Requirements

### Unit Tests

Each component must have comprehensive unit tests:
- Cryptographic operations (hash, encrypt, sign)
- Database operations (CRUD, queries)
- API endpoint validation
- Merkle tree generation and verification
- Key derivation consistency

### Integration Tests

Cross-component testing:
- Camera → Aggregator submission flow
- Aggregator → SMA validation flow
- Aggregator → Blockchain posting
- End-to-end verification query

### Performance Benchmarks

- Hash computation time (target: <500ms on Pi)
- API response time (target: <100ms for verification)
- Batch processing time (target: <5s for 1000 images)
- Merkle proof generation (target: <10ms)

---

## Development Conventions

### Code Style
- **Python:** Black formatter, type hints required
- **Solidity:** Hardhat linter, NatSpec comments
- **TypeScript:** ESLint + Prettier
- **All:** Comprehensive docstrings/comments

### Git Workflow
- Feature branches from `main`
- Pull requests with code review
- Semantic versioning
- Conventional commits

### Security Practices
- No secrets in code (use environment variables)
- Input validation on all APIs
- Rate limiting on public endpoints
- Audit logging for sensitive operations

---

## Common Development Tasks

### Running the Aggregation Server

```bash
cd packages/aggregator
pip install -r requirements.txt
cp .env.example .env
# Edit .env with database credentials
uvicorn src.main:app --reload
```

### Running the SMA

```bash
cd packages/sma
pip install -r requirements.txt
python scripts/generate_key_tables.py  # First time only
uvicorn src.main:app --port 8001 --reload
```

### Deploying Contracts (Testnet)

```bash
cd packages/contracts
npm install
cp .env.example .env
# Add zkSync testnet RPC and private key
npx hardhat compile
npx hardhat run scripts/deploy.ts --network zksync-testnet
```

### Running Camera Prototype

```bash
cd packages/camera-pi
pip install -r requirements.txt
python scripts/provision_device.py  # First time only
python src/main.py
```

---

## Known Limitations & Future Work

### Phase 1 Limitations
- Single aggregator (no federation yet)
- Testnet only (no real monetary value)
- Manual provisioning (no automated manufacturing)
- Limited to Raspberry Pi hardware

### Phase 2 Additions
- iOS app with device fingerprints (not NUC)
- Larger key tables (2,500 × 1,000)
- Time-based batching (6-hour timeout)
- Production database optimizations

### Phase 3 Requirements
- Manufacturer API integration
- Production smart contract deployment
- Federated aggregator network
- Public verification interface

---

## Frequently Referenced Files

When Claude Code needs specific implementation details:

- **Aggregator API design:** `docs/phase-plans/Birthmark_Phase_1_Plan_Aggregation_Server.md`
- **SMA key table logic:** `docs/phase-plans/Birthmark_Phase_1-2_Plan_SMA.md`
- **Smart contract specs:** `docs/phase-plans/Birthmark_Phase_1_Plan_zkSync_Smart_Contract.md`
- **Camera hardware setup:** `docs/phase-plans/Birthmark_Phase_1_Plan_Simulated_Camera.md`
- **iOS architecture:** `docs/phase-plans/Birthmark_Phase_2_Plan_iOS_App.md`
- **Security architecture:** `docs/specs/Birthmark_Camera_Security_Architecture.md`

---

## Success Metrics

### Phase 1 (Current)
- [ ] 99%+ uptime for aggregation server
- [ ] <5 second hash time on Raspberry Pi
- [ ] <$0.00003 per image on zkSync testnet
- [ ] 80%+ photography club satisfaction
- [ ] 500+ images verified end-to-end

### Technical Quality
- [ ] 100% of valid tokens pass SMA validation
- [ ] Merkle proofs verify 100% of the time
- [ ] <100ms verification API response time
- [ ] Zero false positives or negatives

---

## Contact & Resources

**Founder:** Samuel C. Ryan  
**Organization:** The Birthmark Standard Foundation  
**GitHub:** github.com/Birthmark-Standard/Birthmark  
**License:** Open source (specific license TBD)

**Related Standards:** C2PA (complementary, addresses different threat model)

---

*This document is the authoritative source of truth for Claude Code development context. Update as architecture evolves.*
