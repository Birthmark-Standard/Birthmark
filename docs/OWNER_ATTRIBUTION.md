# Owner Attribution System

## Overview

The Birthmark Owner Attribution System allows photographers to optionally include verifiable attribution in their authenticated photos. This feature provides a privacy-preserving way for photographers to prove ownership while maintaining the Birthmark Standard's core privacy guarantees.

## Architecture

### Three-Part System

1. **Image EXIF Metadata** (stays with the image)
   - Plaintext owner name (e.g., "Jane Smith", "jane@example.com")
   - Random 32-byte salt (base64-encoded)

2. **Blockchain Record** (permanent, public)
   - Hash of (owner name + salt)
   - No plaintext name or identifying information

3. **Verification** (anyone with the image file)
   - Extract name and salt from EXIF
   - Compute hash
   - Compare with blockchain record

### Privacy Properties

✅ **Each photo gets a unique hash** - Same photographer, different hash per image
✅ **Blockchain records are unlinkable** - Cannot correlate images without the file
✅ **Optional attribution** - Disabled by default, user must opt-in
✅ **No central tracking** - No single entity can link all photos from a photographer
✅ **Survives metadata stripping** - If EXIF is stripped, attribution is simply lost (not leaked)

## Usage

### 1. Configure Camera

```bash
cd packages/camera-pi
python -m camera_pi.config
```

Interactive prompts:
```
=== Owner Attribution Configuration ===

Owner attribution allows you to include verifiable attribution
in your photos using a hash-based system.

⚠ PRIVACY NOTE:
  - Owner name and random salt are stored in image EXIF
  - Only a hash of (name + salt) is stored on blockchain
  - Each photo gets a unique hash (even from same owner)
  - Blockchain records cannot be correlated without the image file

Enable owner attribution? (y/n): y

Enter owner name/identifier. This can be:
  - Your name (e.g., 'Jane Smith')
  - Email (e.g., 'jane@example.com')
  - Organization + name (e.g., 'Jane Smith - Reuters')

Owner name: Jane Smith - Reuters

✓ Owner attribution enabled
  Owner name: Jane Smith - Reuters

All future photos will include owner attribution.
```

Configuration is saved to `./data/camera_config.json`:

```json
{
  "owner_attribution": {
    "enabled": true,
    "owner_name": "Jane Smith - Reuters"
  }
}
```

### 2. Capture Photos

Once configured, all captured photos automatically include owner attribution:

```bash
python -m camera_pi capture --use-certificates
```

Output:
```
=== Capture #1 ===
ISP parameters: WB(R:1.25, B:1.15), Exp:+0.0, Sharp:0.5, NR:0.3
✓ Raw capture: (3040, 4056) in 0.245s
✓ Hash computed: a9d1dbb063ffd40e... in 0.089s
✓ Processed capture: (3040, 4056, 3)
✓ Processed hash: 29d6c8498815c58c...
✓ ISP variance: 0.0234
✓ Owner attribution: Jane Smith - Reuters
✓ Using embedded certificate (no token generation needed)
✓ Certificate bundle created (variance: 0.0234)
✓ Saved: IMG_1699564800.json
✓ Total time: 0.512s
```

### 3. Verify Attribution

Upload image to the Birthmark verifier:

```bash
curl -X POST http://localhost:8080/api/verify \
  -F "file=@IMG_1699564800.jpg"
```

Response:
```json
{
  "image_hash": "29d6c8498815c58cb274cb4878cd3f4f...",
  "verified": true,
  "modification_level": 1,
  "modification_display": "Validated (Camera ISP or Minor Software Edits)",
  "owner_hash": "7b2r4s91f3a8d6c2e5f7g9h1...",
  "owner_verified": true,
  "owner_name": "Jane Smith - Reuters",
  "message": "✅ Image verified on blockchain! Validated | Photo by: Jane Smith - Reuters"
}
```

## Technical Details

### Owner Hash Generation

```python
import hashlib
import secrets

# Generate random salt (32 bytes)
owner_salt = secrets.token_bytes(32)

# Compute owner_hash = SHA256(owner_name + owner_salt)
hash_input = owner_name.encode('utf-8') + owner_salt
owner_hash = hashlib.sha256(hash_input).hexdigest()
```

### EXIF Storage Format

**Artist Field**: Plaintext owner name
```
Artist: Jane Smith - Reuters
```

**Copyright Field**: Standard copyright notice
```
Copyright: © Jane Smith - Reuters
```

**UserComment Field**: Encoded salt
```
UserComment: BirthmarkOwnerSalt:aGVsbG8gd29ybGQgdGhpcyBpcyBhIHRlc3Q=...
```

### Blockchain Schema

```rust
pub struct ImageRecord<T: Config> {
    pub image_hash: BoundedVec<u8, T::MaxImageHashLength>,
    pub submission_type: SubmissionType,
    pub modification_level: u8,
    pub parent_image_hash: Option<BoundedVec<u8, T::MaxImageHashLength>>,
    pub authority_id: BoundedVec<u8, T::MaxAuthorityIdLength>,
    pub owner_hash: Option<BoundedVec<u8, T::MaxImageHashLength>>,  // NEW
    pub timestamp: T::Moment,
    pub block_number: BlockNumberFor<T>,
}
```

### Verification Algorithm

```python
def verify_owner_attribution(image_bytes, blockchain_owner_hash):
    # 1. Extract EXIF metadata
    owner_name = exif['Artist']
    owner_salt_b64 = exif['UserComment'].split(':')[1]
    owner_salt = base64.b64decode(owner_salt_b64)

    # 2. Compute hash
    computed_hash = SHA256(owner_name + owner_salt)

    # 3. Compare with blockchain
    if computed_hash == blockchain_owner_hash:
        return {"verified": True, "owner_name": owner_name}
    else:
        return {"verified": False, "warning": "Metadata tampered"}
```

## Privacy Analysis

### What Different Parties See

**Camera Manufacturer** (via Manufacturer Authority):
- ✅ One of their cameras authenticated a photo
- ❌ Which specific camera
- ❌ Owner name
- ❌ Owner hash
- ❌ Image content

**Submission Server**:
- ✅ Image hash
- ✅ Owner hash (if enabled)
- ❌ Owner name
- ❌ Which photos are from same owner (different hashes)
- ❌ Image content

**Blockchain** (public):
- ✅ Image hash
- ✅ Owner hash (if enabled)
- ❌ Owner name (need image file to verify)
- ❌ Which photos are from same owner
- ❌ Image content

**Public Verifier** (with image file):
- ✅ Owner name (from EXIF)
- ✅ Verification that name matches blockchain
- ❌ Other photos from same owner

### Privacy Guarantees

1. **Unlinkability**: Cannot determine if two images are from the same owner without having both image files
2. **Selective Disclosure**: Photographers choose which images to include owner attribution
3. **Revocability**: Can remove EXIF from images to remove attribution (blockchain record remains but can't be verified)
4. **No Enumeration**: Cannot list all photos from a specific owner on the blockchain
5. **No Profiling**: Cannot build a profile of a photographer's work from blockchain data alone

## Security Considerations

### Threats Mitigated

✅ **EXIF Stripping**: Attribution survives metadata loss via blockchain record
✅ **Name Tampering**: Verification fails if name is changed
✅ **Salt Tampering**: Verification fails if salt is changed
✅ **Hash Substitution**: Cannot substitute different owner_hash (blockchain is immutable)
✅ **Correlation Attacks**: Different hashes per image prevent linking

### Limitations

⚠ **EXIF Required**: If EXIF is stripped before verification, attribution cannot be verified (but also not falsified)
⚠ **No Anonymity**: Once verified, owner name is publicly visible to anyone with the image
⚠ **Salt Visibility**: Salt is visible in EXIF, but this is intentional (needed for verification)
⚠ **Social Graph Leakage**: If images are shared publicly, metadata can reveal social connections

## Use Cases

### Photojournalism

**Scenario**: Reuters photographer Jane Smith covers a news event

**Workflow**:
1. Enable owner attribution: "Jane Smith - Reuters"
2. Capture photos at the event
3. Submit photos to Reuters editor
4. Reuters publishes photos with EXIF intact
5. Public can verify: "Photo by: Jane Smith - Reuters"

**Benefits**:
- Proves photo came from authenticated Reuters camera
- Verifiable attribution to specific photographer
- Survives social media sharing if EXIF is preserved

### Citizen Journalism

**Scenario**: Activist documents human rights abuse

**Workflow**:
1. Disable owner attribution (privacy)
2. Capture photos
3. Submit to news organization
4. Organization can verify authenticity (no owner name)

**Benefits**:
- Proves photo is authentic
- No photographer attribution (protects activist)
- Cannot be used to identify photographer

### Commercial Photography

**Scenario**: Wedding photographer wants credit

**Workflow**:
1. Enable owner attribution: "sarah@photography.com"
2. Capture wedding photos
3. Deliver to clients with EXIF
4. Clients share photos online
5. Public can verify attribution

**Benefits**:
- Portfolio building (verifiable work samples)
- Copyright protection (provable authorship)
- Marketing (attribution survives sharing)

## Editing Software Integration

### Preserving Owner Attribution

When editing authenticated photos, software should:

1. **Read parent owner_hash** from blockchain
2. **Preserve EXIF fields** (read-only)
3. **Use same owner_hash** in child submission

```python
# Load parent image
parent_hash = blockchain.query(parent_image_hash)
parent_owner_hash = parent_hash.owner_hash

# Create child submission
child_submission = {
    "parent_image_hash": parent_image_hash,
    "owner_hash": parent_owner_hash,  # Preserve
    # ... other fields
}
```

### Privacy Note

Editing software should NOT allow modifying owner name or salt. These fields are read-only and tied to the parent image's authentication.

## API Reference

### Camera Configuration API

```python
from camera_pi.config import CameraConfig, configure_owner_attribution

# Load configuration
config = CameraConfig.load()

# Check if enabled
if config.owner_attribution.is_configured():
    print(f"Owner: {config.owner_attribution.owner_name}")

# Interactive configuration
configure_owner_attribution()

# Programmatic configuration
config.owner_attribution.enabled = True
config.owner_attribution.owner_name = "Jane Smith"
config.save()
```

### Owner Attribution API

```python
from camera_pi.owner_attribution import (
    generate_owner_metadata,
    verify_owner_metadata,
    write_owner_exif,
    read_owner_exif
)

# Generate metadata for a photo
metadata = generate_owner_metadata("Jane Smith")
# Returns: OwnerMetadata(owner_name, owner_salt, owner_hash)

# Verify metadata
valid = verify_owner_metadata(
    owner_name="Jane Smith",
    owner_salt=metadata.owner_salt,
    expected_hash=metadata.owner_hash
)

# Write to EXIF (requires piexif/PIL)
write_owner_exif("photo.jpg", metadata)

# Read from EXIF
owner_name, owner_salt = read_owner_exif("photo.jpg")
```

### Verifier API

```python
from verifier.owner_verification import verify_owner_attribution

# Verify owner attribution
result = verify_owner_attribution(
    image_bytes=open("photo.jpg", "rb").read(),
    blockchain_owner_hash="7b2r4s91f3..."
)

# Returns:
# {
#     'has_owner_metadata': True,
#     'owner_name': 'Jane Smith',
#     'owner_verified': True,
#     'warning': None
# }
```

## FAQ

**Q: Can I change the owner name after taking a photo?**
A: No. The owner_hash is computed during capture and stored on the blockchain (immutable). Changing the EXIF name will cause verification to fail.

**Q: What if I take photos with and without owner attribution?**
A: Each photo is independent. You can enable/disable attribution anytime via camera configuration.

**Q: Can someone steal my owner attribution?**
A: No. Each photo has a unique random salt. Even if someone copies your name and salt from one photo to another, the blockchain owner_hash won't match.

**Q: What if EXIF is stripped?**
A: The photo is still authenticated (blockchain has the image hash), but owner attribution cannot be verified. The blockchain still has the owner_hash, but without the EXIF name and salt, it cannot be verified.

**Q: Can I use a pseudonym?**
A: Yes. The owner name can be any string (name, email, handle, etc.). The system doesn't validate identity.

**Q: Does this leak my location?**
A: No. Owner attribution is separate from GPS metadata. GPS hashing is a separate optional feature.

**Q: Can news organizations remove my attribution?**
A: They can remove the EXIF metadata, but then attribution cannot be verified. The blockchain owner_hash remains, but can't be matched without the EXIF data.

## References

- [Birthmark Technical Architecture](./Birthmark_Standard_Technical_Architecture.docx)
- [Privacy Architecture](./PRIVACY.md)
- [Camera Security](./Birthmark_Camera_Security_Architecture.docx)
