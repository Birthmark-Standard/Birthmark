# Birthmark Phase 2 Architecture Updates

**Version:** 2.0
**Date:** November 2025
**Status:** Active Development
**Purpose:** Document architectural refinements from security analysis and Apple partnership strategy discussions

---

## Document Purpose

This document captures critical architectural refinements for Phase 2 based on:
- Security analysis and threat modeling
- Apple partnership strategy discussions
- Technical implementation lessons learned
- Abuse detection and monitoring requirements

**Related Documents:**
- Original Plan: [Birthmark_Phase_2_Plan_iOS_App.md](../phase-plans/Birthmark_Phase_2_Plan_iOS_App.md)
- Phase 1-2 SMA Plan: [Birthmark_Phase_1-2_Plan_SMA.md](../phase-plans/Birthmark_Phase_1-2_Plan_SMA.md)

---

## Critical Terminology Correction

### SMA = Simulated Manufacturing Authority

**Correction:** SMA stands for "Simulated Manufacturing Authority," not "Substitute Manufacturing Authority"

**Role in Phase 2:**
- Acts as stand-in for Apple's Manufacturing Authority during iOS proof-of-concept
- Provides device provisioning, validation, and abuse monitoring
- Will be replaced by actual manufacturer (Apple) Manufacturing Authority in Phase 3

**Why "Simulated":**
- Demonstrates what a real manufacturer MA would do
- Validates the architecture before manufacturer partnerships
- Allows testing without requiring manufacturer cooperation

---

## Updated Device Identity Architecture

### Previous Approach (Original Phase 2 Plan)

**Old method:**
```
device_fingerprint = SHA256(
    UIDevice.identifierForVendor +
    cryptographic_random_seed +
    "Birthmark-Standard-iOS-v1"
)
```

**Issues with old approach:**
- Not clear what happens if device name changes
- Ambiguous about what gets stored vs. discarded
- Unclear persistence model

### New Approach: Device Secret with Frozen Identity

**Device Secret Creation (Permanent):**

```swift
// Step 1: Generate random seed (32 bytes)
var randomBytes = [UInt8](repeating: 0, count: 32)
SecRandomCopyBytes(kSecRandomDefault, 32, &randomBytes)
let randomSeed = Data(randomBytes)

// Step 2: Get device name
let deviceName = UIDevice.current.name

// Step 3: Create device secret (PERMANENT)
let combined = randomSeed + deviceName.data(using: .utf8)!
let deviceSecret = SHA256.hash(data: combined)

// Step 4: Store ONLY device_secret in Keychain
// device_secret: 32 bytes (permanent identifier)

// Step 5: DISCARD randomSeed and deviceName (never stored)
// These are only used during provisioning, then thrown away
```

**Critical Properties:**

1. **Frozen at Provisioning Time**
   - `device_secret` is created once during first app launch
   - Never regenerated or recalculated
   - Remains unchanged even if user renames device later

2. **Inputs Are Discarded**
   - `random_seed` is never stored (discarded immediately)
   - `device_name` is never stored (discarded immediately)
   - Only the final hash (`device_secret`) is retained

3. **Keychain Storage**
   - Store: `device_secret` (32 bytes)
   - Store: `key_tables` (3 tables of 1,000 keys each)
   - Store: `key_table_indices` (which global tables: e.g., [42, 157, 891])
   - Do NOT store: `random_seed`, `device_name`

**Why This Matters:**
- Device remains identifiable even after rename
- Consistent authentication across app reinstalls (if Keychain persists)
- Clear security boundary (only secret is stored)

---

## SMA Key Table Architecture

### Global Key Table Pool

**SMA maintains 2,500 global key tables:**
- Each table contains 1,000 encryption keys (32 bytes each)
- Total: 2.5 million keys in the global pool
- Each device is randomly assigned 3 tables during provisioning

### Provisioning Flow

**Device requests provisioning:**

```json
POST /api/provision
{
  "device_id": "uuid",
  "device_secret_hash": "sha256_of_device_secret",
  "platform": "iOS"
}
```

**SMA response:**

```json
{
  "device_id": "uuid",
  "key_tables": [
    ["base64_key1", "base64_key2", ..., "base64_key1000"],  // Table 42
    ["base64_key1", "base64_key2", ..., "base64_key1000"],  // Table 157
    ["base64_key1", "base64_key2", ..., "base64_key1000"]   // Table 891
  ],
  "key_table_indices": [42, 157, 891]
}
```

**What Gets Stored:**
- Device stores: 3 complete tables (3,000 keys total) + global indices
- SMA stores: `device_id` → `device_secret` mapping + assigned table indices

**Key Properties:**
- Random table selection prevents pattern analysis
- Device stores actual key data (not just indices)
- SMA can decrypt any token from any device (has all global keys)
- Aggregation server has no keys (cannot decrypt)

---

## Updated Image Signing Flow

### Certificate Generation

**For each photo submission:**

```swift
// Step 1: Retrieve device_secret from Keychain (same value every time)
let deviceSecret = keychain.get("device_secret")

// Step 2: Randomly select one of 3 assigned tables
let selectedTableIndex = Int.random(in: 0..<3)  // 0, 1, or 2
let globalTableIndex = keyTableIndices[selectedTableIndex]  // e.g., 157

// Step 3: Randomly select a key from that table
let selectedKeyIndex = Int.random(in: 0..<1000)
let encryptionKey = keyTables[selectedTableIndex][selectedKeyIndex]

// Step 4: Encrypt device_secret with selected key
let cameraToken = AES_GCM.encrypt(
    plaintext: deviceSecret,
    key: encryptionKey,
    nonce: generateRandomNonce()  // 12 bytes, unique per encryption
)

// Step 5: Build certificate with GLOBAL table index
let certificate = {
    "camera_token": base64Encode(cameraToken),
    "table_index": globalTableIndex,  // 157 (not local index 1)
    "key_index": selectedKeyIndex,     // 0-999
    "timestamp": currentTimestamp,
    "metadata": {...}
}
```

**Certificate Format:**

```json
{
  "image_hash": "sha256_of_processed_image",
  "camera_token": "base64_encrypted_device_secret",
  "table_index": 157,      // GLOBAL table index (from key_table_indices)
  "key_index": 423,        // Index within that table (0-999)
  "timestamp": 1732000000,
  "gps_hash": "optional_sha256",
  "signature": "device_signature_over_bundle"
}
```

**Critical Properties:**
- `camera_token` varies with every photo (random key + random nonce)
- Always decrypts to the same `device_secret`
- SMA can identify device by decrypted secret
- Aggregation server cannot decrypt (no keys)

---

## Updated SMA Validation Flow

### How SMA Verifies Device Identity

**Validation Request (from Aggregation Server):**

```json
POST /api/validate
{
  "camera_token": "base64_encrypted_device_secret",
  "table_index": 157,      // Global table index
  "key_index": 423,        // Key within table
  "timestamp": 1732000000
}
```

**SMA Validation Process:**

```python
def validate_submission(request):
    # Step 1: Extract validation parameters
    camera_token = base64_decode(request.camera_token)
    table_index = request.table_index  # e.g., 157
    key_index = request.key_index      # e.g., 423

    # Step 2: Retrieve encryption key from global pool
    encryption_key = global_key_tables[table_index][key_index]

    # Step 3: Decrypt camera token
    try:
        decrypted_secret = AES_GCM.decrypt(
            ciphertext=camera_token,
            key=encryption_key
        )
    except DecryptionError:
        return {"status": "fail", "reason": "invalid_token"}

    # Step 4: Look up device by matching device_secret
    device = db.query(
        "SELECT * FROM devices WHERE device_secret = ?",
        decrypted_secret
    )

    if not device:
        return {"status": "fail", "reason": "unknown_device"}

    # Step 5: Check if device is blacklisted
    if device.is_blacklisted:
        return {"status": "fail", "reason": "blacklisted"}

    # Step 6: Log submission for abuse detection
    log_submission(
        device_id=device.device_id,
        timestamp=request.timestamp,
        image_hash=None  # SMA never sees image hash
    )

    # Step 7: Return validation result
    return {
        "status": "pass",
        "device_id": device.device_id
    }
```

**Database Schema Updates:**

```sql
-- Registered devices
CREATE TABLE devices (
    device_id UUID PRIMARY KEY,
    device_secret BYTEA NOT NULL UNIQUE,  -- 32 bytes (what gets decrypted)
    key_table_indices INTEGER[3] NOT NULL, -- e.g., [42, 157, 891]
    platform VARCHAR(50) NOT NULL,         -- 'iOS', 'Raspberry Pi', etc.
    provisioned_at TIMESTAMP NOT NULL,
    is_blacklisted BOOLEAN DEFAULT FALSE,
    blacklisted_at TIMESTAMP,
    blacklist_reason TEXT,
    INDEX idx_device_secret (device_secret)
);

-- Submission logs (for abuse detection)
CREATE TABLE submissions (
    id SERIAL PRIMARY KEY,
    device_id UUID REFERENCES devices(device_id),
    timestamp TIMESTAMP NOT NULL,
    validation_result VARCHAR(10) NOT NULL,  -- 'pass' or 'fail'
    INDEX idx_device_timestamp (device_id, timestamp)
);
```

**Critical Privacy Invariant:**
- SMA validates device authenticity (knows which device)
- SMA never sees `image_hash` (doesn't know what was photographed)
- Aggregation server sees `image_hash` but cannot decrypt `camera_token`

---

## Automated Abuse Detection System

### Fully Automated Blacklisting

**Threat Model:**
- Keychain credentials can be extracted (jailbroken device, malware)
- Stolen `device_secret` + `key_tables` can forge valid certificates
- Need behavioral monitoring to limit damage from credential theft

**Detection Strategy:**

```python
def check_abuse_daily():
    """
    Runs once per day via cron job.
    No manual review required.
    Threshold: 10,000 submissions in 24 hours.
    """
    for device_id in get_all_registered_devices():
        count_24h = count_submissions(
            device_id=device_id,
            time_window=timedelta(hours=24)
        )

        if count_24h > 10_000:
            # Automatic permanent ban
            blacklist_device(
                device_id=device_id,
                reason=f"Exceeded daily limit: {count_24h} submissions"
            )

            log_incident(
                device_id=device_id,
                submission_count=count_24h,
                incident_type="exceeded_daily_limit"
            )

            # Optional: Alert security team
            send_alert(
                severity="high",
                message=f"Device {device_id} auto-blacklisted: {count_24h} submissions/24h"
            )
```

**Warning System:**

```python
def check_abuse_warnings():
    """
    Runs hourly.
    Warning at 8,000 submissions in 24 hours.
    """
    for device_id in get_all_registered_devices():
        count_24h = count_submissions(device_id, timedelta(hours=24))

        if 8_000 <= count_24h < 10_000:
            log_warning(
                device_id=device_id,
                submission_count=count_24h,
                warning_type="approaching_limit"
            )

            # Optional: Could notify device via API
            # (but attackers would just ignore)
```

**Rationale for 10,000/day Threshold:**

| User Type | Expected Usage | Exceeds Threshold? |
|-----------|----------------|-------------------|
| Casual photographer | 10-50 photos/day | No (0.1-0.5%) |
| Professional photographer | 500-2,000 photos/day | No (5-20%) |
| Wedding/event photographer | 2,000-5,000 photos/day | No (20-50%) |
| **Industrial-scale abuse** | **10,000+ photos/day** | **Yes (100%+)** |

**What This Catches:**
- Botnets using stolen credentials at scale
- Coordinated disinformation campaigns
- Automated systems generating fake authenticity

**What This Misses (Acceptable):**
- Small-scale abuse (<10,000/day)
- Sophisticated attackers who stay under threshold
- Distributed attacks across multiple stolen credentials

**Why This Is Acceptable:**
- Proof-of-concept, not production security
- Small-scale abuse is expensive/slow for attackers
- Demonstrates: behavioral monitoring helps but isn't sufficient
- Proves the case for hardware security (Secure Enclave)

### API Integration

**Updated Validation Endpoint:**

```python
@app.post("/api/validate")
async def validate(request: ValidationRequest):
    # Decrypt camera token
    decrypted_secret = decrypt_camera_token(
        request.camera_token,
        request.table_index,
        request.key_index
    )

    # Find device
    device = find_device_by_secret(decrypted_secret)

    if not device:
        return {"status": "fail", "reason": "unknown_device"}

    # Check blacklist
    if device.is_blacklisted:
        log_blocked_attempt(device.device_id)
        return {"status": "fail", "reason": "blacklisted"}

    # Log submission
    log_submission(device.device_id, request.timestamp)

    return {"status": "pass", "device_id": device.device_id}
```

**New SMA Endpoints:**

```python
# Check device status
GET /api/device/{device_id}/status
Response:
{
  "device_id": "uuid",
  "is_blacklisted": false,
  "submissions_24h": 147,
  "submissions_total": 3421,
  "provisioned_at": "2025-01-15T10:30:00Z"
}

# Blacklist statistics (internal only)
GET /api/admin/blacklist/stats
Response:
{
  "total_blacklisted": 3,
  "blacklisted_today": 1,
  "top_offenders": [
    {"device_id": "uuid", "count_24h": 47832, "blacklisted_at": "..."}
  ]
}
```

---

## Security Model Clarifications

### Intentional Weaknesses (Proof-of-Concept)

**What CAN Be Attacked:**

1. **Keychain Extraction**
   - Jailbroken devices can access Keychain
   - Malware with sufficient privileges can extract keys
   - `device_secret` and `key_tables` can be stolen

2. **Credential Reuse**
   - Stolen credentials work until device is blacklisted
   - Attacker can forge valid certificates
   - Works across multiple devices (credential theft)

3. **No Hardware Isolation**
   - Keys stored in software (Keychain), not Secure Enclave
   - No hardware root of trust
   - No tamper detection

**What This PROVES:**

1. **Software-only security has demonstrable limits**
   - Keychain is better than nothing, but extractable
   - Behavioral monitoring helps, but isn't sufficient
   - Hardware manufacturer cooperation is necessary

2. **Abuse detection is defense-in-depth, not primary defense**
   - Catches high-volume attacks
   - Doesn't prevent credential theft
   - Doesn't stop sophisticated low-volume attacks

3. **Hardware integration is not optional**
   - Only Secure Enclave can prevent credential extraction
   - Need manufacturer cooperation for production deployment
   - When security researchers break it → that's our evidence

### Security Roadmap

**Phase 2 (Current): Keychain Storage**
- Validates workflow and architecture
- Demonstrates performance is acceptable
- Documents limitations clearly
- Invites security community to attack

**Phase 3 (With Apple): Secure Enclave Integration**
- Hardware-backed credential storage
- Hardware root of trust for cryptographic operations
- Tamper detection and key isolation
- Sensor-level integration (before ISP processing)

---

## Documentation Updates Required

### README.md Security Section

Add this section to main README:

```markdown
## Phase 2 Security Model

### Known Limitations

This Phase 2 iOS implementation uses iOS Keychain (not Secure Enclave).
**This is intentional** - we're validating workflow before manufacturer partnerships.

**What can be attacked:**
- Device credentials can be extracted on jailbroken devices
- Stolen credentials work until abuse detection triggers (10,000 submissions/day)
- No hardware root of trust

**Why this is acceptable:**
- Proof-of-concept to validate photographer adoption
- Documents exactly what hardware integration solves
- Behavioral monitoring demonstrates defense-in-depth approach
- When broken by security researchers, proves need for Secure Enclave

**Phase 3 with Apple will provide:**
- Hardware-backed credential storage (Secure Enclave)
- Hardware root of trust for cryptographic operations
- Sensor-level integration (before ISP processing)
- Tamper detection and key isolation
```

### Security Audit Invitation

Add to testing documentation:

```markdown
## Security Audit Invitation

We're inviting the security community to audit our Phase 2 implementation.

**What we want you to test:**
1. Extract device credentials from iOS Keychain
2. Demonstrate credential reuse attacks
3. Test if abuse detection (10k/day limit) can be evaded
4. Document what Secure Enclave integration would prevent

**Code:** [GitHub Repository]
**Docs:** [Technical Specifications]

**Why we're doing this:**
- We'll publish all successful attacks as evidence for manufacturer partnerships
- Goal: Prove that hardware security is necessary, not optional
- This is proof-of-concept, not production - we expect you to break it

**Responsible Disclosure:**
- No responsible disclosure needed - we expect attacks
- Please document your findings publicly
- We'll cite your work in manufacturer discussions
```

---

## Apple Partnership Strategy Updates

### Evidence Package - Security Section

**Add to Phase 3 materials:**

#### "Security Analysis and Lessons Learned"

**1. Credential Extraction Documented**
- Invite security researchers to extract Keychain credentials
- Publish attack writeups as evidence
- "Here's what happened without hardware security"

**2. Abuse Detection Results**
- "Automated blacklisting caught X attempted exploitation events"
- "Small-scale abuse (<10k/day) went undetected, as expected"
- "Demonstrates behavioral monitoring is necessary but not sufficient"

**3. Clear Hardware Requirements**
- "Only Secure Enclave can prevent credential extraction"
- "Software-only security validated workflow but has clear limits"
- "Need manufacturer partnership for production deployment"

### Updated Pitch to Apple

**Opening:**

> "Our iOS proof-of-concept has 87 active photographers and works well enough to prove demand, but security researchers have documented that Keychain credentials are extractable. Our automated abuse detection limits damage, but only Secure Enclave integration can provide the security guarantees journalists need."

**What we bring:**
- Validated workflow and user demand
- Open-source reference implementation
- Clear documentation of what hardware solves
- Nonprofit positioning (no commercial conflict)

**What Apple provides:**
- Secure Enclave integration (hardware root of trust)
- Camera pipeline integration (sign at capture time)
- Brand association with content authenticity efforts

---

## Testing Strategy Updates

### Security Audit Invitation (New)

**After basic functionality works, invite community audit:**

**Post to r/netsec, r/crypto, r/ReverseEngineering:**

> **Title:** [Open Source Security Audit Request] Photo Authentication iOS App
>
> We've built an open-source photo authentication app for photojournalists.
> Phase 2 uses iOS Keychain - we know it's extractable, that's by design.
>
> **We're inviting security researchers to:**
> 1. Extract device credentials from Keychain
> 2. Demonstrate credential reuse attacks
> 3. Test if abuse detection (10k/day limit) can be evaded
> 4. Document what Secure Enclave integration would prevent
>
> **Code:** [GitHub]
> **Docs:** [Technical specs]
>
> We'll publish all successful attacks as evidence for manufacturer partnerships.
> **Goal:** Prove that hardware security is necessary, not optional.

**Expected Results:**
- Researchers extract credentials → proves Keychain limitation
- High-volume attacks get blacklisted → proves monitoring works
- Small-scale attacks succeed → proves monitoring isn't sufficient
- All of this becomes evidence for Apple pitch

---

## Implementation Checklist

### iOS App Updates

- [ ] Generate `device_secret` from `random_seed` + `device_name`
- [ ] Discard `random_seed` and `device_name` after hashing
- [ ] Store only `device_secret` permanently in Keychain
- [ ] Use global table indices in certificates (not local 0-2)
- [ ] Random key selection from assigned tables for each submission
- [ ] Handle provisioning failure with reinstall recommendation

### SMA Service Updates

- [ ] Maintain 2,500 global key tables (1,000 keys each)
- [ ] Random table selection during provisioning (select 3 from 2,500)
- [ ] Return both key data and global indices to devices
- [ ] Submission logging with timestamps
- [ ] Daily cron job checking 24-hour submission counts
- [ ] Automated blacklisting at 10,000/day threshold
- [ ] Warning system at 8,000/day threshold
- [ ] Blacklist check in validation endpoint

### Documentation Updates

- [ ] Update security model section in main README
- [ ] Document intentional weaknesses explicitly
- [ ] Add security audit invitation section
- [ ] Prepare evidence package template for Phase 3
- [ ] Update iOS app README with security warnings

### Testing Additions

- [ ] Test that `device_secret` doesn't change after device rename
- [ ] Test random key selection produces varying `camera_tokens`
- [ ] Test SMA correctly decrypts with global table indices
- [ ] Test abuse detection triggers at 10,001 submissions
- [ ] Test blacklisted devices get validation failure
- [ ] Test warning system at 8,000 submissions
- [ ] Integration test: extract Keychain, attempt reuse

---

## Key Technical Clarifications

### Device Secret Stability

**Properties:**
- Created once during provisioning
- Never regenerated or changed
- Survives device name changes
- Survives app reinstall (if Keychain persists)

**Why:**
- Consistent device identity across lifecycle
- Predictable validation behavior
- Clear security boundary

### Camera Token Variability

**Properties:**
- Different for every image
- Same plaintext (`device_secret`), different encryption key + nonce
- SMA can always decrypt (has all global keys)
- Aggregation server cannot decrypt (has no keys)

**Why:**
- Prevents replay attacks
- Prevents pattern analysis
- Maintains privacy separation

### Table Index Mapping

**Structure:**
- Device has 3 tables locally (indices 0, 1, 2)
- Each maps to a global index (e.g., 42, 157, 891)
- Certificate uses global index (e.g., 157, not local 1)
- SMA uses global index to look up key

**Why:**
- SMA can decrypt without knowing device identity first
- Enables table rotation in future phases
- Simplifies key management

### Separation of Concerns

**Aggregation Server:**
- Sees: `image_hash`, certificate metadata
- Routes validation requests to SMA
- Never decrypts `camera_token`
- Submits validated hashes to blockchain

**SMA:**
- Decrypts `camera_token`
- Verifies device identity
- Performs abuse detection
- Never sees `image_hash` (doesn't know what was photographed)

**Blockchain:**
- Records attestation (hash + timestamp)
- Never sees device identity
- Never sees image content
- Public verification

---

## Changes Summary

### What Changed from Original Phase 2 Plan

**Device Identity:**
- Now: Hash of `random_seed` + `device_name`, inputs discarded
- Before: Device fingerprint with unclear persistence model

**Key Storage:**
- Now: Only `device_secret` + `key_tables` + `key_table_indices` stored
- Before: Unclear what gets stored vs. discarded

**Table Assignment:**
- Now: SMA maintains 2,500 global pool, assigns 3 random tables
- Before: Implied but not explicitly detailed

**Certificate Format:**
- Now: Uses global table indices (e.g., 157), not local (e.g., 1)
- Before: Table indexing was ambiguous

**Abuse Detection:**
- Now: Automated 10,000/day blacklisting with 8,000/day warning
- Before: Not specified

**Security Strategy:**
- Now: Explicitly invite attacks to prove hardware necessity
- Before: Security model was understated

**Terminology:**
- Now: SMA = Simulated Manufacturing Authority
- Before: Sometimes called "Substitute"

### What Stayed the Same

**Overall Architecture:**
- Same flow: Device → Aggregation Server → SMA → Blockchain
- Same privacy separation
- Same integration with Phase 1 infrastructure

**Testing Strategy:**
- TestFlight beta testing
- 60-100 photographer testers
- Performance benchmarking
- User research approach

**Timeline and Milestones:**
- 3-4 months total
- Progressive rollout waves
- Month 4 evidence package

**Performance Targets:**
- <20ms overhead
- <2% battery impact
- >98% upload success rate

**User Experience:**
- Zero-latency capture
- Background upload
- Offline queue support

---

## Open Questions & Decisions

### Implementation Questions

1. **Should blacklisted devices receive specific error message or generic "fail"?**
   - **Decision:** Generic "fail" with no specific message
   - **Rationale:** Don't help attackers understand detection

2. **What happens if SMA provisioning fails?**
   - **Decision:** App recommends full reinstall
   - **Rationale:** Simplifies error handling for proof-of-concept

3. **Should there be warning at 5,000 submissions before hitting 10,000 blacklist?**
   - **Decision:** Warning at 8,000 submissions
   - **Rationale:** Gives legitimate users (e.g., event photographers) advance notice

4. **How long should submission logs be retained (storage/privacy)?**
   - **Decision:** No expiration at this stage of development
   - **Rationale:** Discussion with privacy experts deferred to later phase

5. **Should `device_secret` be re-hashed before storing in Keychain (defense in depth)?**
   - **Decision:** No, `device_secret` is already a hash
   - **Rationale:** Additional hashing provides no security benefit

### Strategic Questions

1. **When to launch security audit invitation?**
   - **Recommendation:** After Month 2 (first beta wave working)
   - **Rationale:** Need functional app for researchers to test

2. **How to handle if major vulnerability found early?**
   - **Recommendation:** Document and continue (expected outcome)
   - **Rationale:** Vulnerabilities prove our point to manufacturers

3. **Should we implement rate limiting in addition to daily blacklisting?**
   - **Recommendation:** Not for Phase 2
   - **Rationale:** Keep scope focused, daily limit is sufficient for proof-of-concept

---

## Related Documents

- [Original Phase 2 iOS Plan](../phase-plans/Birthmark_Phase_2_Plan_iOS_App.md)
- [Phase 1-2 SMA Plan](../phase-plans/Birthmark_Phase_1-2_Plan_SMA.md)
- [Phase 1 Deployment Guide](../PHASE_1_DEPLOYMENT_GUIDE.md)
- [Certificate Migration Guide](CERTIFICATE_MIGRATION_GUIDE.md)

---

## Document Maintenance

**Version:** 2.0
**Date:** November 2025
**Author:** Samuel C. Ryan, Birthmark Standard Foundation
**Status:** Active Development

**Revision History:**
- v2.0 (Nov 2025): Major architecture refinements
  - Device secret creation and persistence model
  - SMA key table architecture (2,500 global pool)
  - Automated abuse detection system
  - Security model clarifications
  - Apple partnership strategy updates
- v1.0 (Nov 2025): Original Phase 2 plan (see separate document)

---

**Implementation Note:** These updates refine the security model and abuse detection but don't fundamentally change the core user experience or workflow. The app still captures photos, creates certificates, and submits to the aggregation server. The changes improve our strategic positioning for Apple partnerships by clearly documenting both capabilities and limitations.
