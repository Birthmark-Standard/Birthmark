# Birthmark Blockchain (Deprecated)

**Status:** Replaced by `packages/blockchain/`
**Previous Type:** Smart Contracts for zkSync Layer 2
**New Implementation:** Custom blockchain in `packages/blockchain/`

---

## Important: Package Moved

This package previously contained Ethereum smart contracts for zkSync Layer 2 deployment.

**The project has pivoted to a custom blockchain implementation.**

**New location:** `packages/blockchain/`

Please see:
- `/packages/blockchain/README.md` - Architecture and design
- `/packages/blockchain/USAGE.md` - Quick start guide

---

## Why the Change?

The Birthmark Standard pivoted from Ethereum Layer 2 (zkSync) to a custom blockchain for several reasons:

1. **Zero Gas Fees:** Eliminates per-transaction costs
2. **Direct Hash Storage:** Full SHA-256 hashes on-chain (not Merkle roots)
3. **Simpler Verification:** Direct lookup instead of Merkle proofs
4. **Complete Control:** Owned infrastructure and consensus
5. **Purpose-Built:** Optimized for image hash verification

See `/packages/blockchain/README.md` for detailed comparison.

---

# Original Documentation (Archived)

**Below is the original planning documentation for reference only.**

---

# Birthmark Blockchain (Original Plan)

**Status:** Archived
**Type:** Custom Blockchain Implementation
**Purpose:** Direct on-chain storage of image hash authenticity records

## Overview

This package will contain the custom blockchain implementation for the Birthmark Standard. Unlike traditional approaches using Ethereum Layer 2 solutions, this blockchain is designed specifically for storing full SHA-256 image hashes directly on-chain, providing a simpler, more cost-effective, and fully controlled verification system.

## Architecture Vision

### Core Principles

1. **Direct Hash Storage:** Full SHA-256 hashes (64 hex characters) stored on-chain
2. **No Gas Fees:** Eliminates blockchain transaction costs for users
3. **Simple Verification:** Direct hash lookup without Merkle proof complexity
4. **Full Control:** Complete ownership of infrastructure and consensus mechanism
5. **Purpose-Built:** Optimized specifically for image hash verification use case

### Blockchain Design (Proposed)

**Block Structure:**
- Block header with timestamp, previous hash, nonce
- Transaction list containing image hash submissions
- Aggregator signatures for batch authentication
- Merkle tree for block integrity (internal use, not for image verification)

**Transaction Types:**
- `RegisterHash`: Submit new image hash with metadata (timestamp, camera identity token)
- `BatchRegister`: Bulk submission from aggregation server
- `QueryHash`: Verification request (read-only, no transaction needed)

**Consensus Mechanism:**
- Proof-of-Authority (PoA) with trusted aggregators as validators
- Simple, fast block production (target: 1-5 second blocks)
- Minimal energy consumption
- Suitable for permissioned network with known aggregators

**Data Model:**
```
ImageRecord {
  hash: SHA256 (32 bytes)
  timestamp: uint64
  aggregator: AggregatorID
  camera_token_hash: SHA256 (encrypted identity, optional)
  gps_hash: SHA256 (optional location proof)
  block_height: uint64
  tx_index: uint32
}
```

## Benefits vs. Previous Approach

| Feature | zkSync L2 | Custom Blockchain |
|---------|-----------|-------------------|
| **Cost per image** | ~$0.00003 | $0 (hosting only) |
| **Hash storage** | Merkle roots only | Full SHA-256 hashes |
| **Verification** | Merkle proof required | Direct lookup |
| **Infrastructure** | Ethereum dependency | Fully owned |
| **Complexity** | High (L2 + L1) | Low (single chain) |
| **Control** | Limited | Complete |

## Technology Stack (Under Evaluation)

### Option 1: Custom Implementation
- **Language:** Rust or Go
- **Database:** RocksDB or PostgreSQL
- **Networking:** libp2p or custom P2P
- **Consensus:** Simple PoA
- **Pros:** Full control, minimal dependencies
- **Cons:** More development work

### Option 2: Cosmos SDK
- **Framework:** Cosmos SDK (Tendermint consensus)
- **Language:** Go
- **Pros:** Battle-tested, rich ecosystem
- **Cons:** Heavier than needed, complex setup

### Option 3: Substrate
- **Framework:** Substrate (Polkadot framework)
- **Language:** Rust
- **Pros:** Modular, customizable
- **Cons:** Steep learning curve, complex

### Option 4: Simplified Ledger
- **Approach:** Database-backed ledger with cryptographic chain
- **Language:** Python/TypeScript
- **Storage:** PostgreSQL with cryptographic verification
- **Pros:** Simplest, fastest to implement
- **Cons:** Not a "true" blockchain (but may be sufficient)

## Project Structure (Planned)

```
packages/blockchain/
├── node/                    # Blockchain node implementation
│   ├── consensus/          # PoA consensus logic
│   ├── storage/            # Block and state storage
│   ├── networking/         # P2P communication
│   └── api/                # REST/gRPC API for queries
├── cli/                    # Node management CLI
├── genesis/                # Genesis block configuration
├── scripts/                # Deployment and setup scripts
├── tests/                  # Integration and unit tests
└── docs/                   # Architecture documentation
```

## Integration Points

### Aggregation Server → Blockchain
- **Endpoint:** `POST /submit-batch`
- **Payload:** Array of `{hash, timestamp, camera_token}`
- **Response:** `{block_height, tx_hashes[]}`
- **Authentication:** Aggregator signing key

### Verifier Client → Blockchain
- **Endpoint:** `GET /verify/{image_hash}`
- **Response:** `{verified: bool, timestamp, block_height, aggregator}`
- **Performance:** <100ms response time

### Camera → Aggregator → Blockchain
1. Camera captures image, computes SHA-256 hash
2. Camera sends to aggregation server with encrypted identity token
3. Aggregation server validates with manufacturer SMA
4. Aggregation server submits to blockchain in batch
5. Blockchain stores hash permanently
6. Verifier can query hash anytime

## Development Roadmap

### Phase 1: Architecture Definition (Current)
- [ ] Finalize technology stack decision
- [ ] Define block structure and data format
- [ ] Design consensus mechanism
- [ ] Document API specifications

### Phase 2: Prototype Implementation
- [ ] Build minimal node software
- [ ] Implement basic consensus
- [ ] Create REST API for queries
- [ ] Test with sample image hashes

### Phase 3: Integration
- [ ] Connect to aggregation server
- [ ] End-to-end testing with camera prototype
- [ ] Performance optimization
- [ ] Deploy test network

### Phase 4: Production (2028 Target)
- [ ] Multi-node deployment
- [ ] Production aggregator validators
- [ ] Monitoring and alerting
- [ ] Public verification interface

## Performance Requirements

- **Transaction throughput:** 1,000+ hashes/second (for batch submissions)
- **Query latency:** <100ms for hash verification
- **Storage:** ~100 bytes per image record
- **Projected load:** 10M images/year = ~1GB/year storage
- **Node requirements:** Modest (2-4 core CPU, 8GB RAM, 100GB SSD)

## Security Considerations

1. **Aggregator Authorization:** Only pre-approved aggregators can submit
2. **Replay Protection:** Nonce-based or timestamp-based anti-replay
3. **Data Integrity:** Cryptographic chain prevents tampering
4. **Availability:** Multiple validator nodes prevent single point of failure
5. **Privacy:** Only hash stored, not image content or camera identity

## Why Not Ethereum/zkSync?

**Decision rationale:**
- Gas fees make micropayments impractical at scale
- Merkle root batching adds verification complexity
- Dependency on Ethereum ecosystem creates external risk
- Smart contract upgrades and governance complexity
- Layer 2 still requires Layer 1 settlement costs

**Custom blockchain advantages:**
- Zero per-transaction costs (only hosting)
- Simplified verification (direct hash lookup)
- Complete control over consensus and features
- Purpose-built for image hash verification
- Can optimize for specific use case

## Open Questions

1. **Node hosting:** Self-hosted vs. cloud vs. hybrid?
2. **Validator count:** 3 nodes? 5 nodes? More?
3. **Geographic distribution:** Multi-region for availability?
4. **Public access:** Open read API or authenticated?
5. **Archival strategy:** How long to retain old blocks?
6. **Backup and recovery:** Disaster recovery procedures?

## Related Documentation

- **Project Overview:** `/CLAUDE.md`
- **Aggregation Server:** `/packages/aggregator/` (to be integrated)
- **Camera Prototype:** `/packages/camera-pi/` (submits to aggregator)
- **Phase Plans:** `/docs/phase-plans/`

## Contributing

This package is under active architectural design. Contributions and feedback welcome as we define the optimal blockchain structure for the Birthmark Standard.

---

**Note:** This package previously contained Ethereum smart contracts for zkSync Layer 2. Those have been removed as the project pivoted to a custom blockchain solution in November 2025.

**The Birthmark Standard Foundation**
*Proving images are real, not generated.*
