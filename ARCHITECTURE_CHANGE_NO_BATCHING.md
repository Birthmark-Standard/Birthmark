# Architecture Change: Direct Hash Submission (No Batching)

**Date:** December 3, 2025
**Branch:** `claude/validate-submission-server-01Bd2WVoNMS6ynwwjY4X6AHL`

---

## 🔄 Architectural Change

### Original Design (Batching)
- **Purpose:** Reduce gas fees on public blockchain (e.g., Ethereum)
- **Mechanism:** Batch 100-1000 hashes together into Merkle tree
- **Submission:** Single root hash per batch
- **Verification:** Requires Merkle proof

### New Design (Direct Submission)
- **Purpose:** Simple, direct verification on custom blockchain
- **Mechanism:** Each hash submitted individually
- **Submission:** One blockchain transaction per hash
- **Verification:** Direct hash query (user hashes image and queries)

---

## ✅ Why No Batching?

### 1. No Gas Fees
**Custom Birthmark Blockchain:** Operated by like-minded institutions (universities, archives, journalism organizations) with zero gas fees. No financial incentive for batching.

### 2. Simpler User Verification
**With Batching:**
```
User hashes image → Get Merkle proof from aggregator → Verify against root
```

**Without Batching:**
```
User hashes image → Query blockchain directly → Get result
```

**Benefit:** Users can independently verify their images without depending on the aggregator to provide Merkle proofs.

### 3. Immediate Verification
- **With Batching:** Wait for batch accumulation (30+ seconds)
- **Without Batching:** Submit immediately after SMA validation (<2 seconds)

### 4. Crash Recovery Simplicity
- **With Batching:** Track which hashes went into which batch, maintain batch state
- **Without Batching:** Track individual blockchain submissions with `tx_id`

---

## 📋 Changes Made

### 1. Database Schema

**Removed Fields from `PendingSubmission`:**
- `batched` (Boolean) - No longer tracking batch status
- `batched_at` (DateTime) - No longer tracking batch time

**Removed Indexes:**
- `idx_pending_batched` - Index on batched field
- `idx_pending_status` - Composite index on (sma_validated, batched)

**Kept Field:**
- `tx_id` - Renamed purpose: tracks blockchain submission for crash recovery (not batch)

**Migration:** `20241203_0200_remove_batching_fields.py`

### 2. Database Models

**Updated `PendingSubmission` model:**
- Docstring: "awaiting SMA validation and blockchain submission" (removed "batching")
- Removed batching tracking section
- Clarified `tx_id` is for blockchain submission tracking

**Updated `Transaction` model:**
- Docstring: "containing image hash submission" (removed "batch of")
- Added comment: `batch_size` now means "Number of hashes in this transaction"

**Updated `ModificationRecordDB` model:**
- Comment: "when final hash is submitted" (removed "batched")

### 3. Submission API

**File:** `src/aggregator/api/submissions.py`

**Removed `batched=False` from:**
- `submit_camera_bundle()` endpoint (line 66)
- `submit_authentication_bundle_legacy()` endpoint (line 231)
- `submit_certificate_bundle()` endpoint (line 325)

**Added Direct Blockchain Submission:**
- New module: `src/aggregator/blockchain/blockchain_client.py`
- Function: `submit_hash()` - Submits individual validated hash to blockchain
- Integration: Called after SMA validation passes in `validate_camera_transaction_inline()`

**Flow:**
```
Camera → Aggregator → Store in DB → SMA Validation → ✅ PASS → Submit to Blockchain → Update tx_id
                                                    → ❌ FAIL → Mark as failed
```

### 4. Blockchain Client

**New File:** `src/aggregator/blockchain/blockchain_client.py`

**Features:**
- Direct hash submission (no batching)
- Async httpx client
- Timeout handling
- Error recovery
- Returns `tx_id` and `block_height`

**Endpoint:** `POST /api/v1/blockchain/submit`

**Payload:**
```json
{
  "image_hash": "abc123...",
  "timestamp": 1733259600,
  "aggregator_id": "aggregator_node_001",
  "modification_level": 0,
  "parent_image_hash": null,
  "manufacturer_authority_id": "CANON_001"
}
```

---

## 🎯 Impact on Documentation

### Documents Needing Updates

Due to the architectural change, the following documents reference batching and should be updated or have a note added:

1. **WEEK_1_2_VALIDATION_REPORT.md**
   - Section: "Performance Validation" mentions batch creation time
   - Section: "Database Indexes" mentions batching queries
   - Section: "Pre-Deployment Checklist" mentions BATCH_SIZE config
   - Section: "Critical Path" mentions waiting for batching

2. **WEEK_3_INTEGRATION_TESTING_GUIDE.md**
   - Section: "Continuous Capture Summary" mentions waiting for batching
   - Section: "Performance" mentions batch creation time

3. **WEEK_3_SUMMARY.md**
   - Section: "Week 4 Plan" mentions batching service
   - Section: "Phase 1 Simplifications" mentions batching
   - Section: "Next Steps" mentions batching

### Recommended Approach

**Option A:** Add a note at the top of each document:
```markdown
> **⚠️ ARCHITECTURE CHANGE:** As of December 3, 2025, batching has been removed.
> The custom Birthmark blockchain has no gas fees, so each hash is submitted individually.
> See [ARCHITECTURE_CHANGE_NO_BATCHING.md](ARCHITECTURE_CHANGE_NO_BATCHING.md) for details.
```

**Option B:** Update each reference inline (more time-consuming but cleaner)

**Option C:** Mark documents as superseded and create new versions

---

## 🚀 Benefits Summary

| Aspect | With Batching | Without Batching (New) |
|--------|---------------|------------------------|
| **Gas Cost** | Optimized | N/A (zero fees) |
| **Verification** | Complex (Merkle proof) | Simple (direct query) |
| **Latency** | 30+ seconds | <2 seconds |
| **User Independence** | Depends on aggregator | Fully independent |
| **Code Complexity** | High (batch management) | Low (direct submission) |
| **Crash Recovery** | Complex (batch state) | Simple (tx_id tracking) |

---

## 📊 Code Statistics

**Files Changed:**
- 1 migration created
- 3 database models updated
- 1 API file updated (submissions.py)
- 1 new blockchain client created
- 2 new blockchain module files

**Lines Changed:**
- Migration: +50 lines
- Models: -10 lines (removed batching)
- Submissions: +45 lines (blockchain submission)
- Blockchain client: +150 lines (new)

**Total:** ~235 lines added/modified

---

## ✅ Next Steps

1. **Run migration:** `alembic upgrade head`
2. **Update documentation:** Add architecture change notes
3. **Test direct submission:** Mock camera → Aggregator → Blockchain
4. **Verify crash recovery:** Test server outages during submission
5. **Update integration tests:** Remove batching expectations

---

**Prepared By:** Claude Code Agent
**Date:** December 3, 2025
**Branch:** `claude/validate-submission-server-01Bd2WVoNMS6ynwwjY4X6AHL`
