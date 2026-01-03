"""
Owner attribution system for Birthmark Protocol.

Implements hash-based owner attribution with EXIF metadata storage.
Provides privacy-preserving photographer attribution that survives metadata stripping.
"""

import hashlib
import secrets
import base64
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class OwnerMetadata:
    """
    Owner metadata for a single image.

    Contains both plaintext data (for EXIF) and hash (for blockchain).
    """
    owner_name: str  # Plaintext name/identifier (stored in EXIF)
    owner_salt: bytes  # Random 32-byte salt (stored in EXIF, base64-encoded)
    owner_hash: str  # SHA-256 hash of (owner_name + owner_salt) (stored on blockchain)


def generate_owner_metadata(owner_name: str) -> OwnerMetadata:
    """
    Generate owner attribution metadata for an image.

    Creates a random salt and computes the owner hash. Each image gets
    a unique salt, ensuring blockchain records cannot be correlated.

    Args:
        owner_name: Owner name/identifier (e.g., "Jane Smith", "jane@example.com")

    Returns:
        OwnerMetadata with name, salt, and hash

    Example:
        >>> metadata = generate_owner_metadata("Jane Smith")
        >>> len(metadata.owner_salt)
        32
        >>> len(metadata.owner_hash)
        64
    """
    if not owner_name or not owner_name.strip():
        raise ValueError("Owner name cannot be empty")

    # Generate cryptographically secure random salt (32 bytes)
    owner_salt = secrets.token_bytes(32)

    # Compute owner_hash = SHA256(owner_name + owner_salt)
    hash_input = owner_name.encode('utf-8') + owner_salt
    owner_hash = hashlib.sha256(hash_input).hexdigest()

    return OwnerMetadata(
        owner_name=owner_name,
        owner_salt=owner_salt,
        owner_hash=owner_hash
    )


def verify_owner_metadata(
    owner_name: str,
    owner_salt: bytes,
    expected_hash: str
) -> bool:
    """
    Verify that owner name and salt match the expected hash.

    Used during verification to check if EXIF metadata has been tampered with.

    Args:
        owner_name: Owner name from EXIF
        owner_salt: Owner salt from EXIF (decoded from base64)
        expected_hash: Owner hash from blockchain record

    Returns:
        True if hash matches, False if tampered

    Example:
        >>> metadata = generate_owner_metadata("Jane Smith")
        >>> verify_owner_metadata(metadata.owner_name, metadata.owner_salt, metadata.owner_hash)
        True
        >>> verify_owner_metadata("Wrong Name", metadata.owner_salt, metadata.owner_hash)
        False
    """
    # Compute hash from provided name and salt
    hash_input = owner_name.encode('utf-8') + owner_salt
    computed_hash = hashlib.sha256(hash_input).hexdigest()

    # Constant-time comparison to prevent timing attacks
    return secrets.compare_digest(computed_hash, expected_hash)


def encode_salt_for_exif(salt: bytes) -> str:
    """
    Encode salt as base64 string for EXIF storage.

    Args:
        salt: Raw salt bytes (32 bytes)

    Returns:
        Base64-encoded string
    """
    return base64.b64encode(salt).decode('utf-8')


def decode_salt_from_exif(salt_b64: str) -> bytes:
    """
    Decode salt from EXIF base64 string.

    Args:
        salt_b64: Base64-encoded salt string from EXIF

    Returns:
        Raw salt bytes

    Raises:
        ValueError: If salt is not valid base64 or wrong length
    """
    try:
        salt = base64.b64decode(salt_b64)
        if len(salt) != 32:
            raise ValueError(f"Salt must be 32 bytes, got {len(salt)}")
        return salt
    except Exception as e:
        raise ValueError(f"Invalid salt encoding: {e}")


def write_owner_exif(image_path: str, metadata: OwnerMetadata) -> None:
    """
    Write owner attribution metadata to image EXIF.

    Stores plaintext owner name and base64-encoded salt in EXIF fields.
    These fields can be read by anyone with the image file to verify
    attribution against the blockchain.

    Args:
        image_path: Path to image file
        metadata: OwnerMetadata to write

    Note:
        This function requires piexif or pillow library.
        Implementation depends on image format (JPEG, PNG, etc.)
    """
    try:
        import piexif
        from PIL import Image

        # Load existing EXIF
        img = Image.open(image_path)
        exif_dict = piexif.load(img.info.get('exif', b''))

        # Add owner attribution fields to EXIF
        # Using ImageDescription and Copyright fields as they're widely supported
        exif_dict['0th'][piexif.ImageIFD.Artist] = metadata.owner_name.encode('utf-8')
        exif_dict['0th'][piexif.ImageIFD.Copyright] = f"© {metadata.owner_name}".encode('utf-8')

        # Store salt in UserComment (supports arbitrary data)
        salt_b64 = encode_salt_for_exif(metadata.owner_salt)
        exif_comment = f"BirthmarkOwnerSalt:{salt_b64}".encode('utf-8')
        exif_dict['Exif'][piexif.ExifIFD.UserComment] = exif_comment

        # Write EXIF back to image
        exif_bytes = piexif.dump(exif_dict)
        img.save(image_path, exif=exif_bytes)

        print(f"✓ Owner attribution written to EXIF")
        print(f"  Owner: {metadata.owner_name}")
        print(f"  Hash: {metadata.owner_hash[:16]}...")

    except ImportError:
        print("⚠ piexif/PIL not available - EXIF writing skipped")
        print("  Install: pip install piexif pillow")
    except Exception as e:
        print(f"⚠ Failed to write EXIF: {e}")


def read_owner_exif(image_path: str) -> Optional[Tuple[str, bytes]]:
    """
    Read owner attribution metadata from image EXIF.

    Extracts owner name and salt from EXIF fields.

    Args:
        image_path: Path to image file

    Returns:
        Tuple of (owner_name, owner_salt) if present, None otherwise
    """
    try:
        import piexif
        from PIL import Image

        img = Image.open(image_path)
        exif_dict = piexif.load(img.info.get('exif', b''))

        # Read owner name from Artist field
        artist_bytes = exif_dict['0th'].get(piexif.ImageIFD.Artist)
        if not artist_bytes:
            return None

        owner_name = artist_bytes.decode('utf-8')

        # Read salt from UserComment
        user_comment = exif_dict['Exif'].get(piexif.ExifIFD.UserComment)
        if not user_comment:
            return None

        comment_str = user_comment.decode('utf-8')
        if not comment_str.startswith('BirthmarkOwnerSalt:'):
            return None

        salt_b64 = comment_str.split(':', 1)[1]
        owner_salt = decode_salt_from_exif(salt_b64)

        return (owner_name, owner_salt)

    except ImportError:
        print("⚠ piexif/PIL not available - EXIF reading skipped")
        return None
    except Exception as e:
        print(f"⚠ Failed to read EXIF: {e}")
        return None


if __name__ == "__main__":
    # Test owner attribution system
    print("=== Owner Attribution Test ===\n")

    # Generate metadata
    owner_name = "Jane Smith - Reuters"
    print(f"Owner: {owner_name}\n")

    # Generate 3 different images from same owner
    print("Generating metadata for 3 photos from same owner:")
    for i in range(3):
        metadata = generate_owner_metadata(owner_name)
        print(f"\nPhoto {i+1}:")
        print(f"  Owner name: {metadata.owner_name}")
        print(f"  Owner salt: {encode_salt_for_exif(metadata.owner_salt)[:20]}...")
        print(f"  Owner hash: {metadata.owner_hash}")

        # Verify
        verified = verify_owner_metadata(
            metadata.owner_name,
            metadata.owner_salt,
            metadata.owner_hash
        )
        print(f"  Verification: {'✓ PASS' if verified else '✗ FAIL'}")

    print("\n✓ Each photo has a unique hash (privacy preserved)")
