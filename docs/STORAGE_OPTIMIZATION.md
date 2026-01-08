# Substrate Storage Optimization Analysis

**Date**: January 8, 2026
**Status**: In Progress
**Goal**: Reduce per-record storage overhead from ~1KB to ~150-200 bytes

## Executive Summary

The Birthmark blockchain currently uses a full-featured Substrate runtime with unnecessary pallets that add significant overhead. This document outlines the current state, identifies optimization opportunities, and provides implementation steps to achieve 5-10x storage reduction while preserving forkless upgrade capabilities.

---

## Current State Analysis

### Runtime Pallets (13 total)

#### Essential Pallets (5)
1. **frame_system** - Core blockchain functionality
2. **pallet_timestamp** - Block timestamps (required for record timestamps)
3. **pallet_aura** - Block production (Aura consensus)
4. **pallet_grandpa** - Block finality (GRANDPA consensus)
5. **pallet_birthmark** - Core authentication records (custom)

#### Removable Pallets (8)
6. **pallet_balances** - Token balances (NOT NEEDED - no token economy)
7. **pallet_transaction_payment** - Fee handling (NOT NEEDED - feeless for submission server)
8. **pallet_sudo** - Superuser privileges (MAYBE NEEDED initially for emergency governance)
9. **pallet_democracy** - On-chain voting (NOT NEEDED - off-chain governance sufficient)
10. **pallet_collective** - Council/committee management (NOT NEEDED - overkill)
11. **pallet_treasury** - Treasury management (NOT NEEDED - no treasury)
12. **pallet_scheduler** - Scheduled dispatches (NOT NEEDED - no scheduled tasks)
13. **pallet_preimage** - Large preimage storage (NOT NEEDED - dependency of democracy)

**Verdict**: Can remove 7 pallets immediately, maybe 8 if alternative governance approach used.

---

## Current Data Structure Overhead

### ImageRecord Structure
```rust
pub struct ImageRecord<T: Config> {
    pub image_hash: BoundedVec<u8, T::MaxImageHashLength>,           // 64 bytes + 1 length = 65 bytes
    pub submission_type: SubmissionType,                              // 1 byte
    pub modification_level: u8,                                       // 1 byte
    pub parent_image_hash: Option<BoundedVec<u8, T::MaxImageHashLength>>, // 1 + 0-65 bytes
    pub authority_id: BoundedVec<u8, T::MaxAuthorityIdLength>,       // 1 + variable (currently max 100)
    pub owner_hash: Option<BoundedVec<u8, T::MaxImageHashLength>>,   // 1 + 0-65 bytes
    pub timestamp: T::Moment,                                         // 8 bytes (u64)
    pub block_number: BlockNumberFor<T>,                              // 4 bytes (u32)
}
```

**Size Analysis**:
- **Minimum** (no parent, no owner, short authority): ~80 bytes
- **Typical** (with parent, short authority): ~145 bytes
- **Maximum** (all fields, max authority): ~280 bytes

### Transaction Overhead

#### SignedExtra Components (8 checks)
```rust
pub type SignedExtra = (
    frame_system::CheckNonZeroSender<Runtime>,        // ~1 byte
    frame_system::CheckSpecVersion<Runtime>,          // ~4 bytes
    frame_system::CheckTxVersion<Runtime>,            // ~4 bytes
    frame_system::CheckGenesis<Runtime>,              // ~32 bytes (hash)
    frame_system::CheckEra<Runtime>,                  // ~2 bytes
    frame_system::CheckNonce<Runtime>,                // ~4 bytes
    frame_system::CheckWeight<Runtime>,               // ~8 bytes
    pallet_transaction_payment::ChargeTransactionPayment<Runtime>, // ~16 bytes (fee calc)
);
```

**Total SignedExtra**: ~71 bytes per transaction

#### Account Data Overhead
```rust
type AccountData = pallet_balances::AccountData<Balance>;
// Contains: free, reserved, frozen balances + flags
// Size: ~32 bytes per account
```

#### Extrinsic Structure
```rust
pub type UncheckedExtrinsic = generic::UncheckedExtrinsic<Address, RuntimeCall, Signature, SignedExtra>;
// Components:
// - Address: MultiAddress (33 bytes for AccountId32)
// - RuntimeCall: Encoded call data (variable)
// - Signature: MultiSignature (65 bytes for Sr25519)
// - SignedExtra: ~71 bytes
```

**Total Transaction Overhead**: ~169 bytes + call data

### Estimated Current Overhead

For a typical `submit_image_record` call:
- **Extrinsic overhead**: ~169 bytes (address, signature, signed extra)
- **Call data**: ~150 bytes (ImageRecord fields)
- **Storage overhead**: ~50 bytes (storage key, metadata, etc.)
- **SCALE encoding overhead**: ~10-20 bytes

**Total Estimated**: **~380-400 bytes per record**

---

## Optimization Strategy

### Phase 2A: Audit Current Deployment ✅

**Status**: Completed via code analysis

**Findings**:
- 8 unnecessary pallets identified
- Transaction signature overhead unnecessary (only submission server writes)
- Account system overhead unnecessary (no balances)
- Current estimate: ~380-400 bytes per record

### Phase 2B: Create Minimal Runtime

**Goal**: Strip to bare essentials while preserving forkless upgrades

#### Pallets to Keep (5)
1. `frame_system` - Essential
2. `pallet_timestamp` - Required for timestamps
3. `pallet_aura` - Block production
4. `pallet_grandpa` - Finality
5. `pallet_birthmark` - Core logic

#### Pallets to Remove (8)
- `pallet_balances`
- `pallet_transaction_payment`
- `pallet_sudo` (replace with hardcoded root account or off-chain governance)
- `pallet_democracy`
- `pallet_collective`
- `pallet_treasury`
- `pallet_scheduler`
- `pallet_preimage`

#### Account System Simplification

**Current**:
```rust
type AccountData = pallet_balances::AccountData<Balance>;
```

**Optimized**:
```rust
type AccountData = (); // No account data needed
```

#### Transaction Processing Simplification

**Current**: Signed transactions with full validation
**Optimized**: Unsigned inherent transactions from submission server

**Implementation**:
```rust
// Remove SignedExtra complexity
pub type SignedExtra = (
    frame_system::CheckNonZeroSender<Runtime>,
    frame_system::CheckSpecVersion<Runtime>,
    frame_system::CheckGenesis<Runtime>,
);

// Or use unsigned inherent transactions:
impl frame_system::offchain::CreateInherent for Pallet<T> {
    // Submission server creates inherent transactions
    // No signature, no nonce, no fee
}
```

**Estimated Savings**: ~120-150 bytes per transaction

### Phase 2C: Optimize Data Structure

#### Authority ID Compression

**Current**: Variable-length string (max 100 bytes)
```rust
pub authority_id: BoundedVec<u8, T::MaxAuthorityIdLength>, // Max 100 bytes
```

**Optimized**: Lookup table with u16 index
```rust
pub authority_id: u16, // 2 bytes

// Separate lookup table
#[pallet::storage]
pub type AuthorityRegistry<T> = StorageMap<_, Blake2_128Concat, u16, BoundedVec<u8, ConstU32<100>>>;
```

**Savings**: ~18-98 bytes per record (assuming avg authority ID is 20 bytes)

#### Owner Hash Removal (Phase 1)

The `owner_hash` field is optional and rarely used. Consider:
- Remove from initial implementation
- Add via runtime upgrade when attribution feature is needed

**Savings**: 1-66 bytes per record

#### Compact Encoding

Use Substrate's `#[codec(compact)]` attribute for numeric fields:

```rust
#[derive(Encode, Decode, TypeInfo, MaxEncodedLen)]
pub struct ImageRecord<T: Config> {
    pub image_hash: [u8; 32],                    // Fixed 32 bytes (binary, not hex)
    pub submission_type: SubmissionType,         // 1 byte
    pub modification_level: u8,                  // 1 byte
    pub parent_image_hash: Option<[u8; 32]>,     // 1 + 0-32 bytes
    pub authority_id: u16,                       // 2 bytes (lookup table)

    #[codec(compact)]
    pub timestamp: u32,                          // 4 bytes -> 1-5 bytes compact

    #[codec(compact)]
    pub block_number: u32,                       // 4 bytes -> 1-5 bytes compact
}
```

**Optimized Size**:
- **Minimum** (no parent): 32 + 1 + 1 + 1 + 2 + 2 + 2 = **41 bytes**
- **Typical** (with parent): 32 + 1 + 1 + 1 + 32 + 2 + 2 + 2 = **73 bytes**
- **Maximum**: **73 bytes**

**Savings**: ~70-200 bytes per record

### Phase 2D: Storage Key Optimization

**Current**: Blake2_128Concat hashing for storage keys
- Hash: 16 bytes
- Key (image_hash): 64 bytes (hex) or 32 bytes (binary)
- **Total**: 80 bytes (hex) or 48 bytes (binary)

**Optimized**: Use binary hash (32 bytes) instead of hex (64 bytes)
- Hash: 16 bytes
- Key: 32 bytes
- **Total**: 48 bytes

**Savings**: 32 bytes per record in storage keys

---

## Implementation Plan

### Step 1: Create Minimal Runtime Branch

```bash
git checkout -b optimization/minimal-runtime
```

### Step 2: Remove Unnecessary Pallets

**File**: `packages/registry/runtime/Cargo.toml`
```toml
# Remove dependencies:
# - pallet-balances
# - pallet-transaction-payment
# - pallet-sudo
# - pallet-democracy
# - pallet-collective
# - pallet-treasury
# - pallet-scheduler
# - pallet-preimage
```

**File**: `packages/registry/runtime/src/lib.rs`
- Remove pallet configurations
- Remove from `construct_runtime!` macro
- Simplify `SignedExtra` type

### Step 3: Optimize ImageRecord Structure

**File**: `packages/registry/pallets/birthmark/src/lib.rs`

1. **Add AuthorityRegistry**:
```rust
#[pallet::storage]
pub type AuthorityRegistry<T: Config> = StorageMap<
    _,
    Blake2_128Concat,
    u16,
    BoundedVec<u8, ConstU32<100>>,
    OptionQuery,
>;

#[pallet::storage]
pub type NextAuthorityId<T: Config> = StorageValue<_, u16, ValueQuery>;
```

2. **Optimize ImageRecord**:
```rust
#[derive(Clone, Encode, Decode, Eq, PartialEq, RuntimeDebug, TypeInfo, MaxEncodedLen)]
pub struct ImageRecord {
    pub image_hash: [u8; 32],              // Binary hash, not hex
    pub submission_type: SubmissionType,   // 1 byte
    pub modification_level: u8,            // 1 byte
    pub parent_image_hash: Option<[u8; 32]>, // 0 or 32 bytes
    pub authority_id: u16,                 // Lookup table index

    #[codec(compact)]
    pub timestamp: u32,                    // Compact encoding

    #[codec(compact)]
    pub block_number: u32,                 // Compact encoding
}
```

3. **Add helper function**:
```rust
pub fn register_or_get_authority(authority: Vec<u8>) -> Result<u16, Error<T>> {
    // Search for existing authority
    for (id, stored_authority) in AuthorityRegistry::<T>::iter() {
        if stored_authority.to_vec() == authority {
            return Ok(id);
        }
    }

    // Register new authority
    let new_id = NextAuthorityId::<T>::get();
    let bounded: BoundedVec<u8, ConstU32<100>> = authority
        .try_into()
        .map_err(|_| Error::<T>::AuthorityIdTooLong)?;

    AuthorityRegistry::<T>::insert(new_id, bounded);
    NextAuthorityId::<T>::put(new_id.saturating_add(1));

    Ok(new_id)
}
```

### Step 4: Implement Unsigned Transactions (Optional)

For maximum optimization, make submission server use unsigned inherent transactions:

```rust
#[pallet::validate_unsigned]
impl<T: Config> ValidateUnsigned for Pallet<T> {
    type Call = Call<T>;

    fn validate_unsigned(
        _source: TransactionSource,
        call: &Self::Call,
    ) -> TransactionValidity {
        match call {
            Call::submit_image_record { .. } => {
                // Validate call is from authorized submission server
                // (check IP, shared secret, or other mechanism)
                ValidTransaction::with_tag_prefix("BirthmarkSubmission")
                    .priority(u64::MAX)
                    .and_provides(/* unique identifier */)
                    .build()
            }
            _ => InvalidTransaction::Call.into(),
        }
    }
}
```

### Step 5: Measure Results

**Before Optimization**:
- Extrinsic size: ~380-400 bytes
- Storage per record: ~400-500 bytes

**After Optimization**:
- Extrinsic size: ~50-80 bytes (unsigned inherent)
- Storage per record: ~120-170 bytes

**Total Savings**: ~70-80% reduction

---

## Expected Results

### Storage Requirements (Optimized)

| Daily Volume | Annual Storage | Storage Cost/Year | VPS Cost/Month | Total/Year |
|--------------|----------------|-------------------|----------------|------------|
| 100K images  | 6.2 GB         | $1-2              | $10-15         | $120-180   |
| 1M images    | 62 GB          | $10-15            | $15-20         | $180-240   |
| 10M images   | 620 GB         | $100-150          | $30-40         | $360-480   |

### Economics for Journalism Institutions

**Per Node Operating Cost** (optimized):
- VPS: $10-20/month ($120-240/year)
- Storage: $1-10/month ($12-120/year)
- Bandwidth: $5-10/month ($60-120/year)
- **Total**: $200-500/year

**Comparison** (unoptimized):
- Storage: $50-100/month ($600-1200/year)
- VPS: $30-50/month ($360-600/year)
- **Total**: $1000-2000/year

**Savings**: 60-75% reduction in operating costs

---

## Migration Path

### Phase 1 → Phase 2 Transition

1. **Fork Chain State**: Export chain state before runtime upgrade
2. **Deploy Optimized Runtime**: Perform forkless runtime upgrade
3. **Migrate Data**: Convert hex hashes to binary, populate authority registry
4. **Verify**: Ensure all records accessible and valid
5. **Archive Old State**: Keep Phase 1 data for reference

### Backwards Compatibility

**API Changes**:
- Accept both hex and binary hashes (convert hex → binary internally)
- Map authority strings to IDs transparently
- Maintain existing RPC endpoints

**Example**:
```rust
pub fn submit_with_compatibility(
    image_hash_hex: String,  // Accept hex string
    authority_name: String,   // Accept string
    // ... other params
) -> DispatchResult {
    // Convert hex to binary
    let binary_hash = hex::decode(image_hash_hex)?;

    // Look up or register authority
    let authority_id = Self::register_or_get_authority(authority_name.into_bytes())?;

    // Call optimized function
    Self::submit_image_record_optimized(binary_hash, authority_id, ...)
}
```

---

## Risk Assessment

### Low Risk
- ✅ Removing unused pallets (democracy, treasury, etc.)
- ✅ Optimizing data structure encoding
- ✅ Authority ID lookup table

### Medium Risk
- ⚠️ Removing pallet_balances (requires account system changes)
- ⚠️ Removing transaction signatures (requires authorization mechanism)
- ⚠️ Changing hash format (hex → binary)

### Mitigation Strategies

1. **Testnet First**: Deploy all changes to testnet, run for 1 month
2. **Gradual Rollout**: Implement optimizations in stages
3. **Backwards Compatibility**: Support both old and new formats during transition
4. **Monitoring**: Track storage growth, extrinsic sizes, and node performance
5. **Rollback Plan**: Keep ability to revert to Phase 1 runtime if issues arise

---

## Success Metrics

### Technical Metrics
- [ ] Extrinsic size: <100 bytes per record
- [ ] Storage size: <150 bytes per record
- [ ] Transaction processing: <100ms per record
- [ ] Batch processing: 100 records in <1 second
- [ ] Zero data loss during migration

### Economic Metrics
- [ ] Node operating cost: <$500/year per institution
- [ ] Storage cost: <$200/year at 1M images/day
- [ ] 5x improvement in storage efficiency

### Operational Metrics
- [ ] Forkless upgrade successful
- [ ] All 20 nodes upgraded within 24 hours
- [ ] Zero downtime during migration
- [ ] All existing records queryable after upgrade

---

## Timeline

### Immediate (This Session)
1. ✅ Complete audit and analysis
2. 🔄 Create minimal runtime configuration
3. 🔄 Implement data structure optimizations
4. 🔄 Write migration tests

### Next Session
5. Deploy to local testnet
6. Benchmark and measure results
7. Document findings
8. Create Phase 2 deployment plan

### Future Phases
9. Deploy to multi-node testnet (3-5 nodes)
10. Run stress tests (1M+ records)
11. Production deployment planning
12. Multi-institutional rollout

---

## References

- [Substrate Storage Optimization Guide](https://docs.substrate.io/optimize/)
- [SCALE Codec Specification](https://docs.substrate.io/reference/scale-codec/)
- [Substrate Runtime Versioning](https://docs.substrate.io/maintain/runtime-upgrades/)
- Birthmark Phase 1 Architecture: `/home/user/Birthmark/CLAUDE.md`

---

**Document Version**: 1.0
**Last Updated**: 2026-01-08
**Next Review**: After Phase 2B implementation
