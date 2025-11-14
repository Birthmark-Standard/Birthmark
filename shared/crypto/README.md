# Shared Cryptographic Utilities

**Purpose:** Standardized cryptographic operations for the Birthmark system

## Overview

This directory contains all cryptographic primitives used across the Birthmark Standard. Centralizing these utilities ensures:
- Consistent implementation across packages
- Proper security practices
- Easy auditing and updates
- Prevention of cryptographic mistakes

## Files

### `hashing.py`

Standardized SHA-256 hashing:

```python
def compute_sha256(data: bytes) -> str:
    """
    Compute SHA-256 hash of data.

    Args:
        data: Raw bytes to hash

    Returns:
        64-character hex string
    """
    return hashlib.sha256(data).hexdigest()

def hash_image_data(bayer_array: np.ndarray) -> str:
    """
    Hash raw Bayer sensor data from camera.
    Ensures consistent byte ordering across platforms.
    """
    bayer_bytes = bayer_array.tobytes()
    return compute_sha256(bayer_bytes)
```

**Critical:** Byte ordering must be consistent across all platforms (camera, aggregator, verifier).

### `key_derivation.py`

HKDF (HMAC-based Key Derivation Function) for key table system:

```python
def derive_table_key(master_key: bytes, table_id: int, rotation_epoch: int) -> bytes:
    """
    Derive a 256-bit key from master key using HKDF.

    Args:
        master_key: 256-bit master key
        table_id: Table identifier (0-2499)
        rotation_epoch: Time-based rotation counter

    Returns:
        256-bit derived key
    """
    info = f"table_{table_id}_epoch_{rotation_epoch}".encode()
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=info
    ).derive(master_key)
```

**Purpose:** Allows key rotation without redistributing keys to cameras.

### `encryption.py`

AES-256-GCM encryption for NUC tokens:

```python
def encrypt_nuc_token(nuc_hash: bytes, key: bytes) -> tuple[bytes, bytes, bytes]:
    """
    Encrypt NUC hash with AES-256-GCM.

    Args:
        nuc_hash: 32-byte SHA-256 hash of NUC map
        key: 32-byte encryption key

    Returns:
        (ciphertext, nonce, auth_tag)
    """
    nonce = os.urandom(12)  # 96-bit nonce
    cipher = Cipher(
        algorithms.AES(key),
        modes.GCM(nonce)
    )
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(nuc_hash) + encryptor.finalize()
    return (ciphertext, nonce, encryptor.tag)

def decrypt_nuc_token(ciphertext: bytes, key: bytes, nonce: bytes, tag: bytes) -> bytes:
    """
    Decrypt NUC token with AES-256-GCM.

    Raises:
        InvalidTag: If authentication fails (tampered data)
    """
    cipher = Cipher(
        algorithms.AES(key),
        modes.GCM(nonce, tag)
    )
    decryptor = cipher.decryptor()
    return decryptor.update(ciphertext) + decryptor.finalize()
```

## Cryptographic Standards

### Hashing
- **Algorithm:** SHA-256
- **Library:** Python `hashlib` (uses OpenSSL backend)
- **Output:** 64 hex characters (32 bytes binary)

### Key Derivation
- **Algorithm:** HKDF-SHA256 (RFC 5869)
- **Master key:** 256-bit random
- **Derived keys:** 256-bit
- **Salt:** Optional (None for deterministic derivation)
- **Info:** Contextual string (table ID + epoch)

### Encryption
- **Algorithm:** AES-256-GCM
- **Key size:** 256 bits
- **Nonce:** 96 bits (random, unique per encryption)
- **Tag:** 128 bits (authentication)
- **Library:** `cryptography` (Python)

## Security Considerations

### Random Number Generation
All nonces and keys use `os.urandom()` which provides cryptographically secure randomness.

### Constant-Time Operations
Key comparison and validation use constant-time comparison to prevent timing attacks:

```python
import hmac

def constant_time_compare(a: bytes, b: bytes) -> bool:
    return hmac.compare_digest(a, b)
```

### Key Storage
- **Development:** Environment variables
- **Production:** Hardware Security Module (HSM)
- **Never:** Hard-coded in source code

### Error Handling
Cryptographic errors are never silently ignored:

```python
try:
    plaintext = decrypt_nuc_token(...)
except InvalidTag:
    # Authentication failed - possible tampering
    raise ValidationError("Token authentication failed")
```

## Performance Targets

- SHA-256 hashing (12MP image): <500ms on Raspberry Pi
- HKDF key derivation: <1ms
- AES-GCM encryption: <10ms
- AES-GCM decryption: <10ms

## Testing

```bash
cd shared/crypto
pytest tests/test_*.py
```

Test coverage includes:
- Correctness (known test vectors)
- Consistency (same input → same output)
- Error handling (invalid keys, tampered data)
- Performance benchmarks

## Dependencies

```python
# requirements.txt
cryptography>=41.0.0  # For AES-GCM, HKDF
```

## Security Auditing

**Important:** Any changes to cryptographic code require:
1. Security review by cryptography expert
2. Test vector validation
3. Performance benchmarking
4. Documentation update

## Known Limitations

- No post-quantum cryptography (future consideration)
- Single AES implementation (no algorithm agility)
- Key rotation requires coordination

## Related Documentation

- Security architecture: `docs/specs/Birthmark_Camera_Security_Architecture.md`
- Key table design: `docs/phase-plans/Birthmark_Phase_1-2_Plan_SMA.md`
