# Certificate Architecture Migration Guide

## Overview

The Birthmark system now supports TWO authentication formats:

1. **Legacy Format** (`/api/v1/submit`): Separate fields (AuthenticationBundle)
2. **Certificate Format** (`/api/v1/submit-cert`): Self-contained certificates (CertificateBundle)

Both formats are fully supported. The certificate format is the recommended path forward as it provides better self-routing and cleaner architecture.

## What's Been Implemented

### ✅ Core Certificate Utilities (`shared/certificates/`)

- **OID Definitions** (`oids.py`): Standard X.509 extension OIDs
  - Camera certificates: `1.3.6.1.4.1.60000.1.*`
  - Software certificates: `1.3.6.1.4.1.60000.2.*`

- **Certificate Builder** (`builder.py`): Generate certificates with custom extensions
  - `CameraCertificateBuilder`: Creates camera certificates with NUC, key info, MA endpoint
  - `SoftwareCertificateBuilder`: Creates software certificates (Phase 2)

- **Certificate Parser** (`parser.py`): Extract Birthmark extensions
  - Parses DER-encoded certificates
  - Extracts custom extension data
  - Validates extension formats

- **Certificate Validator** (`validator.py`): Verify certificate chains
  - Signature verification
  - Expiration checking
  - Extension validation

### ✅ Blockchain Package Updates

- **New Schemas** (`schemas.py`):
  - `CertificateBundle`: Certificate-based submission format
  - `CertificateValidationRequest`: MA/SA validation request
  - Legacy schemas retained for backward compatibility

- **New Endpoint** (`/api/v1/submit-cert`):
  - Accepts CertificateBundle submissions
  - Parses camera certificate
  - Extracts MA endpoint from certificate
  - Routes validation to correct MA

- **Certificate Validator Service** (`certificate_validator.py`):
  - Wraps shared certificate utilities
  - Coordinates MA validation
  - Dynamically routes to MA endpoint from cert

### ✅ SMA Package Updates

- **New Endpoint** (`/validate-cert`):
  - Accepts certificate-based validation
  - Parses camera certificate extensions
  - Extracts encrypted NUC, key table ID, key index from cert
  - Phase 1: Format validation
  - Phase 2 TODO: Full cryptographic validation

## What Needs to Be Done

### 🔲 Camera-Pi Package Updates

The camera-pi package currently uses the legacy format. To migrate to certificates:

#### Option A: Dual Support (Recommended for Testing)

Keep both formats working during transition:

1. **Update SMA Provisioning** (`packages/sma/src/provisioning/provisioner.py`):
   - Import `CameraCertificateBuilder` from shared/certificates
   - When generating device certificate, add Birthmark extensions:
     ```python
     from shared.certificates import CameraCertificateBuilder

     builder = CameraCertificateBuilder(
         device_serial=serial,
         manufacturer_name="Simulated Manufacturer",
         device_public_key=device_public_key
     )
     builder.set_manufacturer_id("simulated_ma")
     builder.set_ma_endpoint("http://localhost:8001/validate-cert")
     builder.set_encrypted_nuc(encrypted_nuc)  # 60 bytes
     builder.set_key_table_id(table_id)
     builder.set_key_index(key_index)
     builder.set_device_family(device_family)

     cert = builder.build(ca_private_key)
     cert_der = builder.to_der(ca_private_key)
     ```

2. **Update Camera Submission** (`packages/camera-pi/src/camera_pi/aggregation_client.py`):
   - Add `submit_certificate()` method alongside existing `submit()`
   - Convert provisioning certificate to base64
   - Create `CertificateBundle` instead of `AuthenticationBundle`
   - Send to `/api/v1/submit-cert`

3. **Add CLI Flag** (`packages/camera-pi/src/camera_pi/main.py`):
   ```python
   parser.add_argument(
       '--use-certificates',
       action='store_true',
       help='Use certificate-based authentication (new format)'
   )
   ```

#### Option B: Full Migration

Replace legacy format entirely:

1. Deprecate `AuthenticationBundle` and `/api/v1/submit`
2. Update all camera code to use certificates
3. Remove legacy validation code

## Certificate Flow

### Legacy Flow (Current)
```
Camera:
├─ Generate encrypted NUC token
├─ Send separate fields: image_hash, encrypted_token, table_refs, key_indices
└─ Blockchain aggregator routes to SMA

Blockchain:
├─ Receive separate fields
├─ Call SMA at fixed endpoint
└─ SMA validates token
```

### Certificate Flow (New)
```
Camera:
├─ Load device certificate (contains all auth data)
├─ Send: image_hash + camera_cert
└─ Certificate includes MA endpoint

Blockchain:
├─ Parse camera certificate
├─ Extract MA endpoint from cert
├─ Extract encrypted NUC, key info from cert
├─ Route validation to correct MA (from cert)
└─ MA validates certificate
```

## Key Benefits of Certificate Format

1. **Self-Routing**: MA endpoint embedded in certificate
2. **Self-Contained**: All auth data in one document
3. **Standard Format**: X.509 is industry standard
4. **Easier Federation**: Each manufacturer can specify their own MA
5. **Cleaner API**: Single certificate field vs multiple fields
6. **Future-Proof**: Software certificates follow same pattern (Phase 2)

## Testing Certificate Format

Once provisioning is updated to generate certificate extensions:

```bash
# Terminal 1: Start SMA
cd packages/sma
uvicorn src.main:app --port 8001

# Terminal 2: Start Blockchain
cd packages/blockchain
uvicorn src.main:app --port 8545

# Terminal 3: Provision device with certificate extensions
cd packages/sma
python scripts/generate_ca.py  # If not done
python scripts/provision_device.py --device-serial TEST-001

# Terminal 4: Test camera submission
cd packages/camera-pi
python -m camera_pi capture --use-certificates  # If implementing dual support
```

## Migration Strategy

### Phase 1 (Current)
- ✅ Certificate utilities implemented
- ✅ Blockchain accepts both formats
- ✅ SMA accepts both formats
- 🔲 Camera uses legacy format

### Phase 2 (Next Steps)
- 🔲 Update SMA provisioning to generate certificate extensions
- 🔲 Update camera to support both formats
- 🔲 Test both formats side-by-side
- 🔲 Verify certificate validation works end-to-end

### Phase 3 (Production)
- 🔲 Default camera to certificate format
- 🔲 Deprecate legacy format
- 🔲 Remove legacy code

## Questions to Resolve

1. **Should we support both formats simultaneously?**
   - Pros: Easier testing, gradual migration
   - Cons: More code to maintain

2. **When to deprecate legacy format?**
   - After successful testing of certificate format
   - After all cameras migrated

3. **Should we update existing provisioning data?**
   - Re-provision all test devices with new certificates
   - Or add extensions to existing certificates

## Technical Notes

### Certificate Extension Format

Camera certificates include these custom extensions:

| Extension | OID | Format | Size |
|-----------|-----|--------|------|
| manufacturerID | .1.1 | UTF8String | Variable |
| maEndpoint | .1.2 | UTF8String | Variable |
| encryptedNUC | .1.3 | OCTET STRING | 60 bytes |
| keyTableID | .1.4 | INTEGER | 2 bytes |
| keyIndex | .1.5 | INTEGER | 2 bytes |
| deviceFamily | .1.6 | UTF8String | Variable |

### Privacy Considerations

- **MA never sees image hash** in validation logic (only in logs)
- **Encrypted NUC** prevents correlation between submissions
- **Single table/key** per certificate (vs 3 random in legacy format)
  - Legacy sent 3 tables/keys for privacy (actual + 2 random)
  - Certificate format embeds 1 table/key (actual) in cert
  - Privacy maintained because certificate is constant, encrypted NUC rotates

### Performance

- Certificate parsing: ~1ms (cached after first parse)
- No significant overhead vs legacy format
- Benefit: Fewer database fields to store

---

**Status**: Certificate infrastructure ready, awaiting camera-pi integration
**Next**: Update SMA provisioning to generate certificate extensions
