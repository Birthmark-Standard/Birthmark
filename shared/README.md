# Shared Package

**Purpose:** Common code shared across all Birthmark packages
**Language:** Python (with OpenAPI specs for protocols)

## Overview

The shared package contains core data structures, cryptographic utilities, and API protocol definitions used throughout the Birthmark Standard system. This ensures consistency and prevents code duplication across packages.

## Directory Structure

### `types/`
Core data structures and type definitions:
- `submission.py` - AuthenticationBundle (camera → aggregator)
- `validation.py` - ValidationRequest/Response (aggregator ↔ SMA)
- `merkle.py` - Merkle tree and proof structures

### `crypto/`
Shared cryptographic utilities:
- `hashing.py` - Standardized SHA-256 implementation
- `key_derivation.py` - HKDF for key table rotation
- `encryption.py` - AES-256-GCM for NUC token encryption

### `protocols/`
API contracts (source of truth for all interfaces):
- `camera_to_aggregator.yaml` - OpenAPI spec for submission API
- `aggregator_to_sma.yaml` - OpenAPI spec for validation API
- `aggregator_to_chain.py` - Smart contract ABI wrapper

## Usage

All packages should import from shared rather than duplicating code:

```python
# Good
from shared.types import AuthenticationBundle
from shared.crypto import compute_sha256

# Bad
# Copying cryptographic functions into local package
```

## Type Definitions

All shared types use Python dataclasses with type hints for clarity and IDE support.

## Cryptographic Standards

All cryptographic implementations in shared/ follow:
- FIPS 140-2 compliant algorithms
- Constant-time operations where applicable
- Secure random number generation
- Proper error handling

## Protocol Versioning

API protocols use semantic versioning:
- `/api/v1/submit` - Current version
- Future versions maintain backward compatibility or provide migration path

## Testing

Shared utilities have comprehensive unit tests:

```bash
cd shared
pytest tests/
```

## Development Guidelines

1. **All changes require tests** - 100% coverage target
2. **Breaking changes require major version bump**
3. **Document all cryptographic assumptions**
4. **Use type hints for all functions**
5. **Keep dependencies minimal**

## Dependencies

Minimal external dependencies:
- `cryptography` - For AES-GCM, HKDF, and hashing
- `pydantic` - For data validation
- `pyyaml` - For protocol spec parsing

## Related Documentation

- Security architecture: `docs/specs/Birthmark_Camera_Security_Architecture.md`
- Type system design: See individual README files in subdirectories
