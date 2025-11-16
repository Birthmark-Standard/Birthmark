# Blockchain Package

**Phase:** Phase 1 (Architecture Planning)
**Status:** In Development
**Blockchain:** Custom Birthmark Blockchain

## Overview

The blockchain package will contain the implementation for the Birthmark Standard's custom blockchain that stores full image hashes on-chain rather than Merkle roots on a Layer 2 solution.

## Architecture Change

**Previous Approach (Removed):**
- zkSync Era Layer 2 on Ethereum
- Stored Merkle roots of batched image hashes
- Off-chain Merkle proof verification
- Cost: ~$0.00003 per image

**New Approach (In Development):**
- Custom blockchain hosted by Birthmark Standard
- Stores full image hashes directly on-chain
- Direct hash verification without Merkle proofs
- Eliminates dependency on Ethereum/zkSync infrastructure

## Benefits of Custom Blockchain

1. **Full Control:** Complete ownership of infrastructure and consensus
2. **Direct Storage:** Full SHA-256 hashes stored on-chain (no Merkle trees needed)
3. **Cost Optimization:** No gas fees or Layer 2 costs
4. **Simplified Architecture:** Direct hash lookups without proof generation
5. **Independence:** No reliance on Ethereum ecosystem or zkSync

## Directory Structure

### `contracts/` (To Be Determined)
Blockchain implementation code - technology stack TBD

### `scripts/` (To Be Determined)
Node deployment and management scripts

### `test/` (To Be Determined)
Blockchain and consensus tests

## Technology Stack (Under Evaluation)

Options being considered:
- Custom blockchain implementation
- Fork of existing blockchain (e.g., Cosmos SDK, Substrate)
- Simplified proof-of-authority consensus
- Direct database-backed ledger with cryptographic verification

## Next Steps

1. Define blockchain architecture and consensus mechanism
2. Choose technology stack
3. Design block structure and data format
4. Implement node software
5. Create deployment infrastructure
6. Build API for aggregation server integration

## Related Documentation

- Project overview: `/CLAUDE.md`
- Aggregation server: `/packages/aggregator/`
- Camera prototype: `/packages/camera-pi/`

---

**Note:** This package previously contained zkSync Era smart contracts, which have been removed as the project pivots to a custom blockchain solution.
