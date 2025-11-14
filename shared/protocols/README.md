# Shared Protocols

**Purpose:** API contracts and interface specifications (source of truth)

## Overview

This directory contains the canonical definitions of all APIs and interfaces in the Birthmark system. These specifications are the **source of truth** that all implementations must follow.

## Files

### `camera_to_aggregator.yaml`

OpenAPI 3.0 specification for the Camera → Aggregator API.

**Endpoints:**
- `POST /api/v1/submit` - Submit authentication bundle
- `GET /api/v1/health` - Health check

**Example:**
```yaml
openapi: 3.0.0
info:
  title: Birthmark Aggregation API
  version: 1.0.0
paths:
  /api/v1/submit:
    post:
      summary: Submit authentication bundle from camera
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AuthenticationBundle'
      responses:
        '202':
          description: Accepted for processing
```

### `aggregator_to_sma.yaml`

OpenAPI 3.0 specification for the Aggregator → SMA validation API.

**Endpoints:**
- `POST /api/v1/validate` - Validate camera authenticity

**Critical Privacy Requirement:**
This API spec **must not** include `image_hash` in any request. The SMA validates camera authenticity, not image content.

**Example:**
```yaml
paths:
  /api/v1/validate:
    post:
      summary: Validate camera authentication token
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                encrypted_token:
                  type: string
                  format: byte
                table_references:
                  type: array
                  items:
                    type: integer
                # NOTE: NO image_hash property
```

### `aggregator_to_chain.py`

Python wrapper for zkSync smart contract ABI.

**Functions:**
```python
class BirthmarkRegistryClient:
    def __init__(self, contract_address: str, rpc_url: str):
        """Initialize connection to BirthmarkRegistry contract"""
        pass

    def post_batch(self, merkle_root: str, image_count: int) -> str:
        """
        Post a new batch to blockchain.

        Args:
            merkle_root: 64-char hex string
            image_count: Number of images in batch

        Returns:
            Transaction hash (0x...)
        """
        pass

    def verify_inclusion(
        self,
        batch_id: int,
        image_hash: str,
        proof: List[str],
        leaf_index: int
    ) -> bool:
        """
        Verify Merkle proof on-chain.

        Returns:
            True if proof is valid, False otherwise
        """
        pass

    def get_batch(self, batch_id: int) -> dict:
        """
        Retrieve batch information.

        Returns:
            {
                'merkle_root': str,
                'image_count': int,
                'timestamp': int,
                'aggregator': str
            }
        """
        pass
```

## Protocol Versioning

### Version Strategy
- API version in URL path: `/api/v1/submit`
- Major version bumps for breaking changes
- Minor updates maintain backward compatibility

### Current Version: v1
- Initial protocol
- All endpoints return JSON
- Authentication via device signatures

### Future Versions
- v2: May add batch submission for cameras
- v3: May add federated aggregator support

## OpenAPI Usage

### Generating Client Libraries

```bash
# Python client
openapi-generator-cli generate \
  -i camera_to_aggregator.yaml \
  -g python \
  -o generated/python-client

# TypeScript client
openapi-generator-cli generate \
  -i camera_to_aggregator.yaml \
  -g typescript-fetch \
  -o generated/ts-client
```

### Validation

```bash
# Validate OpenAPI specs
openapi-generator-cli validate -i camera_to_aggregator.yaml
openapi-generator-cli validate -i aggregator_to_sma.yaml
```

### Documentation Generation

```bash
# Generate human-readable docs
redoc-cli bundle camera_to_aggregator.yaml -o api-docs.html
```

## Smart Contract ABI

The `aggregator_to_chain.py` wrapper uses the contract ABI from:
```
packages/contracts/artifacts/BirthmarkRegistry.json
```

**Auto-generation:**
When contracts are compiled, the Python wrapper should be regenerated:

```bash
cd packages/contracts
npx hardhat compile
python scripts/generate_abi_wrapper.py > ../../shared/protocols/aggregator_to_chain.py
```

## Testing

### Contract Testing
```bash
# Test that implementations match specs
cd shared/protocols
pytest tests/test_protocol_compliance.py
```

### Mock Servers
Use OpenAPI specs to generate mock servers for testing:

```bash
# Run mock aggregator
prism mock camera_to_aggregator.yaml

# Run mock SMA
prism mock aggregator_to_sma.yaml
```

## Development Workflow

1. **Design API changes in OpenAPI specs first**
2. **Review specs for privacy/security concerns**
3. **Validate specs with OpenAPI tools**
4. **Generate client/server stubs**
5. **Implement against stubs**
6. **Test compliance with contract tests**

## Privacy Checklist

Before merging any protocol changes:

- [ ] Verify SMA never receives image hashes
- [ ] Verify aggregator cannot track individual cameras
- [ ] Verify no PII in API logs
- [ ] Verify no metadata beyond hash/timestamp
- [ ] Verify encryption of sensitive fields

## Related Documentation

- API design: `docs/phase-plans/Birthmark_Phase_1_Plan_Aggregation_Server.md`
- Smart contract: `packages/contracts/contracts/BirthmarkRegistry.sol`
- Type definitions: `shared/types/`

## Tools

Recommended tools for working with protocols:

- **OpenAPI Generator:** Client/server code generation
- **Redoc:** API documentation
- **Prism:** Mock API servers
- **Spectral:** API linting
- **Swagger UI:** Interactive API explorer

---

*All protocol changes must maintain backward compatibility or provide migration path.*
