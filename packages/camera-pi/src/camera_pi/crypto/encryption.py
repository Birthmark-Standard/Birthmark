# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
AES-256-GCM encryption for NUC tokens.

Encrypts NUC hash with derived encryption keys for SMA validation.
"""

import secrets
from dataclasses import dataclass
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass
class EncryptedData:
    """
    Result of AES-256-GCM encryption.

    The ciphertext and auth_tag are combined in AESGCM output,
    but we separate them for clarity in the API.
    """
    ciphertext: bytes  # Encrypted plaintext
    auth_tag: bytes    # 16-byte authentication tag
    nonce: bytes       # 12-byte nonce (must be unique per encryption)

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary with hex-encoded values."""
        return {
            "ciphertext": self.ciphertext.hex(),
            "auth_tag": self.auth_tag.hex(),
            "nonce": self.nonce.hex()
        }


def encrypt_aes_gcm(
    plaintext: bytes,
    key: bytes,
    nonce: bytes | None = None
) -> EncryptedData:
    """
    Encrypt data with AES-256-GCM.

    Args:
        plaintext: Data to encrypt (e.g., 32-byte NUC hash)
        key: 256-bit (32 bytes) encryption key
        nonce: Optional 12-byte nonce (generated if None)

    Returns:
        EncryptedData with ciphertext, auth_tag, and nonce

    Raises:
        ValueError: If key is not 32 bytes

    Example:
        >>> key = secrets.token_bytes(32)
        >>> plaintext = b"test data"
        >>> encrypted = encrypt_aes_gcm(plaintext, key)
        >>> len(encrypted.nonce)
        12
        >>> len(encrypted.auth_tag)
        16
    """
    if len(key) != 32:
        raise ValueError(f"Key must be 32 bytes, got {len(key)}")

    # Generate random nonce if not provided
    if nonce is None:
        nonce = secrets.token_bytes(12)
    elif len(nonce) != 12:
        raise ValueError(f"Nonce must be 12 bytes, got {len(nonce)}")

    # Encrypt with AES-256-GCM
    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(
        nonce,
        plaintext,
        None  # No associated data
    )

    # Split ciphertext and auth tag
    # AESGCM appends 16-byte auth tag to ciphertext
    ciphertext = ciphertext_with_tag[:-16]
    auth_tag = ciphertext_with_tag[-16:]

    return EncryptedData(
        ciphertext=ciphertext,
        auth_tag=auth_tag,
        nonce=nonce
    )


def decrypt_aes_gcm(
    ciphertext: bytes,
    auth_tag: bytes,
    nonce: bytes,
    key: bytes
) -> bytes:
    """
    Decrypt data with AES-256-GCM.

    Useful for testing encryption/decryption round-trip.
    SMA performs the actual decryption for validation.

    Args:
        ciphertext: Encrypted data
        auth_tag: 16-byte authentication tag
        nonce: 12-byte nonce from encryption
        key: 256-bit (32 bytes) encryption key

    Returns:
        Decrypted plaintext

    Raises:
        ValueError: If key/nonce/tag are wrong size
        cryptography.exceptions.InvalidTag: If authentication fails

    Example:
        >>> key = secrets.token_bytes(32)
        >>> plaintext = b"test data"
        >>> encrypted = encrypt_aes_gcm(plaintext, key)
        >>> decrypted = decrypt_aes_gcm(
        ...     encrypted.ciphertext,
        ...     encrypted.auth_tag,
        ...     encrypted.nonce,
        ...     key
        ... )
        >>> decrypted == plaintext
        True
    """
    if len(key) != 32:
        raise ValueError(f"Key must be 32 bytes, got {len(key)}")
    if len(nonce) != 12:
        raise ValueError(f"Nonce must be 12 bytes, got {len(nonce)}")
    if len(auth_tag) != 16:
        raise ValueError(f"Auth tag must be 16 bytes, got {len(auth_tag)}")

    # Combine ciphertext and auth tag
    ciphertext_with_tag = ciphertext + auth_tag

    # Decrypt with AES-256-GCM
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, None)

    return plaintext
