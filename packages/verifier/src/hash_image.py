# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Image hashing utility for Birthmark verification.

Computes SHA-256 hash of image files to verify against blockchain.
"""

import hashlib
from pathlib import Path
from typing import Union
from PIL import Image
import io


def hash_image_file(image_path: Union[str, Path]) -> str:
    """
    Hash an image file using SHA-256.

    Args:
        image_path: Path to image file

    Returns:
        Hex string of SHA-256 hash (64 characters)
    """
    with open(image_path, 'rb') as f:
        image_data = f.read()

    return hashlib.sha256(image_data).hexdigest()


def hash_image_bytes(image_bytes: bytes) -> str:
    """
    Hash image bytes using SHA-256.

    Args:
        image_bytes: Raw image file bytes

    Returns:
        Hex string of SHA-256 hash (64 characters)
    """
    return hashlib.sha256(image_bytes).hexdigest()


def hash_image_pil(image: Image.Image, format: str = "JPEG") -> str:
    """
    Hash a PIL Image object.

    Args:
        image: PIL Image object
        format: Image format to save as before hashing (JPEG, PNG, etc.)

    Returns:
        Hex string of SHA-256 hash (64 characters)
    """
    # Convert PIL image to bytes
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    image_bytes = buffer.getvalue()

    return hash_image_bytes(image_bytes)


def verify_hash_format(image_hash: str) -> bool:
    """
    Verify that a hash string is valid SHA-256 format.

    Args:
        image_hash: Hash string to verify

    Returns:
        True if valid SHA-256 hex string (64 characters)
    """
    if len(image_hash) != 64:
        return False

    try:
        int(image_hash, 16)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python hash_image.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]

    if not Path(image_path).exists():
        print(f"Error: File not found: {image_path}")
        sys.exit(1)

    image_hash = hash_image_file(image_path)
    print(f"SHA-256 hash: {image_hash}")
