# Birthmark Blockchain Node

**Status:** Phase 1 Development
**Type:** Merged Aggregator + Blockchain Validator
**Technology:** FastAPI + PostgreSQL + Custom Blockchain

---

## Overview

This package implements the **merged aggregator and blockchain node** architecture for the Birthmark Standard. Unlike traditional systems that separate aggregation from blockchain validation, this design combines both responsibilities into a single deployable unit that institutions can run to participate in the Birthmark network.

### Why Merge Aggregator + Node?

**Trust Model Alignment:**
- Institutions trusted to aggregate (universities, archives, journalism orgs) ARE the validators
- No separation between "who receives submissions" and "who validates the chain"
- Reputation at stake: institutions police each other via consensus voting

**Operational Simplicity:**
- Single Docker container deployment per institution
- No network hop between aggregation → blockchain submission
- Fewer moving parts = easier operations

**Natural Scaling:**
- Each new institution adds both aggregation capacity AND validation redundancy
- Geographic distribution happens organically as network grows

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                  BIRTHMARK NODE (Institution)              │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              AGGREGATOR COMPONENT                    │ │
│  │  ┌────────────────────────────────────────────────┐ │ │
│  │  │  Camera Submission API                         │ │ │
│  │  │  POST /api/v1/submit                           │ │ │
│  │  │  - Receives AuthenticationBundle from cameras  │ │ │
│  │  │  - Queues for validation                       │ │ │
│  │  └────────────────────────────────────────────────┘ │ │
│  │                                                       │ │
│  │  ┌────────────────────────────────────────────────┐ │ │
│  │  │  SMA Validation Client                         │ │ │
│  │  │  - Sends encrypted tokens to manufacturer      │ │ │
│  │  │  - Receives PASS/FAIL (never sends image hash) │ │ │
│  │  └────────────────────────────────────────────────┘ │ │
│  │                                                       │ │
│  │  ┌────────────────────────────────────────────────┐ │ │
│  │  │  Batch Accumulator                             │ │ │
│  │  │  - Collects validated submissions              │ │ │
│  │  │  - Creates transaction batches (100-1000)      │ │ │
│  │  │  - Proposes blocks to blockchain layer         │ │ │
│  │  └────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────┘ │
│                            │                               │
│                            ▼                               │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              BLOCKCHAIN NODE COMPONENT               │ │
│  │  ┌────────────────────────────────────────────────┐ │ │
│  │  │  Transaction Validator                         │ │ │
│  │  │  - Validates transaction format                │ │ │
│  │  │  - Checks aggregator authorization             │ │ │
│  │  │  - Prevents duplicate hashes                   │ │ │
│  │  │  (replaces smart contract logic)               │ │ │
│  │  └────────────────────────────────────────────────┘ │ │
│  │                                                       │ │
│  │  ┌────────────────────────────────────────────────┐ │ │
│  │  │  Consensus Engine (PoA)                        │ │ │
│  │  │  - Phase 1: Single node (auto-accept)          │ │ │
│  │  │  - Phase 2+: Multi-node voting (2/3 majority)  │ │ │
│  │  │  - Pluggable design for easy upgrade           │ │ │
│  │  └────────────────────────────────────────────────┘ │ │
│  │                                                       │ │
│  │  ┌────────────────────────────────────────────────┐ │ │
│  │  │  Block Storage (PostgreSQL)                    │ │ │
│  │  │  - Blocks table (headers + transactions)       │ │ │
│  │  │  - Image hashes table (indexed for fast query) │ │ │
│  │  │  - Cryptographic chain (tamper-proof)          │ │ │
│  │  └────────────────────────────────────────────────┘ │ │
│  │                                                       │ │
│  │  ┌────────────────────────────────────────────────┐ │ │
│  │  │  Verification API (Public)                     │ │ │
│  │  │  GET /api/v1/verify/{image_hash}               │ │ │
│  │  │  - Direct hash lookup (no Merkle proofs)       │ │ │
│  │  │  - Returns: verified, timestamp, block_height  │ │ │
│  │  └────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              P2P NETWORKING (Phase 2+)               │ │
│  │  - Gossip protocol for block propagation            │ │
│  │  - State sync for new nodes                         │ │
│  │  - Peer discovery                                   │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
         │                                        │
         │ Receives camera                       │ Peer-to-peer
         │ submissions                            │ with other nodes
         ▼                                        ▼
   Raspberry Pi Cameras                    Other Institution Nodes
```

---

## Key Design Principles

### 1. Direct Hash Storage (Not Merkle Roots)
- Full SHA-256 hashes (64 hex chars) stored on-chain
- Verification = simple database lookup
- No Merkle proof generation or validation
- ~100 bytes per image record

### 2. Zero Gas Fees
- Institutions donate hosting (not mining)
- No cryptocurrency required
- Eliminates per-transaction costs
- Cost = server hosting only (~$50-100/month)

### 3. Proof-of-Authority Consensus
- Trusted validator set (known institutions)
- Fast block production (1-5 seconds)
- Minimal energy consumption
- 2/3 majority for block acceptance (Phase 2+)

### 4. Privacy-Preserving
- **SMA never sees image hashes** - only validates camera authenticity
- **Only SHA-256 hashes stored** - not image content
- **Camera identity encrypted** - rotating tokens prevent tracking

### 5. Pluggable Consensus
- Phase 1: Single node (instant approval)
- Phase 2+: Multi-node voting (same interface)
- Minimal code changes when scaling up

---

## Data Flow

### Image Submission Flow
```
1. Camera captures image → computes SHA-256 hash
                         ↓
2. Camera sends to Aggregator: {image_hash, encrypted_nuc_token, timestamp}
                         ↓
3. Aggregator validates with SMA → PASS/FAIL (SMA never sees hash)
                         ↓
4. Aggregator queues validated submission
                         ↓
5. Batch Accumulator creates transaction batch (100-1000 images)
                         ↓
6. Consensus Engine proposes block
                         ↓
7. Block Storage writes to PostgreSQL (immutable)
                         ↓
8. Hash now verifiable via GET /api/v1/verify/{hash}
```

### Verification Query Flow
```
1. User/App wants to verify image → computes SHA-256 hash
                         ↓
2. Query: GET /api/v1/verify/{hash}
                         ↓
3. Blockchain Node queries hash index (PostgreSQL)
                         ↓
4. Response: {verified: true, timestamp, block_height, aggregator}
```

---

## Database Schema

### Blocks Table
```sql
CREATE TABLE blocks (
    block_height BIGINT PRIMARY KEY,
    block_hash CHAR(64) NOT NULL UNIQUE,
    previous_hash CHAR(64) NOT NULL,
    timestamp BIGINT NOT NULL,
    validator_id VARCHAR(255) NOT NULL,
    transaction_count INTEGER NOT NULL,
    signature TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_blocks_hash ON blocks(block_hash);
```

### Transactions Table
```sql
CREATE TABLE transactions (
    tx_id SERIAL PRIMARY KEY,
    tx_hash CHAR(64) NOT NULL UNIQUE,
    block_height BIGINT REFERENCES blocks(block_height),
    aggregator_id VARCHAR(255) NOT NULL,
    batch_size INTEGER NOT NULL,
    signature TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_tx_block ON transactions(block_height);
```

### Image Hashes Table (Fast Lookup)
```sql
CREATE TABLE image_hashes (
    image_hash CHAR(64) PRIMARY KEY,
    tx_id INTEGER REFERENCES transactions(tx_id),
    block_height BIGINT REFERENCES blocks(block_height),
    timestamp BIGINT NOT NULL,
    aggregator_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_hashes_block ON image_hashes(block_height);
CREATE INDEX idx_hashes_timestamp ON image_hashes(timestamp);
```

### Pending Submissions Table (Aggregator Queue)
```sql
CREATE TABLE pending_submissions (
    id SERIAL PRIMARY KEY,
    image_hash CHAR(64) NOT NULL,
    encrypted_token BYTEA NOT NULL,
    table_references INTEGER[] NOT NULL,
    key_indices INTEGER[] NOT NULL,
    timestamp BIGINT NOT NULL,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sma_validated BOOLEAN DEFAULT FALSE,
    validation_attempted_at TIMESTAMP,
    validation_result TEXT
);
CREATE INDEX idx_pending_validated ON pending_submissions(sma_validated);
```

---

## API Endpoints

### Aggregator Endpoints (Camera-Facing)

**POST /api/v1/submit** - Submit authentication bundle
```json
{
  "image_hash": "a1b2c3d4...",  // SHA-256 (64 hex chars)
  "encrypted_nuc_token": "base64...",
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

### Blockchain Endpoints (Public Verification)

**GET /api/v1/verify/{image_hash}** - Verify image authenticity
```json
Response: 200 OK
{
  "verified": true,
  "timestamp": 1732000000,
  "block_height": 123456,
  "aggregator": "university_of_oregon",
  "tx_hash": "abc123..."
}
```

**GET /api/v1/status** - Node health and statistics
```json
Response: 200 OK
{
  "node_id": "university_of_oregon",
  "block_height": 123456,
  "total_hashes": 1500000,
  "pending_submissions": 47,
  "last_block_time": "2024-11-17T10:30:00Z",
  "validator_nodes": 1,  // Phase 1
  "uptime": "99.9%"
}
```

### Internal Endpoints (Node-to-Node, Phase 2+)

**POST /p2p/propose-block** - Propose new block to peers
**GET /p2p/sync/{from_height}** - Sync blockchain state
**GET /p2p/peers** - Get peer list

---

## Configuration

**Environment Variables (.env)**
```bash
# Node Identity
NODE_ID=university_of_oregon
VALIDATOR_KEY_PATH=/data/keys/validator.key

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/birthmark_chain

# Aggregator Settings
SMA_VALIDATION_ENDPOINT=http://sma:8001/validate
BATCH_SIZE_MIN=100
BATCH_SIZE_MAX=1000
BATCH_TIMEOUT_SECONDS=300  # 5 minutes

# Consensus
CONSENSUS_MODE=single  # 'single' for Phase 1, 'poa' for Phase 2+
VALIDATOR_NODES=  # Comma-separated for Phase 2+

# API
API_HOST=0.0.0.0
API_PORT=8545
ENABLE_PUBLIC_VERIFICATION=true

# P2P (Phase 2+)
P2P_PORT=26656
P2P_PEERS=  # Comma-separated peer addresses
```

---

## Quick Start

### 1. Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Docker & Docker Compose (recommended)

### 2. Clone and Install
```bash
cd packages/blockchain
pip install -e ".[dev]"
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your settings
```

### 4. Start with Docker Compose
```bash
docker compose up -d
```

This starts:
- PostgreSQL database
- Birthmark node (aggregator + blockchain)
- Migrations run automatically

### 5. Initialize Genesis Block
```bash
python scripts/init_genesis.py
```

### 6. Verify Node is Running
```bash
curl http://localhost:8545/api/v1/status
```

---

## Development Workflow

### Running Locally (Without Docker)
```bash
# Start PostgreSQL
docker compose up -d postgres

# Run migrations
alembic upgrade head

# Start node
uvicorn src.main:app --reload --port 8545
```

### Running Tests
```bash
pytest tests/ -v --cov=src
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Code Quality
```bash
# Format
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

---

## Phase Roadmap

### Phase 1: Single Node (Current)
- [x] Architecture design
- [x] Core models and database schema
- [x] Aggregator API (camera submissions)
- [x] SMA validation client
- [x] Transaction validator
- [x] Block storage engine
- [x] Single-node consensus (auto-accept)
- [x] Verification API
- [x] Docker deployment
- [x] Genesis block initialization
- [ ] Integration with camera-pi package
- [ ] 500+ test images verified

**Phase 1 Scope:**
- ✅ Camera validation (via SMA)
- ❌ Software validation (via SSA) - deferred to Phase 2+
- ❌ Provenance chain tracking - deferred to Phase 2+
- ❌ Multi-image submissions - Phase 1 accepts one hash per submission

**Success Criteria:**
- Camera → Aggregator → Blockchain → Verification works end-to-end
- <100ms verification query response
- Zero false positives/negatives
- Docker deployment runs on single server

**Phase 1 Limitations:**
- Camera-only validation (no software edits)
- SMA validation uses format checking (full cryptographic validation in Phase 2)
- Single blockchain node (no redundancy)
- Batch size minimum lowered to 1 for testing (production will use 100-1000)

### Phase 2: Multi-Node Deployment
- [ ] P2P networking (gossip protocol)
- [ ] Multi-node consensus (2/3 voting)
- [ ] State synchronization
- [ ] Deploy to 3-5 partner institutions
- [ ] Honeypot testing system
- [ ] Monitoring and alerting

**Success Criteria:**
- 3+ institutions running nodes
- Byzantine fault tolerance (1 node can fail)
- Automatic peer discovery and sync
- <5 second block finality

### Phase 3: Production Scale
- [ ] 10+ validator nodes
- [ ] Geographic distribution (multi-region)
- [ ] Public verification web interface
- [ ] API rate limiting and auth
- [ ] Archival node strategy
- [ ] Disaster recovery procedures

---

## Security Considerations

### Aggregator Layer
- **Input validation:** All camera submissions validated against schema
- **Rate limiting:** Prevent DoS attacks
- **SMA isolation:** Manufacturer never sees image hashes
- **Signature verification:** Camera signatures validated

### Blockchain Layer
- **Transaction validation:** Only authorized aggregators can submit
- **Duplicate prevention:** Hash uniqueness enforced
- **Cryptographic chain:** Previous block hash prevents tampering
- **Consensus voting:** 2/3 majority prevents single rogue node (Phase 2+)

### Privacy
- **No image content stored:** Only SHA-256 hashes
- **No camera identity:** Encrypted rotating tokens
- **Optional GPS:** User can choose to include location proof

---

## Performance Targets

### Phase 1
- **Submission throughput:** 10 submissions/second
- **Verification latency:** <100ms (database query)
- **Block creation:** Every 5 minutes or 1000 transactions
- **Database size:** ~100 bytes/image = ~100GB/million images

### Phase 2+ (Multi-Node)
- **Submission throughput:** 100+ submissions/second (distributed)
- **Block finality:** <5 seconds (consensus voting)
- **Network bandwidth:** <1 Mbps per node (block gossip)

---

## Comparison to Previous Architecture

| Aspect | zkSync L2 (Old) | Custom Blockchain (New) |
|--------|-----------------|-------------------------|
| **Cost** | ~$0.00003/image | $0 (hosting only) |
| **Hash Storage** | Merkle roots only | Full SHA-256 hashes |
| **Verification** | Merkle proof required | Direct lookup |
| **Complexity** | High (L2 + L1) | Low (single chain) |
| **Dependencies** | Ethereum ecosystem | None (fully owned) |
| **Smart Contracts** | Solidity deployment | Native validation |
| **Upgradability** | Governance required | Direct code deploy |
| **Control** | Limited | Complete |

---

## Troubleshooting

### Database Connection Fails
```bash
# Check PostgreSQL is running
docker compose ps

# Check connection
psql $DATABASE_URL -c "SELECT 1"
```

### Genesis Block Fails
```bash
# Reset database
alembic downgrade base
alembic upgrade head
python scripts/init_genesis.py
```

### SMA Validation Fails
```bash
# Check SMA is running
curl http://localhost:8001/health

# Check SMA endpoint in .env
echo $SMA_VALIDATION_ENDPOINT
```

---

## Contributing

This is Phase 1 development. Architecture is still evolving. Feedback welcome!

**Key files to review:**
- `src/shared/models/` - Core data structures
- `src/node/consensus/` - Consensus engine (extensibility point)
- `src/aggregator/validation/` - SMA integration
- `docs/ARCHITECTURE.md` - Detailed design docs

---

## License

TBD - The Birthmark Standard Foundation

---

**The Birthmark Standard: Proving images are real, not generated.**
