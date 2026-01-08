# Birthmark Media Registry - Substrate Node

## Overview

The Birthmark Media Registry is a Substrate-based standalone blockchain operated by journalism organizations to provide permanent, tamper-evident authentication records for images. This replaces the original custom Python blockchain with a production-ready Substrate implementation.

## Why Substrate?

We migrated from the custom Python blockchain to Substrate for several key benefits:

1. **Forkless Upgrades** - Runtime upgrades via WASM without validator coordination or downtime
2. **Battle-Tested Consensus** - GRANDPA (finality) + AURA (block production) used by Polkadot ecosystem
3. **Modular Architecture** - Pallet system enables clean separation of concerns
4. **Production-Ready** - Used by dozens of production blockchains with billions in value
5. **Rust Safety** - Memory safety, thread safety, and strong typing prevent common vulnerabilities

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    BIRTHMARK SUBSTRATE NODE                     │
│                                                                 │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐ │
│  │ Birthmark      │  │ Democracy      │  │ Council          │ │
│  │ Pallet         │  │ (Governance)   │  │ (Coalition)      │ │
│  │                │  │                │  │                  │ │
│  │ - ImageRecords │  │ - Proposals    │  │ - 50 journalism  │ │
│  │ - Provenance   │  │ - Voting       │  │   org members    │ │
│  │ - Query API    │  │ - Execution    │  │ - Supermajority  │ │
│  └────────────────┘  └────────────────┘  └──────────────────┘ │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    CONSENSUS LAYER                         │ │
│  │  • GRANDPA (finality) - BFT with deterministic finality    │ │
│  │  • AURA (block production) - PoA with journalism validators│ │
│  │  • 6 second block time, <10 second finality               │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                        RPC API                             │ │
│  │  • Standard Substrate RPC (system, chain, state)          │ │
│  │  • Transaction submission                                  │ │
│  │  • Query image records by hash (<500ms)                   │ │
│  │  • WebSocket subscriptions for real-time updates          │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- **Rust 1.70+** - `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- **Build tools** - `sudo apt install build-essential git clang libclang-dev pkg-config libssl-dev protobuf-compiler`
- **4GB RAM minimum**, 8GB recommended
- **10GB disk space** for build artifacts

### Build from Source

```bash
cd packages/registry

# Build in release mode (first build takes 20-40 minutes)
cargo build --release

# Binary will be at: ./target/release/birthmark-node
```

### Run Development Node

```bash
# Run with temporary database (data discarded on exit)
./target/release/birthmark-node --dev --tmp

# Or with persistent data
./target/release/birthmark-node --dev --base-path /tmp/birthmark-dev
```

The node will start producing blocks immediately and expose RPC endpoints:

- HTTP RPC: `http://localhost:9944`
- WebSocket: `ws://localhost:9944`

### Run Validator Node (Production)

```bash
# Generate session keys
./target/release/birthmark-node key generate --scheme Sr25519

# Start validator
./target/release/birthmark-node \
  --base-path /var/lib/birthmark \
  --chain production \
  --validator \
  --name "NPPA-Validator-1" \
  --rpc-port 9944 \
  --port 30333
```

## Pallet: Birthmark

The custom Birthmark pallet (`pallets/birthmark/`) provides core functionality for image authentication.

### Storage

```rust
// Map: image_hash -> ImageRecord
ImageRecords<T: Config> = StorageMap<
    _,
    Blake2_128Concat,
    BoundedVec<u8, MaxImageHashLength>,  // 64 hex chars
    ImageRecord<T>,
    OptionQuery,
>;

pub struct ImageRecord<T: Config> {
    pub image_hash: BoundedVec<u8, 64>,
    pub submission_type: SubmissionType,  // Camera | Software
    pub modification_level: u8,           // 0=raw, 1=validated, 2=modified
    pub parent_image_hash: Option<BoundedVec<u8, 64>>,
    pub authority_id: BoundedVec<u8, 100>,
    pub timestamp: T::Moment,
    pub block_number: BlockNumberFor<T>,
}
```

### Extrinsics

**Submit Single Record:**

```rust
Birthmark::submit_image_record(
    origin,
    image_hash: Vec<u8>,           // 64 hex chars
    submission_type: SubmissionType,
    modification_level: u8,
    parent_image_hash: Option<Vec<u8>>,
    authority_id: Vec<u8>,
)
```

**Submit Batch (more gas-efficient):**

```rust
Birthmark::submit_image_batch(
    origin,
    records: Vec<(Vec<u8>, SubmissionType, u8, Option<Vec<u8>>, Vec<u8>)>,  // Max 100
)
```

### Query Records

```bash
# Via RPC (state query)
curl -H "Content-Type: application/json" \
     -d '{"id":1, "jsonrpc":"2.0", "method":"state_getStorage", "params":["<storage_key>"]}' \
     http://localhost:9944
```

## Governance

The Birthmark blockchain uses Substrate's democracy and collective pallets for on-chain governance.

### Council (Coalition)

- **Members:** Up to 50 journalism organizations
- **Voting:** Simple majority for proposals
- **Responsibilities:**
  - Approve external democracy proposals
  - Emergency actions (fast-track proposals)
  - Treasury management

### Democracy (Public Referenda)

- **Launch Period:** 7 days (time to gather support)
- **Voting Period:** 7 days
- **Enactment Period:** 1 day (delay before execution)
- **Minimum Deposit:** 100 tokens (spam prevention)

### Proposal Workflow

1. **Submit Proposal:**
   ```bash
   # Via polkadot-js UI or CLI
   democracy.propose(proposal_hash, value)
   ```

2. **Council Review:**
   - Council can fast-track important proposals
   - Can veto proposals if needed

3. **Public Vote:**
   - Token holders vote (or council members in PoA)
   - Supermajority (67%) required for approval

4. **Automatic Execution:**
   - After enactment period, proposal executes automatically
   - No manual intervention needed

## Forkless Runtime Upgrades

**Major operational advantage of Substrate:**

### Process

1. **Build New Runtime:**
   ```bash
   cargo build --release -p birthmark-runtime
   # WASM at: target/release/wbuild/birthmark-runtime/birthmark_runtime.wasm
   ```

2. **Create Upgrade Proposal:**
   ```bash
   # Submit via democracy pallet
   democracy.notePreimage(runtime_wasm)
   democracy.propose(preimage_hash, deposit)
   ```

3. **Coalition Votes:**
   - Council reviews proposal
   - 7-day voting period
   - Supermajority approval required

4. **Automatic Upgrade:**
   - Upon approval, all validators download new WASM
   - **Zero downtime** - no coordinated restarts
   - Next block uses new runtime logic

### Example Upgrade

```javascript
// Via polkadot-js apps (Governance > Democracy > Submit preimage)
const runtime = fs.readFileSync('birthmark_runtime.wasm');
await api.tx.democracy.notePreimage(runtime).signAndSend(alice);
const preimageHash = blake2AsHex(runtime);
await api.tx.democracy.propose(preimageHash, 1000).signAndSend(alice);
```

## Integration with Submission Server

The Submission Server (`packages/blockchain/`) integrates with Substrate via RPC.

### Python Integration Example

```python
from substrateinterface import SubstrateInterface, Keypair

# Connect to node
substrate = SubstrateInterface(
    url="ws://127.0.0.1:9944",
    ss58_format=42,
    type_registry_preset='substrate-node-template'
)

# Load submission server keypair (authorized to submit records)
keypair = Keypair.create_from_uri('//Alice')

# Submit image record
call = substrate.compose_call(
    call_module='Birthmark',
    call_function='submit_image_record',
    call_params={
        'image_hash': 'a1b2c3d4...',  # 64 hex chars
        'submission_type': 'Camera',
        'modification_level': 0,
        'parent_image_hash': None,
        'authority_id': 'CANON_EOS_R5',
    }
)

extrinsic = substrate.create_signed_extrinsic(call=call, keypair=keypair)
receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

if receipt.is_success:
    print(f"Record submitted in block {receipt.block_hash}")
else:
    print(f"Submission failed: {receipt.error_message}")
```

### Query Image Record

```python
# Query by hash
result = substrate.query(
    module='Birthmark',
    storage_function='ImageRecords',
    params=['a1b2c3d4...']  # image hash
)

if result.value:
    record = result.value
    print(f"Image verified!")
    print(f"Authority: {record['authority_id']}")
    print(f"Modification level: {record['modification_level']}")
    print(f"Block: {record['block_number']}")
else:
    print("Image not found in registry")
```

## Verifier Integration

Update `packages/verifier/` to query Substrate instead of custom blockchain.

```javascript
// In verifier web app
const { ApiPromise, WsProvider } = require('@polkadot/api');

const provider = new WsProvider('wss://registry.birthmarkstandard.org:9944');
const api = await ApiPromise.create({ provider });

// Query image hash
const hash = '0x' + imageHashHex;
const record = await api.query.birthmark.imageRecords(hash);

if (record.isSome) {
    const data = record.unwrap();
    console.log('Verified!', {
        authority: data.authorityId.toHuman(),
        modificationLevel: data.modificationLevel.toNumber(),
        timestamp: data.timestamp.toNumber(),
    });
} else {
    console.log('Not found');
}
```

## Node Requirements

### Development

- 2 CPU cores
- 4GB RAM
- 20GB disk (build artifacts + blockchain data)

### Production Validator

- 4 CPU cores (8 recommended)
- 8GB RAM (16GB for archive node)
- 500GB SSD (fast disk essential for production)
- 100 Mbps network (dedicated IP preferred)
- Ubuntu 22.04 LTS or Debian 11

## Deployment

### Docker (Recommended for Production)

```dockerfile
# Create Dockerfile (see packages/registry/Dockerfile)
FROM ubuntu:22.04

# Install built binary
COPY target/release/birthmark-node /usr/local/bin/

# Expose ports
EXPOSE 9944 9933 30333

# Run node
ENTRYPOINT ["birthmark-node"]
CMD ["--chain", "production", "--validator"]
```

```bash
# Build and run
docker build -t birthmark-node .
docker run -p 9944:9944 -p 30333:30333 \
    -v /var/lib/birthmark:/data \
    birthmark-node \
    --base-path /data \
    --chain production \
    --validator \
    --name "MyValidator"
```

### Systemd Service

```ini
# /etc/systemd/system/birthmark-node.service
[Unit]
Description=Birthmark Validator Node
After=network.target

[Service]
Type=simple
User=birthmark
ExecStart=/usr/local/bin/birthmark-node \
    --base-path /var/lib/birthmark \
    --chain production \
    --validator \
    --name "NPPA-Validator" \
    --rpc-port 9944 \
    --port 30333
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable birthmark-node
sudo systemctl start birthmark-node
sudo journalctl -u birthmark-node -f
```

## Testing

### Unit Tests

```bash
# Test Birthmark pallet
cargo test -p pallet-birthmark

# Test runtime
cargo test -p birthmark-runtime

# All tests
cargo test
```

### Integration Tests

```bash
# Start dev node in background
./target/release/birthmark-node --dev --tmp &
NODE_PID=$!

# Run integration tests (from packages/blockchain/)
python tests/integration/test_substrate_integration.py

# Cleanup
kill $NODE_PID
```

## Monitoring

### Prometheus Metrics

The node exposes Prometheus metrics on port 9615:

```bash
curl http://localhost:9615/metrics
```

Key metrics:
- `substrate_block_height` - Current block number
- `substrate_finalized_height` - Latest finalized block
- `substrate_peers` - Connected peer count
- `substrate_transaction_pool_bytes` - Transaction pool size

### Telemetry

Connect to public telemetry (optional):

```bash
./target/release/birthmark-node \
    --telemetry-url 'wss://telemetry.polkadot.io/submit/ 0' \
    --validator
```

View at: https://telemetry.polkadot.io

## Troubleshooting

### Build Fails

```bash
# Update Rust
rustup update stable
rustup default stable

# Clean build
cargo clean
cargo build --release
```

### Node Won't Start

```bash
# Check logs
RUST_LOG=info ./target/release/birthmark-node --dev

# Purge chain data (development only!)
./target/release/birthmark-node purge-chain --dev
```

### Slow Block Production

- Check system resources (CPU, RAM, disk I/O)
- Ensure at least 2/3 validators are online (for GRANDPA finality)
- Check network connectivity between validators

### Can't Submit Transactions

- Verify account has sufficient balance for gas fees
- Check transaction pool isn't full: `api.rpc.author.pendingExtrinsics()`
- Ensure node is synced: `api.rpc.system.health()`

## Comparison: Custom vs Substrate

| Aspect | Custom Python Blockchain | Substrate |
|--------|--------------------------|-----------|
| **Runtime Upgrades** | Manual restart required | Forkless (WASM upload) |
| **Consensus** | Custom single-node | GRANDPA+AURA (battle-tested) |
| **Finality** | Immediate (single node) | Deterministic (<10s, multi-node) |
| **Governance** | Manual configuration | On-chain democracy + council |
| **Development Complexity** | High (custom implementation) | Medium (using framework) |
| **Ecosystem** | Isolated | Polkadot ecosystem (tools, wallets) |
| **Security Audits** | None | Framework used in $100B+ networks |
| **Scaling** | Manual coordination | Built-in P2P and sync |

## Migration Guide

See `MIGRATION.md` for detailed guide on migrating data from the custom Python blockchain to Substrate.

High-level steps:

1. Export image records from PostgreSQL
2. Generate genesis config with existing records
3. Launch Substrate chain with seeded data
4. Update submission server to use Substrate RPC
5. Update verifier to query Substrate
6. Run both systems in parallel during transition
7. Cut over when Substrate validated

## Development

### Add New Feature to Pallet

1. Edit `pallets/birthmark/src/lib.rs`
2. Add storage, extrinsic, or event
3. Update tests in `pallets/birthmark/src/tests.rs`
4. Compile: `cargo build --release`
5. Test: `cargo test -p pallet-birthmark`
6. Deploy via forkless upgrade

### Add New Pallet

1. Create `pallets/new-pallet/` directory
2. Add to `Cargo.toml` workspace members
3. Configure in `runtime/src/lib.rs`
4. Add to `construct_runtime!` macro
5. Rebuild and upgrade runtime

## Resources

- **Substrate Documentation:** https://docs.substrate.io/
- **Polkadot Wiki:** https://wiki.polkadot.network/
- **Substrate Stack Exchange:** https://substrate.stackexchange.com/
- **Birthmark GitHub:** https://github.com/Birthmark-Standard/Birthmark
- **Support:** samryan.pdx@proton.me

## License

AGPL-3.0-or-later - See LICENSE file in this directory.

This component is part of the core trust infrastructure (Birthmark Media Registry)
and must remain transparent. Any modifications must be made publicly available.

---

**Birthmark Standard:** Proving images are real, not generated.

**Last Updated:** January 2, 2026
**Version:** 0.1.0 (Phase 1 - Substrate Migration)
