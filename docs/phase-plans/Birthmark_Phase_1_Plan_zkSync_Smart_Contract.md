# Birthmark Standard - Phase 1 Plan: zkSync Smart Contract

**Version:** 1.0  
**Date:** November 11, 2025  
**Project:** The Birthmark Standard Foundation  
**Author:** Samuel C. Ryan

---

## Executive Summary

This document outlines the development plan for the Birthmark Standard's smart contract infrastructure on zkSync Era. The smart contract serves as the immutable registry for cryptographic image hashes, enabling verifiable proof that images were captured by authenticated cameras rather than AI-generated or manipulated.

**Key Objectives:**
- Deploy production-ready smart contract on zkSync Era mainnet
- Achieve target cost of <$0.0001 per image hash through batch processing
- Pass third-party security audit before mainnet deployment
- Integrate with aggregation server for seamless hash submission
- Support verification queries with <5 second latency

**Timeline:** 15 weeks from contract start  
**Budget:** ~$27,000 (developer time + audit + deployment costs)  
**Platform:** zkSync Era (Ethereum Layer 2)

---

## 1. Technical Architecture Overview

### 1.1 System Components

The Birthmark Standard uses a three-layer architecture:

1. **Camera Layer** - Hardware devices capture images and generate cryptographic hashes
2. **Aggregation Layer** - Servers batch hashes and post to blockchain
3. **Blockchain Layer** - zkSync Era smart contract provides immutable registry

The smart contract serves as the **source of truth** for image authenticity, storing Merkle roots that represent batches of 1,000-5,000 image hashes.

### 1.2 Why zkSync Era?

**Selected Technology:** zkSync Era on Ethereum Mainnet

**Rationale:**
- **EVM-compatible:** Uses standard Solidity, easier developer recruitment
- **Proven production system:** Live since March 2023 with significant TVL
- **Cost-effective:** $0.15-0.30 per L1 transaction, batching 2,000-5,000 operations
  - **= $0.00003-0.00006 per image hash** (well below $0.0001 target)
- **Native account abstraction:** Enables sponsored transactions for future use cases
- **Cryptographic validity proofs:** Zero-knowledge proofs ensure correctness (vs optimistic rollups)
- **Strong ecosystem:** Extensive tooling, documentation, and community support

**Decision Locked:** zkSync Era is the definitive platform choice. StarkNet evaluation is complete and closed.

### 1.3 Smart Contract Architecture

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title BirthmarkRegistry
 * @notice Immutable registry of image hash batches for the Birthmark Standard
 * @dev Aggregators submit Merkle roots representing batches of authenticated images
 */
contract BirthmarkRegistry {
    
    struct Batch {
        bytes32 merkleRoot;      // Root of Merkle tree (2,000-5,000 images)
        uint64 timestamp;        // Block timestamp of submission
        address aggregator;      // Which aggregator posted this batch
        uint32 imageCount;       // Number of images in this batch
    }
    
    // Storage
    mapping(uint256 => Batch) public batches;
    uint256 public batchCount;
    mapping(address => bool) public authorizedAggregators;
    
    // Events
    event BatchSubmitted(
        uint256 indexed batchId,
        bytes32 merkleRoot,
        uint32 imageCount,
        address indexed aggregator
    );
    
    event AggregatorAuthorized(address indexed aggregator);
    event AggregatorRevoked(address indexed aggregator);
    
    // Access control
    address public owner;
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }
    
    modifier onlyAuthorized() {
        require(authorizedAggregators[msg.sender], "Not authorized");
        _;
    }
    
    constructor() {
        owner = msg.sender;
        authorizedAggregators[msg.sender] = true; // Owner is initial aggregator
    }
    
    /**
     * @notice Submit a batch of image hashes (as Merkle root)
     * @param _merkleRoot Root hash of the Merkle tree
     * @param _imageCount Number of images in this batch
     * @return batchId Unique identifier for this batch
     */
    function submitBatch(bytes32 _merkleRoot, uint32 _imageCount) 
        external 
        onlyAuthorized 
        returns (uint256 batchId) 
    {
        require(_merkleRoot != bytes32(0), "Invalid root");
        require(_imageCount > 0 && _imageCount <= 10000, "Invalid count");
        
        batchCount++;
        batches[batchCount] = Batch({
            merkleRoot: _merkleRoot,
            timestamp: uint64(block.timestamp),
            aggregator: msg.sender,
            imageCount: _imageCount
        });
        
        emit BatchSubmitted(batchCount, _merkleRoot, _imageCount, msg.sender);
        
        return batchCount;
    }
    
    /**
     * @notice Get batch details by ID
     * @param batchId The batch identifier
     * @return Batch struct with all details
     */
    function getBatch(uint256 batchId) external view returns (Batch memory) {
        require(batchId > 0 && batchId <= batchCount, "Invalid batch ID");
        return batches[batchId];
    }
    
    /**
     * @notice Authorize a new aggregator
     * @param aggregator Address to authorize
     */
    function authorizeAggregator(address aggregator) external onlyOwner {
        require(aggregator != address(0), "Invalid address");
        authorizedAggregators[aggregator] = true;
        emit AggregatorAuthorized(aggregator);
    }
    
    /**
     * @notice Revoke aggregator authorization
     * @param aggregator Address to revoke
     */
    function revokeAggregator(address aggregator) external onlyOwner {
        authorizedAggregators[aggregator] = false;
        emit AggregatorRevoked(aggregator);
    }
    
    /**
     * @notice Transfer ownership (for governance transition)
     * @param newOwner New owner address
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Invalid address");
        owner = newOwner;
    }
}
```

### 1.4 Verification Process

The verification flow works as follows:

1. **User uploads image** to verification service (web interface or API)
2. **Service computes SHA-256 hash** of the uploaded image
3. **Query aggregators** to find which batch (if any) contains this hash
4. **Aggregator returns Merkle proof** linking the image hash to a batch's Merkle root
5. **Verify proof** against on-chain Merkle root in the smart contract
6. **Return result** to user: Verified ✓ / Not Found / Invalid Proof

**Key insight:** The smart contract only stores Merkle roots (32 bytes each), not individual image hashes. This enables massive scalability while maintaining cryptographic proof of inclusion.

---

## 2. Development Phases

### Phase 1: Local Development & Testing (Weeks 1-3)

#### Week 1: Environment Setup

**Objective:** Establish complete development environment with zkSync tooling

**Tasks:**
- Install zkSync Era local test node: `era-test-node`
- Set up Hardhat with zkSync plugins:
  - `@matterlabs/hardhat-zksync-solc` (Solidity compiler)
  - `@matterlabs/hardhat-zksync-deploy` (deployment scripts)
  - `@matterlabs/hardhat-zksync-verify` (contract verification)
- Configure Hardhat project structure:
  ```
  contracts/
    BirthmarkRegistry.sol
    test/
  scripts/
    deploy.ts
    authorize-aggregator.ts
  test/
    BirthmarkRegistry.test.ts
  hardhat.config.ts
  ```
- Set up development wallet with test ETH
- Configure environment variables for RPC endpoints and private keys

**Deliverables:**
- [ ] Working Hardhat project compiles successfully
- [ ] Local zkSync node runs and accepts transactions
- [ ] Deployment script successfully deploys to local network
- [ ] Development environment documentation

#### Week 2: Core Contract Development

**Objective:** Implement and test BirthmarkRegistry smart contract

**Tasks:**
- Implement smart contract following architecture in Section 1.3
- Write comprehensive unit tests:
  - Batch submission with valid parameters
  - Authorization checks (only authorized aggregators can submit)
  - Owner-only functions (authorize/revoke aggregators, transfer ownership)
  - Edge cases (zero values, max values, invalid inputs)
  - Event emission verification
  - Gas cost measurement for different batch sizes
- Document all public functions with NatSpec comments
- Implement test fixtures for common scenarios

**Test Coverage Requirements:**
- [ ] >90% line coverage
- [ ] >85% branch coverage
- [ ] All revert conditions tested
- [ ] Gas benchmarks documented

**Deliverables:**
- [ ] Complete smart contract implementation
- [ ] Comprehensive test suite (>90% coverage)
- [ ] Gas optimization baseline measurements
- [ ] Initial security checklist review

#### Week 3: Testing Infrastructure & Optimization

**Objective:** Validate contract behavior and optimize gas consumption

**Tasks:**
- Test batch size variations (1,000 / 2,500 / 5,000 / 10,000 images)
- Measure gas costs for each batch size on local node
- Mock multiple aggregator scenarios:
  - Multiple aggregators submitting batches
  - Authorization and revocation workflows
  - Ownership transfers
- Implement integration test harness simulating full workflow:
  - Mock camera hash generation
  - Batch accumulation (simulated)
  - Merkle tree generation
  - Smart contract submission
  - Verification query simulation
- Document gas optimization opportunities

**Gas Cost Targets:**
- Batch submission: <500,000 gas (target: ~300,000 gas)
- Authorization: <50,000 gas
- Query operations: <50,000 gas (view functions are free)

**Deliverables:**
- [ ] Gas optimization report with recommendations
- [ ] Integration test suite demonstrating end-to-end flow
- [ ] Performance benchmarks documented
- [ ] Code review checklist completed

---

### Phase 2: Testnet Deployment (Weeks 4-6)

#### Week 4: zkSync Sepolia Deployment

**Objective:** Deploy contract to zkSync Sepolia testnet and validate in live environment

**Tasks:**
- Configure Sepolia testnet RPC endpoints:
  - zkSync Sepolia RPC: `https://sepolia.era.zksync.dev`
  - Ethereum Sepolia RPC: `https://rpc.sepolia.org`
- Fund deployment wallet with testnet ETH:
  - Bridge Sepolia ETH to zkSync Sepolia via bridge
  - Ensure sufficient balance for multiple deployments
- Deploy BirthmarkRegistry to testnet
- Verify contract on zkSync Era Block Explorer
- Configure block explorer monitoring:
  - Set up alerts for contract interactions
  - Monitor transaction success rates
  - Track gas costs in real environment

**Testnet Resources:**
- Faucet: https://portal.zksync.io/faucet
- Bridge: https://portal.zksync.io/bridge
- Explorer: https://sepolia.explorer.zksync.io

**Deliverables:**
- [ ] Contract deployed and verified on zkSync Sepolia
- [ ] Deployment documentation with addresses and transaction hashes
- [ ] Block explorer monitoring configured
- [ ] Testnet deployment scripts

#### Week 5: Aggregation Server Integration

**Objective:** Replace mock blockchain functions with real zkSync integration

**Tasks:**
- Implement Python integration layer using `web3.py`
- Replace `mock_blockchain_post()` in aggregation server with `zksync_post_batch()`
- Key integration functions:

```python
# aggregation_server/blockchain.py

from eth_account import Account
from web3 import Web3
from web3.middleware import geth_poa_middleware
import json
from typing import Optional
from uuid import UUID

# Load configuration
ZKSYNC_RPC = os.getenv("ZKSYNC_RPC_URL", "https://sepolia.era.zksync.dev")
CONTRACT_ADDRESS = os.getenv("BIRTHMARK_REGISTRY_ADDRESS")
AGGREGATOR_PRIVATE_KEY = os.getenv("AGGREGATOR_PRIVATE_KEY")
AGGREGATOR_ADDRESS = Account.from_key(AGGREGATOR_PRIVATE_KEY).address

# Load contract ABI
with open("contracts/BirthmarkRegistry.json", "r") as f:
    CONTRACT_ABI = json.load(f)["abi"]

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(ZKSYNC_RPC))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Contract instance
birthmark_registry = w3.eth.contract(
    address=CONTRACT_ADDRESS,
    abi=CONTRACT_ABI
)

async def zksync_post_batch(
    batch_id: UUID, 
    merkle_root: str, 
    image_count: int
) -> str:
    """
    Post Merkle root to zkSync smart contract
    
    Args:
        batch_id: Internal database batch ID
        merkle_root: Hex string (64 chars, no 0x prefix)
        image_count: Number of images in batch
        
    Returns:
        Transaction hash (hex string with 0x prefix)
        
    Raises:
        ValueError: If parameters are invalid
        Exception: If transaction fails
    """
    try:
        # Validate inputs
        if len(merkle_root) != 64:
            raise ValueError(f"Invalid merkle root length: {len(merkle_root)}")
        if image_count <= 0 or image_count > 10000:
            raise ValueError(f"Invalid image count: {image_count}")
        
        # Convert merkle root to bytes32
        merkle_root_bytes = bytes.fromhex(merkle_root)
        
        # Get current nonce
        nonce = w3.eth.get_transaction_count(AGGREGATOR_ADDRESS)
        
        # Build transaction
        tx = birthmark_registry.functions.submitBatch(
            merkle_root_bytes,
            image_count
        ).build_transaction({
            'from': AGGREGATOR_ADDRESS,
            'nonce': nonce,
            'gas': 500000,  # Will optimize based on testing
            'gasPrice': w3.eth.gas_price,
        })
        
        # Sign transaction
        signed_tx = w3.eth.account.sign_transaction(tx, AGGREGATOR_PRIVATE_KEY)
        
        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        print(f"Batch {batch_id} submitted. TX: {tx_hash.hex()}")
        
        # Wait for confirmation (zkSync is fast, ~10-15 seconds)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        
        if receipt['status'] != 1:
            raise Exception(f"Transaction failed: {tx_hash.hex()}")
        
        # Extract batch ID from event logs
        batch_events = birthmark_registry.events.BatchSubmitted().process_receipt(receipt)
        if not batch_events:
            raise Exception("No BatchSubmitted event found in receipt")
        
        on_chain_batch_id = batch_events[0]['args']['batchId']
        
        # Update database
        await db.execute(
            """
            UPDATE batches SET 
                status = 'confirmed',
                zksync_tx_hash = $1,
                zksync_block_number = $2,
                on_chain_batch_id = $3,
                confirmed_at = NOW()
            WHERE batch_id = $4
            """,
            tx_hash.hex(),
            receipt['blockNumber'],
            on_chain_batch_id,
            batch_id
        )
        
        print(f"Batch {batch_id} confirmed. On-chain ID: {on_chain_batch_id}")
        
        return tx_hash.hex()
        
    except Exception as e:
        # Update database with failure status
        await db.execute(
            """
            UPDATE batches SET 
                status = 'failed',
                error_message = $1
            WHERE batch_id = $2
            """,
            str(e),
            batch_id
        )
        raise


async def verify_batch_on_chain(on_chain_batch_id: int) -> Optional[dict]:
    """
    Query smart contract for batch details
    
    Args:
        on_chain_batch_id: Batch ID returned by smart contract
        
    Returns:
        Dictionary with batch details or None if not found
    """
    try:
        batch = birthmark_registry.functions.getBatch(on_chain_batch_id).call()
        
        return {
            "merkle_root": batch[0].hex(),
            "timestamp": batch[1],
            "aggregator": batch[2],
            "image_count": batch[3]
        }
    except Exception as e:
        print(f"Error querying batch {on_chain_batch_id}: {e}")
        return None
```

- Implement retry logic for transient failures (network issues, gas price spikes)
- Add transaction monitoring and alerting
- Test edge cases:
  - Unauthorized aggregator attempts
  - Network connectivity issues
  - Gas price volatility
  - Transaction confirmation delays

**Deliverables:**
- [ ] Python integration module complete
- [ ] Mock functions replaced with real zkSync calls
- [ ] Error handling and retry logic implemented
- [ ] Integration tests pass on testnet

#### Week 6: End-to-End Testing

**Objective:** Validate complete workflow from hash generation to verification

**Tasks:**
- Test complete flow using Python scripts to simulate cameras:
  1. Generate mock image hashes (SHA-256)
  2. Submit hashes to aggregation server API
  3. Aggregation server accumulates batch
  4. Generate Merkle tree from batch
  5. Post Merkle root to zkSync testnet
  6. Query verification status via API
  7. Validate Merkle proof against on-chain root
- Measure actual performance metrics:
  - Gas costs per batch (different sizes)
  - Transaction confirmation times
  - End-to-end latency (hash submission → verification query)
- Test batch size optimization:
  - 1,000 images: Higher per-image cost, faster batching
  - 2,500 images: Balanced approach
  - 5,000 images: Lower per-image cost, longer batching delay
- Stress test: Submit multiple batches in sequence
- Document optimal batching strategy based on real data

**Success Metrics:**
- [ ] Gas cost <$0.0001 per image (target achieved)
- [ ] Transaction confirmation <30 seconds
- [ ] Verification query latency <5 seconds
- [ ] Zero failed transactions in stress test

**Deliverables:**
- [ ] End-to-end test suite with real testnet transactions
- [ ] Performance analysis report with batch size recommendations
- [ ] Cost model validation
- [ ] Updated documentation with testnet learnings

---

### Phase 3: Security & Optimization (Weeks 7-9)

#### Week 7: Access Control & Security Hardening

**Objective:** Implement robust security controls and test attack vectors

**Tasks:**
- **Access Control Review:**
  - Validate aggregator authorization mechanism
  - Test unauthorized submission attempts
  - Verify owner-only function protection
  - Document ownership transfer procedure
- **Emergency Controls:**
  - Consider adding pause functionality for emergency situations
  - Document incident response procedures
  - Plan for governance transition (owner → multisig → DAO)
- **Input Validation:**
  - Test boundary conditions (zero values, max uint values)
  - Validate Merkle root format (must be 32 bytes)
  - Test image count limits
- **Attack Vector Testing:**
  - Front-running attempts (does it matter for our use case?)
  - Replay attacks (can old transactions be resubmitted?)
  - DoS via large batch submissions
  - Unauthorized aggregator impersonation
  - Ownership takeover attempts

**Security Checklist:**
- [ ] All external functions have appropriate access control
- [ ] Input validation on all parameters
- [ ] No integer overflow/underflow risks (Solidity 0.8+ handles this)
- [ ] Events emitted for all state changes
- [ ] No reentrancy vulnerabilities (no external calls during state changes)
- [ ] Gas limits prevent DoS attacks
- [ ] Owner key security documented

**Deliverables:**
- [ ] Security analysis report
- [ ] Attack vector test results
- [ ] Access control documentation
- [ ] Emergency response procedures

#### Week 8: Gas Optimization

**Objective:** Minimize transaction costs while maintaining security

**Tasks:**
- **Storage Optimization:**
  - Use packed structs to reduce storage slots
  - Evaluate uint256 vs uint32/uint64 trade-offs
  - Consider storage vs memory usage patterns
- **Computation Optimization:**
  - Minimize loops (we don't have any, but validate)
  - Optimize event emission (indexed vs non-indexed parameters)
  - Review function visibility (external vs public)
- **Transaction Optimization:**
  - Test EIP-2930 access lists for repeat aggregators
  - Measure gas savings from access list usage
  - Document optimal gas price strategies
- **Batch Size Analysis:**
  - Measure actual gas costs on testnet for each batch size
  - Calculate cost per image for different batch sizes
  - Document trade-offs: cost vs latency vs complexity

**Gas Cost Target Validation:**
- Batch of 2,000 images:
  - zkSync L2 gas: ~300,000 gas units
  - zkSync L1 gas (proof posting): amortized across many L2 txs
  - Total cost: ~$0.20 per batch
  - **Per-image cost: $0.0001** ✓
- Batch of 5,000 images:
  - zkSync L2 gas: ~350,000 gas units (marginal increase)
  - Total cost: ~$0.25 per batch
  - **Per-image cost: $0.00005** ✓✓

**Deliverables:**
- [ ] Gas optimization report
- [ ] Cost analysis for different batch sizes
- [ ] Recommended batch size (likely 2,500-5,000 images)
- [ ] Optimized contract code (if changes needed)

#### Week 9: Pre-Audit Preparation

**Objective:** Prepare comprehensive documentation and testing artifacts for security audit

**Tasks:**
- **Code Quality:**
  - Final code review and cleanup
  - Ensure consistent style and formatting
  - Remove debugging code and comments
  - Finalize NatSpec documentation
- **Test Coverage:**
  - Achieve >95% test coverage
  - Document any untested edge cases (with justification)
  - Add fuzzing tests for input validation
- **Documentation Package:**
  - Architecture overview (this document)
  - Security assumptions and threat model
  - Known limitations and future improvements
  - Access control model and governance plan
  - Integration documentation for aggregation server
- **Audit Preparation:**
  - Create audit scope document
  - List specific areas of concern
  - Prepare test environment for auditors
  - Compile list of questions for auditors

**Audit Scope Document Contents:**
- [ ] Contract purpose and business logic
- [ ] Trust assumptions (who can do what)
- [ ] Known limitations
- [ ] Integration points (aggregation server, verification API)
- [ ] Governance model (current and future)
- [ ] Specific review requests (e.g., "validate Merkle proof verification")

**Deliverables:**
- [ ] Final code review completed
- [ ] >95% test coverage achieved
- [ ] Complete audit preparation package
- [ ] Auditor engagement contracts signed

---

### Phase 4: Security Audit (Weeks 10-12)

#### Week 10-11: Third-Party Security Audit

**Objective:** Independent security review by professional auditors

**Audit Firms (Recommended):**
1. **OpenZeppelin** - Industry standard, excellent reputation
2. **Consensys Diligence** - Strong zkSync experience
3. **Trail of Bits** - Deep security expertise
4. **Least Authority** - Privacy and cryptography focus

**Budget:** $20,000 (standard for comprehensive smart contract audit)

**Audit Scope:**
- Smart contract security review (BirthmarkRegistry.sol)
- Access control and authorization logic
- Gas optimization opportunities
- Integration security (aggregation server → blockchain)
- Cryptographic assumptions (Merkle tree validation)
- Governance and ownership model

**Audit Process:**
1. **Week 10: Initial Review**
   - Auditors review code and documentation
   - Initial findings reported (preliminary report)
   - Questions and clarifications exchanged
2. **Week 11: Deep Dive**
   - Auditors perform detailed analysis
   - Automated tools run (Slither, Mythril, etc.)
   - Manual code review and threat modeling
   - Draft report delivered

**Expected Finding Categories:**
- **Critical:** Issues that could lead to loss of funds or system failure
- **High:** Significant security concerns requiring immediate attention
- **Medium:** Important issues that should be addressed
- **Low:** Minor issues and best practice recommendations
- **Informational:** Code quality and optimization suggestions

**Deliverables:**
- [ ] Signed audit engagement contract
- [ ] Complete audit report with findings
- [ ] Auditor recommendations document
- [ ] Public disclosure plan (post-remediation)

#### Week 12: Audit Remediation

**Objective:** Address all audit findings and prepare for mainnet deployment

**Tasks:**
- **Triage Findings:**
  - Categorize by severity and urgency
  - Create remediation plan with priorities
  - Estimate effort for each fix
- **Implement Fixes:**
  - Address all Critical and High severity findings
  - Implement Medium severity fixes where feasible
  - Document decisions on Low/Informational findings
- **Re-Testing:**
  - Test all changes thoroughly
  - Ensure fixes don't introduce new issues
  - Maintain test coverage >95%
- **Auditor Review:**
  - Submit fixes to auditors for review
  - Obtain final sign-off on remediation
  - Request updated audit report

**Remediation Process:**
```
Finding → Fix → Test → Review → Verify → Document
```

**Quality Gates:**
- [ ] All Critical findings resolved
- [ ] All High findings resolved
- [ ] Medium findings resolved or documented as accepted risk
- [ ] Auditor sign-off obtained
- [ ] Test coverage maintained >95%
- [ ] No new issues introduced

**Deliverables:**
- [ ] Remediation tracking spreadsheet
- [ ] Updated contract code (post-audit)
- [ ] Final audit report with auditor sign-off
- [ ] Public security disclosure (if appropriate)

---

### Phase 5: Mainnet Deployment (Weeks 13-15)

#### Week 13: Mainnet Deployment Strategy

**Objective:** Deploy audited contract to zkSync Era mainnet with controlled rollout

**Pre-Deployment Checklist:**
- [ ] Security audit completed and findings addressed
- [ ] Test coverage >95%
- [ ] All tests passing on testnet
- [ ] Deployment scripts tested and documented
- [ ] Mainnet wallet funded with sufficient ETH
- [ ] Monitoring and alerting infrastructure ready
- [ ] Incident response plan documented
- [ ] Backup and recovery procedures tested

**Deployment Process:**

1. **Deploy Contract:**
   ```bash
   # Deploy to zkSync Era mainnet
   npx hardhat deploy-zksync --network zkSyncMainnet --script deploy.ts
   
   # Verify contract on explorer
   npx hardhat verify --network zkSyncMainnet <CONTRACT_ADDRESS>
   ```

2. **Initialize Access Control:**
   - Set up initial authorized aggregators (start with 1-2 trusted)
   - Configure owner address (use multisig for governance)
   - Document all addresses and transactions

3. **Configure Monitoring:**
   - Set up block explorer monitoring
   - Configure transaction alerts (success/failure)
   - Set up gas price monitoring
   - Configure uptime monitoring for aggregation server

**Initial Aggregator Whitelist:**
- Foundation-operated aggregator (primary)
- Backup aggregator (redundancy)
- Additional aggregators added gradually post-launch

**Mainnet Resources:**
- RPC: `https://mainnet.era.zksync.io`
- Explorer: `https://explorer.zksync.io`
- Bridge: `https://portal.zksync.io/bridge`

**Deliverables:**
- [ ] Contract deployed to mainnet
- [ ] Contract verified on zkSync Era Block Explorer
- [ ] Initial access control configured
- [ ] Monitoring and alerting operational
- [ ] Deployment documentation complete

#### Week 14: Production Integration

**Objective:** Integrate mainnet contract with aggregation server and validate production workflow

**Tasks:**
- **Update Aggregation Server:**
  - Switch from testnet to mainnet RPC endpoints
  - Update contract address in configuration
  - Validate aggregator wallet has sufficient ETH
  - Test transaction signing with mainnet keys
- **Implement Production Features:**
  - Transaction retry logic (exponential backoff)
  - Gas price optimization (dynamic gas pricing)
  - Error handling and alerting
  - Transaction queue management
  - Database backup before mainnet submissions
- **Monitoring Setup:**
  - Transaction success rate dashboard
  - Gas cost tracking (per transaction and per image)
  - Confirmation time metrics
  - Failed transaction alerts
  - Balance alerts (low ETH warning)
- **Incident Response:**
  - Document runbook for common issues
  - Set up on-call rotation (if team grows)
  - Create escalation procedures
  - Test incident response scenarios

**Production Monitoring Dashboard:**
- Real-time transaction status
- Gas cost per batch (rolling average)
- Success/failure rate (target: >99.9%)
- Average confirmation time
- Aggregator wallet balance
- Smart contract interaction metrics

**Deliverables:**
- [ ] Aggregation server production-ready
- [ ] Monitoring dashboard operational
- [ ] Incident response procedures documented
- [ ] Production readiness checklist completed

#### Week 15: Limited Production Launch

**Objective:** Begin processing real image hashes with controlled rollout

**Launch Strategy:**
- **Phase 15a (Days 1-3): Internal Testing**
  - Process 100-500 test images
  - Validate end-to-end flow on mainnet
  - Monitor costs and performance
  - Verify all monitoring and alerting works
- **Phase 15b (Days 4-7): Limited Users**
  - Onboard 10-20 early adopters
  - Process first real batches (1,000-2,000 images)
  - Collect user feedback
  - Monitor for any issues
- **Phase 15c (Days 8-14): Gradual Expansion**
  - Expand to 50-100 users
  - Increase batch sizes to optimal level (2,500-5,000)
  - Begin testing verification API at scale
  - Document operational learnings

**Success Metrics:**
- [ ] Zero critical incidents
- [ ] Gas cost target achieved (<$0.0001/image)
- [ ] 99.9%+ transaction success rate
- [ ] <30 second average confirmation time
- [ ] <5 second verification query latency
- [ ] Positive user feedback (>80% satisfaction)

**Risk Management:**
- Start with small batches (1,000 images)
- Monitor gas costs closely (auto-pause if costs spike)
- Have emergency pause procedure ready
- Maintain backup aggregator for redundancy
- Keep sufficient ETH balance (auto-alert at 50% threshold)

**Operational Procedures:**
- Daily check-ins on metrics (first 2 weeks)
- Weekly status reports to board
- Monthly cost and performance review
- Continuous improvement based on learnings

**Deliverables:**
- [ ] First production batches posted to mainnet
- [ ] Performance metrics meet targets
- [ ] User feedback collected and documented
- [ ] Operational procedures refined
- [ ] Launch report prepared

---

## 3. Integration Architecture

### 3.1 Aggregation Server → Smart Contract

The aggregation server is responsible for batching image hashes and posting Merkle roots to the blockchain. This integration is the critical path for the entire system.

**Integration Points:**

```python
# High-level integration flow

async def process_batch_workflow(batch_id: UUID):
    """
    Complete workflow from hash accumulation to blockchain posting
    """
    
    # 1. Wait until batch is full (or timeout)
    await wait_for_batch_completion(batch_id)
    
    # 2. Retrieve all hashes for this batch
    hashes = await db.fetch_all(
        "SELECT image_hash FROM batch_images WHERE batch_id = $1 ORDER BY created_at",
        batch_id
    )
    
    # 3. Generate Merkle tree
    merkle_tree = build_merkle_tree([h['image_hash'] for h in hashes])
    merkle_root = merkle_tree.root.hex()
    
    # 4. Store Merkle tree for future verification queries
    await store_merkle_tree(batch_id, merkle_tree)
    
    # 5. Post to blockchain
    try:
        tx_hash = await zksync_post_batch(batch_id, merkle_root, len(hashes))
        logger.info(f"Batch {batch_id} posted successfully: {tx_hash}")
    except Exception as e:
        logger.error(f"Failed to post batch {batch_id}: {e}")
        await mark_batch_failed(batch_id, str(e))
        raise
    
    # 6. Update database with on-chain confirmation
    # (This happens inside zksync_post_batch)
```

**Retry Logic:**

```python
async def zksync_post_batch_with_retry(
    batch_id: UUID,
    merkle_root: str,
    image_count: int,
    max_retries: int = 3
) -> str:
    """
    Post batch with exponential backoff retry
    """
    for attempt in range(max_retries):
        try:
            return await zksync_post_batch(batch_id, merkle_root, image_count)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            
            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
            await asyncio.sleep(wait_time)
```

### 3.2 Verification API → Smart Contract

The verification API allows users to check if an image hash exists in the blockchain registry.

**Verification Flow:**

```python
# verification_api/verify.py

from fastapi import FastAPI, UploadFile, HTTPException
from pydantic import BaseModel
import hashlib

app = FastAPI()

class VerificationResult(BaseModel):
    verified: bool
    image_hash: str
    batch_id: Optional[int] = None
    tx_hash: Optional[str] = None
    timestamp: Optional[datetime] = None
    merkle_proof: Optional[List[str]] = None
    aggregator: Optional[str] = None

@app.post("/verify", response_model=VerificationResult)
async def verify_image(file: UploadFile):
    """
    Verify if an uploaded image exists in the Birthmark registry
    """
    
    # 1. Compute SHA-256 hash of uploaded image
    image_data = await file.read()
    image_hash = hashlib.sha256(image_data).hexdigest()
    
    # 2. Check local database first (performance optimization)
    batch_record = await db.fetch_one(
        """
        SELECT 
            b.batch_id,
            b.on_chain_batch_id,
            b.zksync_tx_hash,
            b.merkle_root,
            b.confirmed_at,
            b.aggregator_address
        FROM batches b
        JOIN batch_images bi ON b.batch_id = bi.batch_id
        WHERE bi.image_hash = $1 AND b.status = 'confirmed'
        """,
        image_hash
    )
    
    if not batch_record:
        return VerificationResult(
            verified=False,
            image_hash=image_hash
        )
    
    # 3. Generate Merkle proof from stored tree
    merkle_proof = await generate_merkle_proof(
        batch_record['batch_id'],
        image_hash
    )
    
    # 4. (Optional) Verify proof against on-chain Merkle root
    # This adds latency but provides cryptographic guarantee
    # Can be optional based on user's trust preferences
    on_chain_batch = await verify_batch_on_chain(batch_record['on_chain_batch_id'])
    
    if on_chain_batch['merkle_root'] != batch_record['merkle_root']:
        raise HTTPException(
            status_code=500,
            detail="Merkle root mismatch between database and blockchain"
        )
    
    # 5. Return verification result
    return VerificationResult(
        verified=True,
        image_hash=image_hash,
        batch_id=batch_record['on_chain_batch_id'],
        tx_hash=batch_record['zksync_tx_hash'],
        timestamp=batch_record['confirmed_at'],
        merkle_proof=merkle_proof,
        aggregator=batch_record['aggregator_address']
    )
```

**Merkle Proof Generation:**

```python
def generate_merkle_proof(batch_id: UUID, target_hash: str) -> List[str]:
    """
    Generate Merkle proof for a specific hash in a batch
    
    Returns:
        List of sibling hashes needed to reconstruct root
    """
    # Load stored Merkle tree from database
    tree = load_merkle_tree(batch_id)
    
    # Find target leaf
    leaf_index = tree.find_leaf_index(target_hash)
    if leaf_index is None:
        raise ValueError(f"Hash {target_hash} not found in batch {batch_id}")
    
    # Generate proof path
    proof = []
    current_index = leaf_index
    current_level = 0
    
    while current_level < tree.depth:
        sibling_index = current_index ^ 1  # XOR to get sibling
        sibling_hash = tree.get_node(current_level, sibling_index)
        proof.append(sibling_hash.hex())
        
        current_index = current_index // 2
        current_level += 1
    
    return proof
```

### 3.3 Governance & Access Control

**Initial Setup (Weeks 13-15):**
- Owner: Foundation-controlled EOA (externally owned account)
- Authorized Aggregators: 1-2 Foundation-operated aggregators

**Future Evolution (Post-Launch):**
- **Phase 2 (Months 6-12):** Transition owner to multisig wallet
  - 3-of-5 or 5-of-7 board member multisig
  - Requires multiple signatures to authorize new aggregators
  - Reduces single-point-of-failure risk
- **Phase 3 (Months 12-18):** Explore DAO governance
  - Token-based voting for aggregator authorization
  - Decentralized governance for protocol upgrades
  - Community-driven decision making

**Aggregator Authorization Process:**
1. Candidate aggregator applies with technical and operational details
2. Board reviews application (technical capability, operational security)
3. Multisig signs transaction to authorize aggregator address
4. Aggregator begins posting batches
5. Ongoing monitoring and potential revocation if issues arise

---

## 4. Cost Model & Economics

### 4.1 Cost Breakdown

**zkSync Era Transaction Costs:**
- **L2 Gas Cost:** ~300,000 gas units per batch submission
- **Gas Price:** Variable, typically 0.05-0.1 gwei on zkSync Era
- **L2 Transaction Cost:** ~$0.15-0.30 per transaction

**Batch Economics:**

| Batch Size | L2 Cost | Per-Image Cost | Batching Delay |
|-----------|---------|----------------|----------------|
| 1,000     | $0.20   | $0.00020       | ~1-2 hours     |
| 2,500     | $0.25   | $0.00010       | ~3-4 hours     |
| 5,000     | $0.30   | $0.00006       | ~6-8 hours     |
| 10,000    | $0.40   | $0.00004       | ~12-16 hours   |

**Recommended Strategy:** 2,500-5,000 images per batch
- Achieves target cost (<$0.0001/image) ✓
- Reasonable batching delay (3-8 hours)
- Manageable Merkle tree depth (~12-13 levels)
- Balances cost efficiency with user experience

### 4.2 Operational Costs (Annual)

**Blockchain Posting:**
- Assumption: 50,000 images/day (conservative for early stage)
- Batches per day: 10-20 (at 2,500-5,000 images/batch)
- Daily cost: $2-6
- **Annual blockchain cost: $730-2,190**

**Infrastructure:**
- Aggregation server hosting: $100-200/month
- Database (PostgreSQL): $50-100/month
- Monitoring and alerting: $20-50/month
- **Annual infrastructure cost: $2,040-4,200**

**Total Annual Operational Cost:** $2,770-6,390

**Cost per Image (All-In):**
- Blockchain: $0.00004-0.00012
- Infrastructure: $0.00011-0.00023
- **Total: $0.00015-0.00035 per image**

This cost model demonstrates the sustainability of the Birthmark Standard as a public good infrastructure. With grant funding covering development and initial operations, the long-term costs are manageable through:
- Additional grant funding
- Consortium membership fees (manufacturers, platforms)
- Voluntary donations from users and supporters

---

## 5. Risk Management

### 5.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Smart contract vulnerability | Low (with audit) | Critical | Third-party security audit, bug bounty program |
| zkSync network issues | Low | High | Maintain backup on Ethereum L1, monitor zkSync status |
| Gas price spike | Medium | Medium | Dynamic gas pricing, batch size adjustment, pause mechanism |
| Aggregator server downtime | Medium | High | Redundant aggregators, monitoring and alerting |
| Database corruption | Low | High | Automated backups, replication, recovery procedures |
| Private key compromise | Low | Critical | Hardware security modules, multisig for owner, key rotation |

### 5.2 Operational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Insufficient funding | Medium | High | Diversify funding sources, sustainable cost model |
| Developer unavailability | Medium | Medium | Documentation, code quality, backup developer relationships |
| Regulatory challenges | Low | Medium | Legal counsel, compliance review, privacy-by-design |
| Manufacturer non-adoption | Medium | High | Strong value proposition, user validation, coalition building |
| Competing standards | High | Medium | Emphasize complementarity, open-source approach, coalition |

### 5.3 Security Incident Response

**Incident Severity Levels:**
- **P0 (Critical):** Smart contract vulnerability, key compromise, system-wide failure
- **P1 (High):** Aggregator server down, transaction failures, data integrity issues
- **P2 (Medium):** Performance degradation, partial service disruption
- **P3 (Low):** Minor bugs, optimization opportunities

**Response Procedures:**
1. **Detection:** Monitoring systems alert on anomaly
2. **Assessment:** Determine severity and impact
3. **Containment:** Pause affected systems if necessary
4. **Resolution:** Fix root cause, deploy patch if needed
5. **Recovery:** Restore normal operations, validate fix
6. **Post-Mortem:** Document incident, improve processes

**Emergency Contacts:**
- Blockchain Developer: [Contact info]
- Executive Director: Samuel C. Ryan, 503-941-0418
- Security Auditor: [Firm contact if retainer]
- zkSync Support: support@zksync.io

---

## 6. Success Metrics

### 6.1 Technical Metrics

**Smart Contract Performance:**
- [ ] Gas cost per batch <500,000 gas
- [ ] Cost per image <$0.0001
- [ ] Transaction success rate >99.9%
- [ ] Average confirmation time <30 seconds

**System Performance:**
- [ ] Verification query latency <5 seconds
- [ ] Aggregation server uptime >99.9%
- [ ] Database query performance <100ms
- [ ] End-to-end latency (submit → verify) <10 minutes

**Security:**
- [ ] Pass third-party security audit with no critical findings
- [ ] Zero security incidents in production
- [ ] Zero unauthorized smart contract interactions
- [ ] All transactions properly authorized

### 6.2 Operational Metrics

**Deployment:**
- [ ] Testnet deployment complete by Week 6
- [ ] Security audit complete by Week 12
- [ ] Mainnet deployment complete by Week 13
- [ ] Production launch by Week 15

**Adoption:**
- [ ] 10-20 early adopters by Week 15
- [ ] 1,000+ images verified by Week 15
- [ ] 50+ batches posted to mainnet by Week 15
- [ ] Zero critical incidents during rollout

**Economics:**
- [ ] Actual costs match projections (±20%)
- [ ] Sustainable operational cost model validated
- [ ] Funding secured for next phase

---

## 7. Documentation Requirements

### 7.1 Technical Documentation

- [ ] **Smart Contract Documentation**
  - Comprehensive NatSpec comments
  - Architecture overview
  - Function specifications
  - Event descriptions
  - Access control model
- [ ] **Integration Documentation**
  - Aggregation server integration guide
  - API specifications (REST endpoints)
  - Authentication and authorization
  - Error handling and retry logic
  - Code examples in Python
- [ ] **Deployment Documentation**
  - Testnet deployment procedures
  - Mainnet deployment procedures
  - Configuration management
  - Environment variables
  - Network endpoints
- [ ] **Operational Documentation**
  - Monitoring and alerting setup
  - Incident response procedures
  - Backup and recovery procedures
  - Key management and security
  - Routine maintenance tasks

### 7.2 User Documentation

- [ ] **Verification API Guide**
  - How to verify an image
  - API endpoint documentation
  - Request/response formats
  - Error codes and handling
  - Rate limits and quotas
- [ ] **Merkle Proof Verification**
  - How to validate Merkle proofs
  - Cryptographic explanation
  - Code examples
  - Trust model explanation

### 7.3 Governance Documentation

- [ ] **Access Control Policies**
  - Aggregator authorization process
  - Owner role and responsibilities
  - Multisig setup (future)
  - Emergency procedures
- [ ] **Governance Transition Plan**
  - Current state (Foundation-controlled)
  - Phase 2 (Multisig board control)
  - Phase 3 (DAO governance exploration)
  - Timeline and milestones

---

## 8. Resource Requirements

### 8.1 Personnel

**Blockchain Developer (Part-Time, 15 Weeks)**
- Hours: 12-15 hours/week × 15 weeks = 180-225 hours
- Rate: $125/hour
- Total: $22,500-28,125

**Time Distribution:**
- Weeks 1-6: Heavy development (15-20 hrs/week) = 90-120 hours
- Weeks 7-9: Security hardening (12-15 hrs/week) = 36-45 hours
- Weeks 10-12: Audit support (10-12 hrs/week) = 30-36 hours
- Weeks 13-15: Deployment (12-15 hrs/week) = 36-45 hours

**Required Skills:**
- Solidity smart contract development (EVM-compatible)
- zkSync Era SDK experience (or willingness to learn quickly)
- Backend development (Python for aggregation server integration)
- Cryptographic primitives (Merkle trees, hash functions, digital signatures)
- Testing frameworks (Hardhat, Chai)
- Gas optimization techniques
- Security best practices

### 8.2 Professional Services

**Security Audit:** $20,000
- Comprehensive smart contract security review
- Cryptographic protocol validation
- Access control assessment
- Gas optimization review
- Final report with recommendations

**Recommended Audit Firms:**
1. OpenZeppelin - $18,000-25,000
2. Consensys Diligence - $20,000-30,000
3. Trail of Bits - $25,000-35,000

### 8.3 Infrastructure Costs

**Development (Weeks 1-12):**
- Testnet gas: Negligible (free testnet ETH from faucets)
- Development tools: Free (Hardhat, VSCode, Git)
- Local testing: Free (era-test-node)

**Mainnet Deployment (Weeks 13-15):**
- Contract deployment: ~$50-100
- Initial aggregator wallet funding: $1,000 (operational buffer)
- First 10 production batches: ~$2-3 per batch = $20-30

**Total Infrastructure (15 weeks):** ~$1,070-1,130

### 8.4 Total Budget Summary

| Item | Cost |
|------|------|
| Blockchain Developer (225 hrs) | $28,125 |
| Security Audit | $20,000 |
| Infrastructure & Deployment | $1,130 |
| **Total** | **$49,255** |

**Contingency (10%):** $4,926  
**Total with Contingency:** $54,181

**Funding Source:** Mozilla Foundation grant (Personnel & Professional Services budget)

---

## 9. Timeline Summary

| Phase | Weeks | Key Deliverables | Risk Level |
|-------|-------|------------------|------------|
| **Phase 1: Development** | 1-3 | Smart contract, tests, local validation | Low |
| **Phase 2: Testnet** | 4-6 | Testnet deployment, integration, performance validation | Low-Medium |
| **Phase 3: Security** | 7-9 | Security hardening, gas optimization, audit prep | Medium |
| **Phase 4: Audit** | 10-12 | Security audit, remediation, final approval | Medium |
| **Phase 5: Mainnet** | 13-15 | Mainnet deployment, production launch, monitoring | Medium-High |

**Critical Path:**
1. Contract development (Weeks 1-3)
2. Testnet validation (Weeks 4-6)
3. Security audit (Weeks 10-12)
4. Mainnet deployment (Weeks 13-15)

**Buffer:** 2 weeks built into schedule for unexpected delays (audit scheduling, remediation complexity)

---

## 10. Next Steps

### Immediate Actions (Week 0)

**Executive Director:**
- [ ] Finalize blockchain developer recruitment
- [ ] Secure audit firm engagement
- [ ] Prepare development environment specifications
- [ ] Review and approve this plan with board

**Blockchain Developer:**
- [ ] Set up development environment
- [ ] Review Birthmark Standard architecture documents
- [ ] Familiarize with zkSync Era documentation
- [ ] Review existing aggregation server codebase

### Week 1 Kickoff

**Day 1:**
- Kickoff meeting with Executive Director and Blockchain Developer
- Review project goals, timeline, and success criteria
- Set up communication channels (Slack, GitHub, weekly check-ins)
- Assign GitHub repository access and project management tools

**Day 2-5:**
- Complete development environment setup
- Initialize Hardhat project with zkSync plugins
- Deploy test contract to local zkSync node
- Begin smart contract development

**Weekly Check-ins:**
- Every Monday: Progress review, blockers discussion
- Every Friday: Week in review, next week planning
- Ad-hoc: As needed for technical discussions

---

## Appendix A: zkSync Era Resources

**Official Documentation:**
- zkSync Era Docs: https://era.zksync.io/docs/
- Hardhat Plugin: https://era.zksync.io/docs/tools/hardhat/
- SDK Documentation: https://sdk.zksync.io/

**Developer Tools:**
- Block Explorer: https://explorer.zksync.io
- Bridge: https://portal.zksync.io/bridge
- Faucet: https://portal.zksync.io/faucet
- RPC Endpoints: https://era.zksync.io/docs/api/api.html

**Community:**
- Discord: https://discord.gg/zksync
- GitHub: https://github.com/matter-labs
- Forum: https://community.zksync.io

---

## Appendix B: Contract ABI Reference

```json
{
  "abi": [
    {
      "inputs": [],
      "stateMutability": "nonpayable",
      "type": "constructor"
    },
    {
      "anonymous": false,
      "inputs": [
        {"indexed": true, "internalType": "address", "name": "aggregator", "type": "address"}
      ],
      "name": "AggregatorAuthorized",
      "type": "event"
    },
    {
      "anonymous": false,
      "inputs": [
        {"indexed": true, "internalType": "address", "name": "aggregator", "type": "address"}
      ],
      "name": "AggregatorRevoked",
      "type": "event"
    },
    {
      "anonymous": false,
      "inputs": [
        {"indexed": true, "internalType": "uint256", "name": "batchId", "type": "uint256"},
        {"indexed": false, "internalType": "bytes32", "name": "merkleRoot", "type": "bytes32"},
        {"indexed": false, "internalType": "uint32", "name": "imageCount", "type": "uint32"},
        {"indexed": true, "internalType": "address", "name": "aggregator", "type": "address"}
      ],
      "name": "BatchSubmitted",
      "type": "event"
    },
    {
      "inputs": [{"internalType": "address", "name": "aggregator", "type": "address"}],
      "name": "authorizeAggregator",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [{"internalType": "uint256", "name": "batchId", "type": "uint256"}],
      "name": "getBatch",
      "outputs": [
        {
          "components": [
            {"internalType": "bytes32", "name": "merkleRoot", "type": "bytes32"},
            {"internalType": "uint64", "name": "timestamp", "type": "uint64"},
            {"internalType": "address", "name": "aggregator", "type": "address"},
            {"internalType": "uint32", "name": "imageCount", "type": "uint32"}
          ],
          "internalType": "struct BirthmarkRegistry.Batch",
          "name": "",
          "type": "tuple"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [{"internalType": "address", "name": "aggregator", "type": "address"}],
      "name": "revokeAggregator",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [
        {"internalType": "bytes32", "name": "_merkleRoot", "type": "bytes32"},
        {"internalType": "uint32", "name": "_imageCount", "type": "uint32"}
      ],
      "name": "submitBatch",
      "outputs": [{"internalType": "uint256", "name": "batchId", "type": "uint256"}],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [{"internalType": "address", "name": "newOwner", "type": "address"}],
      "name": "transferOwnership",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    }
  ]
}
```

---

## Appendix C: Sample Deployment Script

```typescript
// scripts/deploy.ts

import { Wallet } from "zksync-web3";
import { HardhatRuntimeEnvironment } from "hardhat/types";
import { Deployer } from "@matterlabs/hardhat-zksync-deploy";

export default async function (hre: HardhatRuntimeEnvironment) {
  console.log("Deploying BirthmarkRegistry to zkSync Era...");

  // Load deployer wallet
  const wallet = new Wallet(process.env.PRIVATE_KEY!);
  const deployer = new Deployer(hre, wallet);

  // Load contract artifact
  const artifact = await deployer.loadArtifact("BirthmarkRegistry");

  // Deploy contract
  const contract = await deployer.deploy(artifact, []);

  // Wait for deployment
  await contract.deployed();

  console.log(`✅ BirthmarkRegistry deployed to: ${contract.address}`);
  console.log(`Transaction hash: ${contract.deployTransaction.hash}`);
  
  // Verify contract on explorer (optional)
  console.log("\nVerifying contract on zkSync Era Block Explorer...");
  console.log(`Run: npx hardhat verify --network zkSyncMainnet ${contract.address}`);
  
  return contract.address;
}
```

---

## Appendix D: Glossary

**Terms:**
- **Aggregator:** Server that batches image hashes and posts Merkle roots to blockchain
- **Batch:** Collection of 1,000-5,000 image hashes represented by a single Merkle root
- **Merkle Root:** Single hash representing an entire Merkle tree, stored on-chain
- **Merkle Proof:** Set of hashes needed to verify a specific image hash is in a batch
- **zkSync Era:** Ethereum Layer 2 scaling solution using zero-knowledge proofs
- **EVM:** Ethereum Virtual Machine, the execution environment for smart contracts
- **Gas:** Computational cost of executing smart contract functions
- **Testnet:** Test blockchain network for development (Sepolia)
- **Mainnet:** Production blockchain network with real economic value

---

**Document Version Control:**
- Version 1.0: Initial release (November 11, 2025)
- Next Review: After Week 6 (testnet validation complete)
- Owner: Samuel C. Ryan, Executive Director
- Contributors: Blockchain Developer (TBD)

---

**Approval Signatures:**

Executive Director: _________________________ Date: _________

Board Chair: _________________________ Date: _________

Blockchain Developer: _________________________ Date: _________
