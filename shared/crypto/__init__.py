"""
Cryptographic utilities for Birthmark Standard.

This module provides standardized implementations of:
- SHA-256 hashing
- HKDF key derivation
- AES-256-GCM encryption/decryption
"""

from .encryption import (
    decrypt_nuc_token,
    decrypt_single_layer,
    encrypt_nuc_token,
    encrypt_single_layer,
)
from .hashing import compute_sha256, compute_sha256_bytes, verify_hash_format
from .key_derivation import derive_key_from_master, derive_multiple_keys

__all__ = [
    # Hashing
    "compute_sha256",
    "compute_sha256_bytes",
    "verify_hash_format",
    # Key derivation
    "derive_key_from_master",
    "derive_multiple_keys",
    # Encryption
    "encrypt_nuc_token",
    "decrypt_nuc_token",
    "encrypt_single_layer",
    "decrypt_single_layer",
]
