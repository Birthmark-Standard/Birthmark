# BirthmarkRegistry Smart Contract

**Version:** 1.0.0
**Blockchain:** zkSync Era (Sepolia Testnet)
**Phase:** Phase 1 - Hardware Prototype
**License:** MIT

## Overview

The `BirthmarkRegistry` contract is the on-chain component of the Birthmark Standard, storing cryptographic proofs of image authenticity on zkSync Era Layer 2. It enables batch submission of image hash Merkle roots with strict access control and pause functionality.

### Key Features

- ✅ **Batch Storage:** Stores Merkle roots representing 1-10,000 image hashes per batch
- ✅ **Access Control:** Owner-managed authorized aggregators
- ✅ **Pause Mechanism:** Emergency pause for batch submissions
- ✅ **Gas Optimized:** Custom errors, efficient storage (target: <$0.00003 per image)
- ✅ **Non-Upgradeable:** Immutable contract for security and simplicity
- ✅ **Event Logging:** Full audit trail via events

## Architecture

```
Aggregation Server  →  BirthmarkRegistry (zkSync Era L2)  →  Ethereum L1 Settlement
                              ↓
                       Batch Storage:
                       - Merkle Root
                       - Timestamp
                       - Image Count
                       - Aggregator Address
```

## Project Structure

```
birthmark-contracts/
├── contracts/
│   └── BirthmarkRegistry.sol       # Main registry contract
├── scripts/
│   ├── deploy.ts                   # Deployment script
│   └── authorize-aggregator.ts     # Aggregator authorization script
├── test/
│   └── BirthmarkRegistry.test.ts   # Comprehensive test suite (>90% coverage)
├── hardhat.config.ts               # Hardhat + zkSync configuration
├── package.json                    # Dependencies and scripts
├── tsconfig.json                   # TypeScript configuration
├── .env.example                    # Environment variables template
└── README.md                       # This file
```

## Prerequisites

### Required Software

- **Node.js:** >=18.0.0
- **npm:** >=9.0.0
- **Git:** For repository management

### Required Accounts

1. **zkSync Sepolia Testnet Wallet:**
   - Create at: https://portal.zksync.io/
   - Fund with testnet ETH: https://portal.zksync.io/faucet

2. **Deployer Wallet:**
   - Private key for deploying the contract
   - Becomes contract owner and first authorized aggregator

3. **Aggregator Wallet (optional for testing):**
   - Separate private key for aggregation server
   - Authorized by owner after deployment

## Installation

```bash
# Clone repository
cd packages/contracts

# Install dependencies
npm install

# Copy environment template
cp .env.example .env

# Edit .env and add your private keys
nano .env
```

### Creating Wallets

**Using MetaMask:**
1. Install MetaMask browser extension
2. Create new wallet or import existing
3. Export private key: Account → Account Details → Export Private Key
4. Add to `.env` file

**Using Hardhat:**
```bash
npx hardhat console
> const wallet = ethers.Wallet.createRandom()
> console.log("Address:", wallet.address)
> console.log("Private Key:", wallet.privateKey)
```

### Getting Testnet ETH

1. Visit https://portal.zksync.io/faucet
2. Connect your wallet
3. Request testnet ETH (0.05-0.1 ETH recommended)
4. Wait for transaction confirmation

## Configuration

### Environment Variables

Edit `.env` file:

```bash
# Deployer wallet (becomes owner)
PRIVATE_KEY=0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef

# zkSync Sepolia RPC URL
ZKSYNC_RPC_URL=https://sepolia.era.zksync.dev

# Deployed contract address (fill after deployment)
CONTRACT_ADDRESS=

# Aggregator wallet (for server, separate from deployer)
AGGREGATOR_PRIVATE_KEY=0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890
```

**⚠️ SECURITY WARNING:**
- Never commit `.env` to version control
- Use separate wallets for deployer and aggregator
- Store private keys securely (password manager, hardware wallet)

## Usage

### 1. Compile Contracts

```bash
npm run compile
```

Expected output:
```
Compiling 1 Solidity file
Successfully compiled 1 Solidity file
```

### 2. Run Tests

```bash
npm test
```

Tests cover:
- ✅ Deployment and initialization
- ✅ Batch submission (success and failure)
- ✅ Access control (authorization, revocation, ownership)
- ✅ Pause mechanism
- ✅ Batch queries
- ✅ Multiple aggregators
- ✅ Gas usage reporting

Expected result: **>90% coverage, all tests passing**

### 3. Deploy to Testnet

```bash
npm run deploy:testnet
```

Expected output:
```
🚀 Deploying BirthmarkRegistry to zkSync Era...

📍 Deployer address: 0x1234...5678
💰 Deployer balance: 0.05 ETH

⏳ Deploying contract...
✅ Contract deployed successfully!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 Contract Address: 0xabcd...ef01
👤 Owner: 0x1234...5678
🔑 Deployer Authorized: true
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 Next steps:
1. Save contract address to .env
2. Verify contract (optional)
3. Authorize additional aggregators
```

**Save the contract address to `.env`:**
```bash
CONTRACT_ADDRESS=0xabcd...ef01
```

### 4. Verify Contract (Optional)

```bash
npx hardhat verify --network zkSyncTestnet <CONTRACT_ADDRESS>
```

This makes the contract source code public on zkSync Explorer.

### 5. Authorize Aggregators

Authorize your aggregation server wallet to submit batches:

```bash
npm run authorize -- 0xAGGREGATOR_ADDRESS_HERE
```

Expected output:
```
🔑 Authorizing new aggregator...

📍 Aggregator to authorize: 0x9876...5432
👤 Owner address: 0x1234...5678
✅ Owner verification passed

⏳ Sending authorization transaction...
✅ Aggregator authorized successfully!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 Aggregator: 0x9876...5432
📦 Transaction: 0xdef0...1234
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Smart Contract Reference

### Core Functions

#### `submitBatch(bytes32 merkleRoot, uint32 imageCount)`
Submits a new batch of image hashes as a Merkle root.

**Parameters:**
- `merkleRoot`: Root hash of Merkle tree (32 bytes, non-zero)
- `imageCount`: Number of images (1-10,000)

**Returns:** `uint256 batchId` - Sequential batch identifier

**Requirements:**
- Caller must be authorized aggregator
- Contract must not be paused
- Merkle root cannot be zero
- Image count must be 1-10,000

**Events:** `BatchSubmitted(batchId, merkleRoot, imageCount, aggregator)`

#### `getBatch(uint256 batchId)`
Retrieves batch information.

**Returns:**
- `merkleRoot`: bytes32
- `timestamp`: uint64 (block timestamp)
- `aggregator`: address (who submitted)
- `imageCount`: uint32

#### `batchExists(uint256 batchId)`
Checks if a batch exists.

**Returns:** `bool` - True if batch exists

### Access Control Functions

#### `authorizeAggregator(address aggregator)`
Authorizes a new aggregator (owner only).

**Events:** `AggregatorAuthorized(aggregator)`

#### `revokeAggregator(address aggregator)`
Revokes aggregator authorization (owner only).

**Events:** `AggregatorRevoked(aggregator)`

#### `transferOwnership(address newOwner)`
Transfers contract ownership (owner only).

**Events:** `OwnershipTransferred(previousOwner, newOwner)`

### Pause Functions

#### `pause()`
Pauses batch submissions (owner only).

**Events:** `Paused(account)`

#### `unpause()`
Unpauses batch submissions (owner only).

**Events:** `Unpaused(account)`

## Cost Model

### zkSync Era Gas Costs

Based on testnet measurements:

| Operation | Estimated Gas | Cost (at 0.01 gwei) |
|-----------|--------------|---------------------|
| Deploy Contract | ~2,000,000 gas | ~$0.10 |
| Submit Batch (1,000 images) | ~150,000 gas | ~$0.03 |
| Authorize Aggregator | ~50,000 gas | ~$0.01 |

**Target:** <$0.00003 per image
**Batch Size:** 1,000-5,000 images
**Total Cost per Batch:** ~$0.03 for 1,000 images = $0.00003/image ✅

## Security Considerations

### Access Control
- ✅ Only authorized aggregators can submit batches
- ✅ Only owner can manage aggregators and pause contract
- ✅ Deployer automatically becomes owner and first aggregator

### Data Integrity
- ✅ Merkle roots are immutable once stored
- ✅ Input validation prevents zero or invalid values
- ✅ Sequential batch IDs prevent collisions

### Emergency Response
- ✅ Pause mechanism stops batch submissions
- ✅ Owner can still manage authorization when paused
- ✅ No upgrade mechanism (simpler, more secure for audit)

### Known Limitations (Phase 1)
- ❌ No on-chain Merkle proof verification (done off-chain by clients)
- ❌ No multi-sig owner control (single owner)
- ❌ Non-upgradeable (by design for security)

## Integration with Aggregation Server

The aggregation server interacts with this contract:

```typescript
import { Contract, Wallet, Provider } from "zksync-ethers";

// Connect to contract
const provider = new Provider("https://sepolia.era.zksync.dev");
const wallet = new Wallet(AGGREGATOR_PRIVATE_KEY, provider);
const contract = new Contract(CONTRACT_ADDRESS, ABI, wallet);

// Submit batch
const merkleRoot = "0x1234..."; // Computed from image hashes
const imageCount = 1000;

const tx = await contract.submitBatch(merkleRoot, imageCount);
const receipt = await tx.wait();

console.log(`Batch submitted: ${receipt.transactionHash}`);
```

See `packages/aggregator/src/blockchain/` for full implementation.

## Troubleshooting

### "PRIVATE_KEY not found"
**Solution:** Copy `.env.example` to `.env` and add your private key.

### "Deployer wallet has zero balance"
**Solution:** Fund wallet with testnet ETH from https://portal.zksync.io/faucet

### "Not authorized" error
**Solution:**
- Ensure you're using the owner wallet for admin functions
- Ensure aggregator is authorized before submitting batches

### "InvalidMerkleRoot" error
**Solution:** Merkle root cannot be zero bytes. Check your hash computation.

### "ImageCountTooHigh" error
**Solution:** Maximum 10,000 images per batch. Split into multiple batches.

### "ContractPaused" error
**Solution:** Contract is paused. Owner must call `unpause()`.

### Compilation errors
**Solution:**
```bash
npm run clean
npm install
npm run compile
```

## Development

### Running Local Tests

```bash
# Run all tests
npm test

# Run with gas reporting
REPORT_GAS=true npm test

# Run specific test file
npx hardhat test test/BirthmarkRegistry.test.ts
```

### Code Style

- Solidity: NatSpec comments on all public functions
- TypeScript: ESLint + Prettier (auto-format on save)
- Custom errors instead of require strings (gas optimization)

### Adding New Features

1. Modify `contracts/BirthmarkRegistry.sol`
2. Add tests to `test/BirthmarkRegistry.test.ts`
3. Run tests: `npm test`
4. Compile: `npm run compile`
5. Deploy to testnet: `npm run deploy:testnet`

## Related Documentation

- **Birthmark Project Overview:** `/CLAUDE.md`
- **Phase 1 Plan:** `/docs/phase-plans/Birthmark_Phase_1_Plan_zkSync_Smart_Contract.md`
- **Aggregation Server:** `/packages/aggregator/`
- **Camera Prototype:** `/packages/camera-pi/`

## Resources

### zkSync Era
- **Docs:** https://era.zksync.io/docs/
- **Sepolia Explorer:** https://sepolia.explorer.zksync.io/
- **Faucet:** https://portal.zksync.io/faucet
- **Hardhat Plugin:** https://era.zksync.io/docs/tools/hardhat/

### Hardhat
- **Docs:** https://hardhat.org/docs
- **zkSync Plugin:** https://github.com/matter-labs/hardhat-zksync

### Solidity
- **Docs:** https://docs.soliditylang.org/
- **Style Guide:** https://docs.soliditylang.org/en/latest/style-guide.html

## Support

- **GitHub Issues:** https://github.com/Birthmark-Standard/Birthmark/issues
- **Founder:** Samuel C. Ryan
- **Organization:** The Birthmark Standard Foundation

## License

MIT License - See LICENSE file for details.

---

**The Birthmark Standard Foundation**
*Proving images are real, not generated.*
