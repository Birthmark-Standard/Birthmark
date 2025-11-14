# Verifier Package

**Phase:** Phase 1
**Status:** In Development
**Purpose:** Client-side image verification

## Overview

The verifier package provides tools for end-users to verify whether an image has been authenticated by the Birthmark Standard. It hashes images client-side and queries the aggregation server and blockchain for verification.

## Key Principle

**Trust but Verify:** Users should be able to independently verify images without trusting the aggregator's database alone. The verifier checks both the aggregator API and the blockchain for confirmation.

## Key Components

### `src/hash_image.py`

Client-side image hashing:
- Accepts image file path
- Computes SHA-256 hash
- Handles different image formats
- **For Phase 1:** Raw Bayer data hashing (matching camera)
- **For Phase 2:** Processed image hashing (matching iOS app)

### `src/query_blockchain.py`

Blockchain verification:
- Queries aggregation server for Merkle proof
- Verifies Merkle proof against blockchain
- Confirms image hash inclusion in batch
- Returns verification result with timestamp

### `web/`

Simple web interface for verification:
- Upload image file
- Display verification status
- Show blockchain transaction link
- Show timestamp and batch information

## Verification Flow

```
1. User uploads image
   ↓
2. Verifier computes SHA-256 hash
   ↓
3. Query aggregator: GET /api/v1/verify/{hash}
   ↓
4. Receive Merkle proof and batch ID
   ↓
5. Query blockchain smart contract
   ↓
6. Verify Merkle proof matches blockchain Merkle root
   ↓
7. Display result: VERIFIED or NOT FOUND
```

## Two-Level Verification

### Level 1: Aggregator Database (Fast)
- Query aggregator API
- Get immediate response
- Trust aggregator record

### Level 2: Blockchain Proof (Trustless)
- Retrieve Merkle proof from aggregator
- Query blockchain for batch Merkle root
- Independently verify proof
- **No trust required in aggregator**

## Usage

### Command Line

```bash
cd packages/verifier
pip install -r requirements.txt

# Hash an image
python src/hash_image.py path/to/image.jpg

# Verify an image
python src/query_blockchain.py path/to/image.jpg
```

### Web Interface

```bash
cd packages/verifier/web
python -m http.server 8080
# Open http://localhost:8080
```

## Output Format

```json
{
  "image_hash": "a1b2c3d4...",
  "verified": true,
  "timestamp": 1732000000,
  "batch_id": 42,
  "merkle_proof": ["hash1", "hash2", "hash3"],
  "blockchain_tx": "0x...",
  "confirmation_time": "2024-11-13T10:30:00Z",
  "verification_level": "blockchain"
}
```

### Verification Levels

- **`"blockchain"`** - Merkle proof verified on-chain (highest trust)
- **`"aggregator"`** - Found in aggregator database (requires trust)
- **`"not_found"`** - Image not authenticated

## Security Considerations

- Hash computation must match camera exactly
- Merkle proof verification prevents aggregator fraud
- Direct blockchain query removes aggregator as single point of trust
- Users should verify blockchain explorer link independently

## Performance

- Hash computation: <1 second for typical images
- API query: <100ms response time
- Blockchain verification: <2 seconds total
- Web interface: <3 seconds end-to-end

## Future Enhancements

- Browser extension for automatic verification
- Social media integration (verify before sharing)
- Mobile verification app
- Batch verification tool for journalists
- AI-generated image detection (complementary check)

## Phase 2 Updates

When iOS app launches:
- Support processed image hashing (not raw sensor)
- Detect image format and apply correct hashing method
- Warn users about re-encoded images (may fail verification)

## Development

```bash
cd packages/verifier
pip install -r requirements.txt
pytest tests/
```

## Related Documentation

- Verification flow diagram: `docs/architecture/verification_flow.png`
- API specification: `shared/protocols/camera_to_aggregator.yaml`
- Smart contract verification: `packages/contracts/contracts/BirthmarkRegistry.sol`

## Integration Examples

### Python

```python
from verifier import hash_image, verify_blockchain

image_hash = hash_image("photo.jpg")
result = verify_blockchain(image_hash)
print(f"Verified: {result['verified']}")
```

### JavaScript (Web)

```javascript
const formData = new FormData();
formData.append('image', fileInput.files[0]);

fetch('/api/verify', {
  method: 'POST',
  body: formData
})
.then(res => res.json())
.then(data => console.log('Verified:', data.verified));
```

---

*This verifier is a critical component for user trust in the Birthmark system.*
