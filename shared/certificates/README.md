# Birthmark Certificate Architecture

## Overview

The Birthmark system uses X.509 certificates with custom extensions to create self-contained authentication documents. This eliminates the need to send separate authentication fields and enables self-routing to the appropriate validation authorities.

## Certificate Types

### 1. Camera Certificate (Phase 1)

Issued by Manufacturer Authority (MA) during device provisioning.

**Standard X.509 Fields:**
- **Subject:** `CN={device_serial}, O={manufacturer_name}`
- **Issuer:** `CN={Manufacturer CA}`
- **Public Key:** Device ECDSA P-256 public key
- **Validity:** 10 years (typical camera lifespan)
- **Signature:** Manufacturer CA ECDSA signature

**Custom Extensions (OID: 1.3.6.1.4.1.60000.1.*):**

| Extension Name | OID | Type | Description |
|---------------|-----|------|-------------|
| manufacturerID | .1.1 | UTF8String | Manufacturer identifier (e.g., "sony_imaging") |
| maEndpoint | .1.2 | UTF8String | MA validation endpoint URL |
| encryptedNUC | .1.3 | OCTET STRING | AES-256-GCM encrypted NUC hash (60 bytes: 32 ciphertext + 12 nonce + 16 tag) |
| keyTableID | .1.4 | INTEGER | Key table ID (0-2499) |
| keyIndex | .1.5 | INTEGER | Key index within table (0-999) |
| deviceFamily | .1.6 | UTF8String | Device family (e.g., "Sony IMX477 12MP") |

### 2. Software Certificate (Phase 2)

Issued by Software Authority (SA) during app release signing.

**Standard X.509 Fields:**
- **Subject:** `CN={app_bundle_id}, O={developer_name}`
- **Issuer:** `CN={Software Authority CA}`
- **Public Key:** App signing key (ECDSA P-256)
- **Validity:** 1 year (app version lifespan)
- **Signature:** Software Authority CA ECDSA signature

**Custom Extensions (OID: 1.3.6.1.4.1.60000.2.*):**

| Extension Name | OID | Type | Description |
|---------------|-----|------|-------------|
| developerID | .2.1 | UTF8String | Developer identifier (e.g., "meta_platforms") |
| saEndpoint | .2.2 | UTF8String | SA validation endpoint URL |
| appIdentifier | .2.3 | UTF8String | App bundle ID (e.g., "com.instagram.ios") |
| versionString | .2.4 | UTF8String | App version (e.g., "312.0.0") |
| allowedVersions | .2.5 | SEQUENCE OF UTF8String | Allowed version strings for validation |

## OID Namespace

```
1.3.6.1.4.1.60000 (Birthmark Standard - placeholder PEN)
├── 1.* - Camera Certificate Extensions
│   ├── 1.1 - manufacturerID
│   ├── 1.2 - maEndpoint
│   ├── 1.3 - encryptedNUC
│   ├── 1.4 - keyTableID
│   ├── 1.5 - keyIndex
│   └── 1.6 - deviceFamily
│
└── 2.* - Software Certificate Extensions
    ├── 2.1 - developerID
    ├── 2.2 - saEndpoint
    ├── 2.3 - appIdentifier
    ├── 2.4 - versionString
    └── 2.5 - allowedVersions
```

**Note:** OID `1.3.6.1.4.1.60000` is a placeholder. Production deployment requires registering a Private Enterprise Number (PEN) with IANA.

## Certificate Bundle Format

Instead of sending individual authentication fields, devices send certificates:

```python
@dataclass
class CertificateBundle:
    """Authentication bundle containing certificates."""

    image_hash: str                    # SHA-256 of raw sensor data (64 hex chars)
    camera_cert: bytes                 # DER-encoded camera certificate
    software_cert: Optional[bytes]     # DER-encoded software cert (Phase 2)
    timestamp: int                     # Unix timestamp
    gps_hash: Optional[str]           # SHA-256 of GPS coordinates
    bundle_signature: bytes            # ECDSA signature over all fields
```

## Validation Flow

### Phase 1: Camera-Only Validation

```
1. Device creates bundle with camera_cert + image_hash
2. Blockchain node receives bundle
3. Node parses camera_cert → extracts maEndpoint
4. Node sends to MA: {camera_cert, image_hash}
5. MA validates:
   - Verify cert signature (is it valid manufacturer cert?)
   - Extract encryptedNUC from extensions
   - Extract keyTableID, keyIndex
   - Decrypt NUC hash
   - Compare to device registry
   - Return PASS/FAIL (never sees image_hash in validation logic)
6. Node stores image_hash on blockchain if PASS
```

### Phase 2: Camera + Software Validation

```
1. Device creates bundle with camera_cert + software_cert + image_hash
2. Blockchain node receives bundle
3. Node validates camera cert (as above)
4. Node parses software_cert → extracts saEndpoint
5. Node sends to SA: {software_cert, image_hash, versionString}
6. SA validates:
   - Verify cert signature (is it valid developer cert?)
   - Extract versionString from extensions
   - Compute versioned_hash = SHA-256(image_hash || versionString)
   - Check if versionString in allowedVersions
   - Return PASS/FAIL
7. Node stores image_hash on blockchain if BOTH pass
```

## Privacy Guarantees

### Camera Certificate Privacy

- **MA never sees image_hash:** Validation request includes cert + hash, but MA only decrypts and checks NUC against registry. The image hash is not used in validation logic.
- **Encrypted NUC:** NUC hash encrypted with AES-256-GCM using rotating keys
- **Key rotation:** Key tables allow periodic rotation without re-provisioning devices
- **No tracking:** Each submission uses same cert, but encrypted token prevents correlation

### Software Certificate Privacy

- **SA never sees raw image:** Only receives SHA-256 hash
- **Version binding:** Hash bound to specific app version, preventing replay across versions
- **Developer isolation:** Each developer runs their own SA, can't see other developers' images

## Certificate Lifecycle

### Camera Certificate

1. **Provisioning:** Device manufactured and provisioned with certificate
2. **Issuance:** MA signs certificate with 10-year validity
3. **Storage:** Certificate stored in device secure element
4. **Usage:** Certificate sent with every image capture
5. **Revocation:** MA maintains CRL for compromised devices
6. **Renewal:** Not typical (camera lifespan ~5-7 years)

### Software Certificate

1. **Development:** Developer builds app version
2. **Signing:** Developer signs app with private key
3. **SA Certification:** SA issues certificate for specific version(s)
4. **Distribution:** Certificate bundled with app
5. **Validation:** Certificate sent with every image capture
6. **Expiration:** 1-year validity, renewed with new app versions
7. **Revocation:** SA maintains CRL for vulnerable versions

## Implementation Notes

### Certificate Generation

Use `cryptography` library for Python:

```python
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

# Custom OID for Birthmark extensions
BIRTHMARK_OID_BASE = x509.ObjectIdentifier("1.3.6.1.4.1.60000")
CAMERA_MA_ENDPOINT = x509.ObjectIdentifier("1.3.6.1.4.1.60000.1.2")
CAMERA_ENCRYPTED_NUC = x509.ObjectIdentifier("1.3.6.1.4.1.60000.1.3")
# ... etc
```

### Certificate Parsing

Extract extensions using:

```python
cert = x509.load_der_x509_certificate(cert_bytes)
for ext in cert.extensions:
    if ext.oid == CAMERA_MA_ENDPOINT:
        ma_endpoint = ext.value.value.decode('utf-8')
```

### Certificate Validation

1. Verify signature chain (device cert → MA CA → root)
2. Check validity period
3. Check revocation status (CRL/OCSP)
4. Extract and validate extensions

## Security Considerations

### Certificate Pinning

- Blockchain nodes maintain list of trusted MA/SA root CAs
- Reject certificates from untrusted issuers
- Periodic updates to trust store

### Extension Validation

- Validate extension data types and ranges
- Reject malformed extensions
- Enforce maximum extension lengths

### Replay Prevention

- Timestamp validation (reject if >1 year old or future-dated)
- Per-block duplicate detection (same hash can't appear twice in batch)
- Historical duplicate detection (same hash can't appear on blockchain twice)

## Migration Path

### Phase 1 → Certificate Architecture

1. Update provisioning to generate certificates
2. Update camera code to send certificates
3. Update blockchain to parse certificates
4. Update SMA to accept certificate-based validation
5. Backward compatibility: Support both formats during transition

### Phase 2: Adding Software Validation

1. Create SSA infrastructure
2. Update mobile apps to include software certificates
3. Update blockchain to validate both certificate types
4. Enforce both validations for Phase 2+ submissions

## File Locations

- **Certificate utilities:** `shared/certificates/`
- **OID definitions:** `shared/certificates/oids.py`
- **Certificate builder:** `shared/certificates/builder.py`
- **Certificate parser:** `shared/certificates/parser.py`
- **Validation utilities:** `shared/certificates/validator.py`

## Testing

- Test certificate generation with valid/invalid extensions
- Test certificate parsing with malformed data
- Test validation with expired certificates
- Test validation with revoked certificates
- Test validation with untrusted CAs
- Test extraction of extensions
- Test routing to correct MA/SA endpoints

---

**Status:** Phase 1 implementation in progress
**Next:** Implement certificate builder and parser utilities
