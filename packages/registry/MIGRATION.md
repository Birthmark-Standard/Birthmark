# Migration Guide: Custom Python Blockchain → Substrate

This guide describes how to migrate from the custom Python blockchain (`packages/blockchain/`) to the Substrate implementation.

## Overview

The migration involves:

1. **Phase 1:** Set up Substrate node alongside existing system
2. **Phase 2:** Export data from PostgreSQL
3. **Phase 3:** Initialize Substrate chain with existing records
4. **Phase 4:** Update integrations (submission server, verifier)
5. **Phase 5:** Run parallel for validation period
6. **Phase 6:** Cut over to Substrate as primary

## Phase 1: Setup Substrate Node

### Build Substrate Node

```bash
cd packages/registry
cargo build --release
```

This creates `./target/release/birthmark-node`.

### Run Development Node (Testing)

```bash
# Run with temporary data
./target/release/birthmark-node --dev --tmp
```

Verify it's working:
- Blocks are being produced
- RPC accessible at `ws://localhost:9944`

### Test Python Integration

```bash
cd integration/python
pip install -r requirements.txt
python birthmark_substrate.py
```

Should successfully submit and query a test record.

## Phase 2: Export Existing Data

### Export Image Records from PostgreSQL

```sql
-- Connect to custom blockchain database
\c birthmark_chain

-- Export all image hashes
COPY (
    SELECT
        image_hash,
        CASE WHEN submission_type = 'camera' THEN 'Camera' ELSE 'Software' END as submission_type,
        modification_level,
        parent_image_hash,
        aggregator_id as authority_id,
        timestamp,
        block_height
    FROM image_hashes
    ORDER BY block_height ASC, created_at ASC
) TO '/tmp/birthmark_export.csv' CSV HEADER;
```

### Verify Export

```bash
wc -l /tmp/birthmark_export.csv  # Count records
head /tmp/birthmark_export.csv   # Inspect format
```

## Phase 3: Initialize Substrate with Existing Data

### Option A: Genesis Block (Recommended for <10K records)

Create a custom genesis configuration that includes all existing records.

```bash
# Generate genesis spec
./target/release/birthmark-node build-spec --chain production > genesis.json
```

Edit `genesis.json` and add existing records to Birthmark pallet storage:

```json
{
  "genesis": {
    "birthmark": {
      "imageRecords": [
        ["a1b2c3d4...", {
          "imageHash": "0xa1b2c3d4...",
          "submissionType": "Camera",
          "modificationLevel": 0,
          "parentImageHash": null,
          "authorityId": "CANON_EOS_R5",
          "timestamp": 1699564800,
          "blockNumber": 1
        }],
        // ... more records
      ]
    }
  }
}
```

This approach is ideal for small datasets but impractical for >10K records due to genesis size limits.

### Option B: Batch Submission (Recommended for >10K records)

Submit existing records via batch extrinsics after chain is live.

```python
import csv
from birthmark_substrate import BirthmarkSubstrate

client = BirthmarkSubstrate("ws://localhost:9944", "//GenesisAccount")
client.connect()

# Read export
with open('/tmp/birthmark_export.csv', 'r') as f:
    reader = csv.DictReader(f)
    records = list(reader)

# Submit in batches of 100
batch = []
for i, record in enumerate(records):
    batch.append({
        'image_hash': record['image_hash'],
        'submission_type': record['submission_type'],
        'modification_level': int(record['modification_level']),
        'parent_image_hash': record['parent_image_hash'] or None,
        'authority_id': record['authority_id'],
    })

    if len(batch) == 100 or i == len(records) - 1:
        result = client.submit_image_batch(batch)
        print(f"Submitted batch {i//100 + 1}: {result}")
        batch = []

print(f"Migration complete! Total records: {client.get_total_records()}")
```

**Pros:**
- Handles unlimited records
- Preserves block numbers and timestamps
- Can be done incrementally

**Cons:**
- Requires gas fees (ensure genesis account is funded)
- Takes time for large datasets (~100 records/second)

## Phase 4: Update Integrations

### Update Submission Server

Replace `packages/blockchain/src/blockchain.py` with Substrate client:

```python
# OLD (custom blockchain)
from src.blockchain import BirthmarkBlockchain
blockchain = BirthmarkBlockchain("http://localhost:8545")

# NEW (Substrate)
from birthmark_substrate import BirthmarkSubstrate
blockchain = BirthmarkSubstrate("ws://localhost:9944", "//SubmissionServer")
```

Update submission logic:

```python
# Submit validated image
result = blockchain.submit_image_record(
    image_hash=image_hash,
    submission_type='Camera',
    modification_level=modification_level,
    authority_id=authority_id,
    parent_image_hash=parent_hash
)

if result['success']:
    # Record submitted to blockchain
    update_submission_status(submission_id, 'blockchain_confirmed')
    store_block_hash(submission_id, result['block_hash'])
else:
    log_error(f"Blockchain submission failed: {result['error']}")
```

### Update Verifier

Replace query logic in `packages/verifier/src/api.py`:

```python
# OLD (custom blockchain)
result = requests.get(f"http://localhost:8545/api/v1/verify/{image_hash}")

# NEW (Substrate)
from birthmark_substrate import BirthmarkSubstrate
client = BirthmarkSubstrate("ws://registry.birthmarkstandard.org:9944")
client.connect()
record = client.get_image_record(image_hash)

if record:
    return {
        'verified': True,
        'modification_level': record['modification_level'],
        'authority': record['authority_id'],
        'timestamp': record['timestamp'],
    }
else:
    return {'verified': False}
```

## Phase 5: Parallel Operation

Run both blockchains simultaneously for validation period (recommended: 2-4 weeks).

### Dual-Write Configuration

Submit to both chains:

```python
# Submit to custom blockchain (primary)
custom_result = custom_blockchain.submit(record)

# Also submit to Substrate (shadow)
substrate_result = substrate_blockchain.submit_image_record(record)

# Log any discrepancies
if custom_result.success != substrate_result['success']:
    log_warning("Blockchain mismatch", custom_result, substrate_result)
```

### Dual-Read Verification

Query both chains and compare:

```python
custom_record = custom_blockchain.verify(image_hash)
substrate_record = substrate_blockchain.get_image_record(image_hash)

# Verify consistency
assert custom_record['verified'] == (substrate_record is not None)
assert custom_record['modification_level'] == substrate_record['modification_level']
```

### Monitoring

Track metrics during parallel operation:

- **Submission latency:** Compare response times (Substrate should be <200ms)
- **Query latency:** Compare lookup times (both should be <100ms)
- **Discrepancies:** Log any mismatches for investigation
- **Gas usage:** Monitor Substrate transaction fees

## Phase 6: Cutover

### Pre-Cutover Checklist

- [ ] All existing records migrated to Substrate
- [ ] Parallel operation running smoothly for 2+ weeks
- [ ] Zero discrepancies between chains in past week
- [ ] Submission server integration tested
- [ ] Verifier integration tested
- [ ] Validator nodes deployed (3+ for production)
- [ ] Monitoring and alerting configured
- [ ] Backup plan documented (rollback procedure)
- [ ] Stakeholders notified of cutover date

### Cutover Procedure

**1. Freeze Custom Blockchain (T-0)**

```sql
-- Mark custom blockchain read-only
UPDATE submissions SET validation_status = 'migrated';
```

Stop accepting new submissions to custom chain.

**2. Final Sync (T+5 min)**

Verify last records migrated:

```python
# Get last custom blockchain record
last_custom = custom_blockchain.get_latest_record()

# Verify exists in Substrate
substrate_record = substrate_blockchain.get_image_record(last_custom['hash'])
assert substrate_record is not None
```

**3. Switch Submission Server (T+10 min)**

Update environment variable:

```bash
# OLD
BLOCKCHAIN_URL=http://localhost:8545

# NEW
BLOCKCHAIN_URL=ws://localhost:9944
```

Restart submission server:

```bash
systemctl restart birthmark-submission-server
```

**4. Switch Verifier (T+15 min)**

Deploy updated verifier pointing to Substrate:

```bash
cd packages/verifier
# Update config to point to Substrate
vim src/config.py  # Change blockchain_url
systemctl restart birthmark-verifier
```

**5. Verification (T+20 min)**

Test end-to-end flow:

```bash
# Submit test image via camera
python packages/camera-pi/src/main.py --test

# Verify appears in Substrate
python -c "
from birthmark_substrate import BirthmarkSubstrate
client = BirthmarkSubstrate('ws://localhost:9944')
client.connect()
print(f'Total records: {client.get_total_records()}')
"
```

**6. Decommission Custom Blockchain (T+1 week)**

After 1 week of successful operation on Substrate:

```bash
# Archive custom blockchain database
pg_dump birthmark_chain > custom_blockchain_archive.sql

# Stop custom blockchain service
systemctl stop birthmark-custom-blockchain

# Remove from startup
systemctl disable birthmark-custom-blockchain
```

Keep archive for 90 days for potential rollback.

## Rollback Procedure

If issues arise during cutover:

**1. Switch Back Immediately**

```bash
# Submission server
BLOCKCHAIN_URL=http://localhost:8545
systemctl restart birthmark-submission-server

# Verifier
systemctl restart birthmark-verifier
```

**2. Resume Custom Blockchain**

```bash
systemctl start birthmark-custom-blockchain
```

**3. Sync Missing Records**

Any records submitted to Substrate during cutover period should be synced back:

```python
# Get records submitted to Substrate during cutover
substrate_records = get_substrate_records(start_time=cutover_time)

# Submit to custom blockchain
for record in substrate_records:
    custom_blockchain.submit(record)
```

**4. Post-Mortem**

Investigate root cause before attempting cutover again:
- Review logs
- Identify failure point
- Fix issue in Substrate or integration
- Plan new cutover date

## Data Validation

### Verify Migration Completeness

```python
def validate_migration():
    """Verify all custom blockchain records exist in Substrate."""

    # Connect to both
    custom = CustomBlockchain()
    substrate = BirthmarkSubstrate("ws://localhost:9944")
    substrate.connect()

    # Get all custom hashes
    custom_hashes = custom.get_all_hashes()  # From PostgreSQL

    # Check each exists in Substrate
    missing = []
    for hash in custom_hashes:
        if not substrate.image_exists(hash):
            missing.append(hash)

    if missing:
        print(f"ERROR: {len(missing)} records missing from Substrate:")
        for h in missing[:10]:  # Show first 10
            print(f"  - {h}")
        return False
    else:
        print(f"SUCCESS: All {len(custom_hashes)} records migrated")
        return True

validate_migration()
```

### Compare Statistics

```python
# Total records
custom_total = custom_blockchain.get_total_records()
substrate_total = substrate_blockchain.get_total_records()
assert custom_total == substrate_total, "Record count mismatch"

# Records by modification level
for level in [0, 1, 2]:
    custom_count = custom_blockchain.count_by_level(level)
    substrate_count = substrate_blockchain.count_by_level(level)
    assert custom_count == substrate_count, f"Level {level} mismatch"
```

## Performance Comparison

Expected performance improvements with Substrate:

| Metric | Custom Blockchain | Substrate | Improvement |
|--------|-------------------|-----------|-------------|
| Block time | ~5 minutes (batched) | ~6 seconds | 50x faster |
| Query latency | <100ms (PostgreSQL) | <100ms (RocksDB) | Similar |
| Submission latency | <200ms | <200ms | Similar |
| Finality | Immediate (single node) | <10s (multi-node BFT) | Production-ready |
| Runtime upgrades | Manual restart | Forkless (WASM) | Zero downtime |
| Governance | Off-chain | On-chain (democracy) | Decentralized |

## Troubleshooting

### Migration Script Fails

```bash
# Check Substrate node is running
curl -H "Content-Type: application/json" \
     -d '{"id":1, "jsonrpc":"2.0", "method":"system_health"}' \
     http://localhost:9944

# Verify account has balance
# (Submission requires gas fees)
```

### Records Don't Match

If validation finds mismatches:

```python
# Export both for comparison
custom_blockchain.export_to_csv('/tmp/custom.csv')
substrate_blockchain.export_to_csv('/tmp/substrate.csv')

# Diff
import csv
custom = set(csv.reader(open('/tmp/custom.csv')))
substrate = set(csv.reader(open('/tmp/substrate.csv')))

missing_in_substrate = custom - substrate
extra_in_substrate = substrate - custom
```

### Performance Issues

If Substrate is slower than expected:

- Check disk I/O (RocksDB requires fast SSD)
- Increase node resources (RAM, CPU)
- Optimize batch size (try 50-200 records per batch)
- Use archive node pruning settings

## Post-Migration

### Archive Custom Blockchain

After successful migration and 90-day verification period:

```bash
# Create final archive
pg_dump birthmark_chain | gzip > birthmark_custom_blockchain_final.sql.gz

# Store in long-term archive
aws s3 cp birthmark_custom_blockchain_final.sql.gz \
    s3://birthmark-archives/blockchain-migration-2026-01/
```

### Update Documentation

- Update architecture diagrams
- Update API documentation
- Update developer guides
- Publish migration post-mortem
- Document lessons learned

### Monitor Production

After migration, monitor:

- Block production rate (should be consistent ~6s)
- Finalization lag (should be <10s)
- Transaction pool size (should stay low)
- Peer count (all validators connected)
- Query latency (maintain <500ms p95)

---

**Migration Support:** samryan.pdx@proton.me

**Last Updated:** January 2, 2026
