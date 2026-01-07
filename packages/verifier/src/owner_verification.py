# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Owner attribution verification for Birthmark images.

Extracts owner metadata from EXIF and verifies against blockchain owner_hash.
"""

import hashlib
import base64
from typing import Optional, Tuple, Dict


def extract_owner_from_exif(image_bytes: bytes) -> Optional[Tuple[str, bytes]]:
    """
    Extract owner attribution from image EXIF metadata.

    Args:
        image_bytes: Raw image file bytes

    Returns:
        Tuple of (owner_name, owner_salt) if present, None otherwise
    """
    try:
        import piexif
        from PIL import Image
        from io import BytesIO

        # Load image from bytes
        img = Image.open(BytesIO(image_bytes))
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
        owner_salt = base64.b64decode(salt_b64)

        if len(owner_salt) != 32:
            return None

        return (owner_name, owner_salt)

    except ImportError:
        # piexif/PIL not available - skip owner verification
        return None
    except Exception:
        # EXIF reading failed - skip owner verification
        return None


def verify_owner_attribution(
    image_bytes: bytes,
    blockchain_owner_hash: Optional[str]
) -> Dict[str, any]:
    """
    Verify owner attribution from image EXIF against blockchain record.

    Args:
        image_bytes: Raw image file bytes
        blockchain_owner_hash: Owner hash from blockchain record (if present)

    Returns:
        Dictionary with verification result:
        {
            'has_owner_metadata': bool,
            'owner_name': Optional[str],
            'owner_verified': Optional[bool],
            'warning': Optional[str]
        }
    """
    # Extract owner metadata from EXIF
    exif_data = extract_owner_from_exif(image_bytes)

    if not exif_data:
        # No owner metadata in EXIF
        return {
            'has_owner_metadata': False,
            'owner_name': None,
            'owner_verified': None,
            'warning': None
        }

    owner_name, owner_salt = exif_data

    # Compute hash from EXIF data
    hash_input = owner_name.encode('utf-8') + owner_salt
    computed_hash = hashlib.sha256(hash_input).hexdigest()

    # Check if blockchain has owner hash
    if blockchain_owner_hash is None:
        # EXIF has owner data but blockchain doesn't - suspicious
        return {
            'has_owner_metadata': True,
            'owner_name': owner_name,
            'owner_verified': False,
            'warning': 'Owner metadata found in EXIF but not in blockchain record (added after authentication)'
        }

    # Verify hash matches
    if computed_hash.lower() == blockchain_owner_hash.lower():
        # Verified!
        return {
            'has_owner_metadata': True,
            'owner_name': owner_name,
            'owner_verified': True,
            'warning': None
        }
    else:
        # Hash mismatch - tampered
        return {
            'has_owner_metadata': True,
            'owner_name': owner_name,
            'owner_verified': False,
            'warning': 'Owner metadata has been tampered with (hash mismatch)'
        }


if __name__ == "__main__":
    # Test owner verification
    print("=== Owner Verification Test ===\n")
    print("This module verifies owner attribution from EXIF metadata.")
    print("Run from verifier web app to verify real images.")
