# Contracts Package

**Phase:** Phase 1
**Status:** In Development
**Blockchain:** zkSync Layer 2 (Testnet)

## Overview

The contracts package contains Solidity smart contracts for the Birthmark Standard blockchain registry. These contracts store Merkle roots of batched image hashes on zkSync Layer 2 for efficient, low-cost verification.

## Key Contract: BirthmarkRegistry.sol

### Responsibilities

1. **Store Merkle Roots:** Accept batches of image hashes as Merkle tree roots
2. **Access Control:** Only authorized aggregators can post batches
3. **Verification:** Provide on-chain Merkle proof verification
4. **Immutability:** Once posted, batch records are permanent

### Key Functions

```solidity
function postBatch(bytes32 merkleRoot, uint256 imageCount) external onlyAggregator returns (uint256)
```
Posts a new batch Merkle root. Returns batch ID.

```solidity
function verifyInclusion(uint256 batchId, bytes32 imageHash, bytes32[] calldata proof, uint256 leafIndex) external view returns (bool)
```
Verifies that an image hash is included in a specific batch using a Merkle proof.

## Architecture

```
Aggregator → zkSync L2 (BirthmarkRegistry) → Ethereum L1 (Settlement)
                    ↓
            Merkle Root Storage
                    ↓
            Verifiable Proofs
```

## Cost Model

**Target:** <$0.00003 per image
**Batch size:** 1,000-5,000 images
**Total cost per batch:** ~$0.10-0.15 on zkSync

## Directory Structure

### `contracts/`
Solidity smart contracts:
- `BirthmarkRegistry.sol` - Main registry contract
- Future: Access control contracts, upgrade mechanisms

### `scripts/`
Deployment and management scripts:
- `deploy.ts` - Deploy contracts to zkSync testnet
- `authorize.ts` - Manage authorized aggregators
- `query.ts` - Query batch information

### `test/`
Hardhat test suite:
- Unit tests for all contract functions
- Gas optimization tests
- Access control tests
- Merkle proof verification tests

## Development

### Setup

```bash
cd packages/contracts
npm install
cp .env.example .env
# Add zkSync testnet RPC URL and deployer private key
```

### Compile

```bash
npx hardhat compile
```

### Test

```bash
npx hardhat test
```

### Deploy (Testnet)

```bash
npx hardhat run scripts/deploy.ts --network zksync-testnet
```

### Verify Contract

```bash
npx hardhat verify --network zksync-testnet <CONTRACT_ADDRESS>
```

## Configuration

### `hardhat.config.ts`

Configures:
- zkSync network settings
- Compiler versions
- Gas reporter
- Etherscan verification

### Environment Variables

```
ZKSYNC_TESTNET_RPC=https://testnet.era.zksync.dev
DEPLOYER_PRIVATE_KEY=0x...
ETHERSCAN_API_KEY=...
```

## Security Considerations

- Only authorized aggregators can post batches
- Merkle roots are immutable once posted
- Ownership transfer mechanisms for aggregator authorization
- Upgrade path for contract improvements (future)

## Phase 1 Limitations

- Testnet only (no real monetary value)
- Single authorized aggregator
- Manual aggregator authorization

## Phase 3 Production Requirements

- Mainnet deployment
- Multi-signature aggregator authorization
- Upgradeable contract pattern
- Emergency pause mechanism
- Governance for aggregator management

## Gas Optimization

- Batch posting optimized for minimal gas
- Merkle proof verification uses efficient keccak256 hashing
- Minimal storage usage per batch
- Event emission for off-chain indexing

## Related Documentation

- Smart contract plan: `docs/phase-plans/Birthmark_Phase_1_Plan_zkSync_Smart_Contract.md`
- Blockchain interface: `shared/protocols/aggregator_to_chain.py`

## zkSync Resources

- zkSync Era Docs: https://era.zksync.io/docs/
- zkSync Testnet Explorer: https://goerli.explorer.zksync.io/
- zkSync Hardhat Plugin: https://era.zksync.io/docs/tools/hardhat/
