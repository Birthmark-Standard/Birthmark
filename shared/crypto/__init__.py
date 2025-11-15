"""
Birthmark Standard - Cryptographic Utilities

This module provides all cryptographic operations used in the Birthmark system:
- SHA-256 hashing for images, NUC maps, and GPS coordinates
- HKDF-SHA256 key derivation for key table system
- AES-256-GCM authenticated encryption for NUC tokens

All cryptographic implementations are centralized here to ensure:
- Consistent security across all components
- Easy auditing and updates
- Prevention of cryptographic mistakes

Modules:
    hashing: SHA-256 hash functions
    key_derivation: HKDF-based key derivation
    encryption: AES-256-GCM authenticated encryption

Example Usage:
    >>> from shared.crypto import compute_sha256, derive_key, encrypt_nuc_token
    >>>
    >>> # Hash image data
    >>> image_hash = compute_sha256(b"raw sensor data")
    >>>
    >>> # Derive encryption key
    >>> master_key = bytes.fromhex("00" * 32)
    >>> encryption_key = derive_key(master_key, key_index=42)
    >>>
    >>> # Encrypt NUC token
    >>> nuc_hash = compute_sha256(b"nuc data")
    >>> token = encrypt_nuc_token(nuc_hash.encode(), encryption_key)
"""

__version__ = "0.1.0"
__author__ = "The Birthmark Standard Foundation"

# Import hashing utilities
from .hashing import (
    compute_sha256,
    compute_sha256_binary,
    hash_image_data,
    hash_gps_coordinates,
    hash_nuc_map,
    verify_hash_format,
    constant_time_compare,
    benchmark_hashing,
)

# Import key derivation utilities
from .key_derivation import (
    derive_key,
    derive_key_batch,
    verify_key_derivation_consistency,
)

# Import encryption utilities
from .encryption import (
    EncryptedToken,
    encrypt_nuc_token,
    decrypt_nuc_token,
    generate_encryption_key,
    validate_encryption_key,
    benchmark_encryption,
)

# Define public API
__all__ = [
    # Hashing
    "compute_sha256",
    "compute_sha256_binary",
    "hash_image_data",
    "hash_gps_coordinates",
    "hash_nuc_map",
    "verify_hash_format",
    "constant_time_compare",
    "benchmark_hashing",
    # Key Derivation
    "derive_key",
    "derive_key_batch",
    "verify_key_derivation_consistency",
    # Encryption
    "EncryptedToken",
    "encrypt_nuc_token",
    "decrypt_nuc_token",
    "generate_encryption_key",
    "validate_encryption_key",
    "benchmark_encryption",
]
