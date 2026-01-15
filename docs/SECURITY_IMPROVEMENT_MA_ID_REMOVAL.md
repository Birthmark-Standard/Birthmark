# Security Improvement: Remove MA/DA ID from Blockchain Records

**Date:** January 10, 2026
**Status:** Architectural Correction Required
**Priority:** High - Security & Privacy Enhancement

---

## Issue

Current Phase 1 implementation stores `authority_id` (MA/DA ID) in blockchain records. This creates an unnecessary attack vector and privacy leak.

**Current Blockchain Record (INCORRECT):**
```python
{
    "image_hash": "sha256_hex_64_chars",
    "submission_type": "camera" | "software",
    "modification_level": 0 | 1 | 2,
    "authority_id": "SIMULATED_CAMERA_001",  # ← SHOULD NOT BE HERE
    "submission_server_id": "server_public_key",
    "timestamp": 1699564800,
    "block_number": 12345
}
```

---

## Security Rationale

### Why MA/DA ID Should NOT Be on Blockchain:

1. **No Additional Value:**
   - Blockchain already validates image authenticity
   - MA/DA identity doesn't increase trustworthiness of record
   - Public doesn't need to know which manufacturer validated

2. **Attack Vector:**
   - If one manufacturer's security is compromised, attacker can identify ALL images from that manufacturer
   - Enables targeted attacks: "Find all images validated by Manufacturer X"
   - Makes system-wide vulnerabilities exploitable at manufacturer level

3. **Privacy Leak:**
   - Reveals market share and usage patterns per manufacturer
   - Can track which manufacturers are used in which regions/contexts
   - Enables manufacturer fingerprinting

4. **Principle of Least Information:**
   - Only store what's necessary for verification
   - Image hash + modification level is sufficient for public verification
   - MA/DA identity is internal validation detail, not public concern

---

## Correct Architecture

### Phase 1: Submission Flow

**Step 1: Camera Submission to Blockchain Node**
```python
# Manufacturer certificate (used for routing)
POST /api/v1/submit
{
    "submission_type": "camera",
    "image_hashes": [...],
    "manufacturer_cert": {
        "authority_id": "SIMULATED_CAMERA_001",  # ← NEEDED for routing
        "validation_endpoint": "http://localhost:8001/validate",
        "camera_token": {...},
        "key_reference": {...}
    }
}
```

**Step 2: Blockchain Node Routes to MA**
- Extract `authority_id` from certificate
- Route validation request to correct MA endpoint
- MA validates and returns PASS/FAIL
- **Discard `authority_id` after validation**

**Step 3: Store on Blockchain (CORRECTED)**
```python
# Blockchain record (authority_id REMOVED)
{
    "image_hash": "sha256_hex_64_chars",
    "submission_type": "camera" | "software",
    "modification_level": 0 | 1 | 2,
    "parent_image_hash": "sha256_hex_64_chars" | None,
    "submission_server_id": "server_public_key",  # Which node accepted
    "timestamp": 1699564800,
    "block_number": 12345
}
```

### Accessing MA/DA Information

**For Audit/Investigation (Authorized Access Only):**

1. **MA Validation Logs (Private):**
   - MA maintains encrypted audit logs of validations
   - Logs include: encrypted camera token, validation result, timestamp
   - Only accessible to MA with proper authorization

2. **Blockchain Node Submission Logs (Private):**
   - Node maintains private logs of submissions received
   - Logs include: full submission (with authority_id), validation routing, response
   - Not published to blockchain
   - Only accessible to node operator

3. **Recovery Path:**
   - If investigation needed: Query blockchain for image hash
   - Identify which submission server accepted it (from `submission_server_id`)
   - Contact submission server for private logs
   - Server provides authority_id from internal logs
   - Contact MA for validation details (with authorization)

**Accessing MA identity requires:**
1. Access to blockchain (public)
2. Access to submission server private logs (requires server operator permission)
3. Decryption of MA validation logs (requires MA operator permission)

This creates appropriate access barriers while preserving auditability.

---

## Data Structure Changes

### What Stays

**Manufacturer Certificate (for routing):**
```python
{
    "authority_id": "MANUFACTURER_001",  # ✅ KEEP - needed for routing
    "validation_endpoint": "https://ma.manufacturer.com/validate",
    "camera_token": {...},
    "key_reference": {...}
}
```

### What Changes

**Blockchain Record (stored permanently):**
```python
# BEFORE (Phase 1 - INCORRECT)
{
    "image_hash": "...",
    "authority_id": "MANUFACTURER_001",  # ❌ REMOVE THIS
    "timestamp": 1699564800
}

# AFTER (Phase 2 - CORRECT)
{
    "image_hash": "...",
    # authority_id removed
    "timestamp": 1699564800
}
```

**Record Size Impact:**
- Removes variable-length string (20-50 bytes typically)
- Further reduces storage overhead
- Improves privacy without sacrificing functionality

---

## Implementation Changes Required

### Phase 1 (Current - Needs Correction)

**Files to Update:**

1. **`packages/blockchain/src/models.py`** (or equivalent)
   - Remove `authority_id` from blockchain record schema
   - Keep in submission processing (for routing)
   - Discard after validation

2. **`packages/blockchain/src/api.py`**
   - Extract `authority_id` from certificate for routing
   - Do NOT pass to blockchain storage function
   - Store `authority_id` in private node logs only

3. **Database Schema:**
   ```sql
   -- OLD (incorrect)
   CREATE TABLE image_hashes (
       image_hash VARCHAR(64) PRIMARY KEY,
       authority_id VARCHAR(100),  -- ❌ REMOVE
       ...
   );

   -- NEW (correct)
   CREATE TABLE image_hashes (
       image_hash VARCHAR(64) PRIMARY KEY,
       -- authority_id removed
       ...
   );

   -- Separate private audit log (not blockchain)
   CREATE TABLE submission_audit_log (
       submission_id UUID PRIMARY KEY,
       image_hash VARCHAR(64),
       authority_id VARCHAR(100),  -- ✅ Store here (private)
       validation_response JSONB,
       received_at TIMESTAMP
   );
   ```

4. **API Documentation:**
   - Update API specs in CLAUDE.md
   - Update verification response format
   - Update example responses

---

## Phase 2 Substrate Implementation

### Pallet Design (Correct from Start)

**Birthmark Record Pallet:**
```rust
#[pallet::storage]
pub type ImageHashes<T: Config> = StorageMap<
    _,
    Blake2_128Concat,
    [u8; 32],  // image_hash
    ImageRecord,
    OptionQuery,
>;

#[derive(Encode, Decode, Clone, PartialEq, Eq, RuntimeDebug, TypeInfo)]
pub struct ImageRecord {
    pub submission_type: SubmissionType,
    pub modification_level: u8,
    pub parent_image_hash: Option<[u8; 32]>,
    pub submission_server_id: [u8; 32],
    pub timestamp: u64,
    // NOTE: authority_id NOT included
}
```

**Private Node Logs (Off-Chain):**
- Store authority routing information in off-chain worker storage
- Not included in blockchain state
- Accessible only to node operator

---

## Verification Response Impact

**Current (Incorrect):**
```json
GET /api/v1/verify/{hash}
{
    "verified": true,
    "modification_level": 1,
    "authority_id": "MANUFACTURER_001",  // ❌ Should not expose
    "timestamp": 1699564800
}
```

**Corrected:**
```json
GET /api/v1/verify/{hash}
{
    "verified": true,
    "modification_level": 1,
    "timestamp": 1699564800,
    "submission_server": "server_pubkey_hash"  // Which node, not which MA
}
```

**User Interpretation:**
- ✅ "This image was authenticated by the Birthmark network on this date"
- ❌ NOT: "This image was authenticated by Manufacturer X"

---

## Migration Path (Phase 1 → Phase 2)

1. **Update Phase 1 Implementation:**
   - Modify database schema (remove authority_id column)
   - Update API to not return authority_id
   - Create private audit log table
   - Migration script to move existing authority_id data to audit log

2. **Document Change:**
   - Update CLAUDE.md data structures
   - Update DEMO_PHASE1.md expected output
   - Update API documentation

3. **Phase 2 Substrate:**
   - Design pallets without authority_id from start
   - Implement off-chain worker for private audit logs
   - No migration needed (clean implementation)

---

## Documentation Updates Needed

**Files to Update:**

1. **CLAUDE.md:**
   - Section: "Data Structures" → Registry Record
   - Remove `authority_id` from example
   - Add explanation of private audit logs

2. **DEMO_PHASE1.md:**
   - Update expected verification output
   - Remove authority_id from examples

3. **PHASE_2_PLANNING.md:**
   - Add pallet design notes
   - Reference this document for rationale

4. **API Documentation:**
   - Update all endpoint specs
   - Update verification response format

---

## Security Benefits

### Before (with authority_id):
- Attacker knows: "Image X was validated by Manufacturer Y"
- Attacker can: Target all images from Manufacturer Y
- If Manufacturer Y compromised: Easy to find all vulnerable images

### After (without authority_id):
- Attacker knows: "Image X was authenticated by Birthmark network"
- Attacker cannot: Identify which manufacturer without server access
- If Manufacturer Y compromised: Cannot easily find their images on blockchain

**Additional Layer:**
- Requires access to private submission server logs (server operator permission)
- Requires decryption of MA validation logs (MA operator permission)
- Creates proper access barriers for sensitive information

---

## Summary

**Key Change:**
- **KEEP** `authority_id` in manufacturer certificate (for routing during submission)
- **REMOVE** `authority_id` from blockchain record (unnecessary and creates attack vector)
- **STORE** `authority_id` in private submission server audit logs (for authorized access)

**Benefits:**
- ✅ Reduces attack surface (cannot target specific manufacturers)
- ✅ Improves privacy (manufacturer identity not public)
- ✅ Maintains auditability (logs available with proper authorization)
- ✅ Reduces storage overhead (smaller records)
- ✅ Aligns with principle of least information

**Next Actions:**
1. Update Phase 1 implementation (database schema + API)
2. Update all documentation (CLAUDE.md, DEMO_PHASE1.md, etc.)
3. Design Phase 2 Substrate pallets without authority_id
4. Document private audit log access procedures

---

**Ideally, the only way to know which manufacturer authorized an image is to decrypt the associated log.**

This architectural change achieves that goal while maintaining full system functionality and auditability.
