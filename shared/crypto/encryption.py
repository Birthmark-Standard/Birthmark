"""
AES-256-GCM encryption utilities for Birthmark Standard.

NUC tokens are encrypted using AES-256-GCM with keys derived from the
SMA's key tables. This provides both confidentiality and authenticity.
"""

import os
from typing import Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def encrypt_nuc_token(nuc_hash: bytes, keys: list[bytes]) -> bytes:
    """
    Encrypt a NUC hash using triple AES-GCM encryption.

    The NUC hash is encrypted three times using three different keys derived
    from the device's assigned key tables. This provides strong security even
    if one key table is compromised.

    Args:
        nuc_hash: 32-byte SHA-256 hash of the device's NUC map
        keys: List of 3 derived encryption keys (32 bytes each)

    Returns:
        Encrypted token (nonce || ciphertext || tag for each layer)

    Example:
        >>> nuc_hash = hashlib.sha256(b"nuc_map_data").digest()
        >>> keys = [secrets.token_bytes(32) for _ in range(3)]
        >>> encrypted = encrypt_nuc_token(nuc_hash, keys)
    """
    if len(nuc_hash) != 32:
        raise ValueError(f"NUC hash must be 32 bytes, got {len(nuc_hash)}")

    if len(keys) != 3:
        raise ValueError(f"Expected 3 encryption keys, got {len(keys)}")

    for i, key in enumerate(keys):
        if len(key) != 32:
            raise ValueError(f"Key {i} must be 32 bytes, got {len(key)}")

    # Apply triple encryption
    plaintext = nuc_hash
    for key in keys:
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)  # 96-bit nonce for GCM
        ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=None)
        # Concatenate nonce + ciphertext+tag
        plaintext = nonce + ciphertext

    return plaintext


def decrypt_nuc_token(encrypted_token: bytes, keys: list[bytes]) -> bytes:
    """
    Decrypt a NUC token using triple AES-GCM decryption.

    Decrypts in reverse order of encryption (last key first).

    Args:
        encrypted_token: Encrypted token from camera
        keys: List of 3 derived encryption keys (32 bytes each)

    Returns:
        32-byte NUC hash

    Raises:
        cryptography.exceptions.InvalidTag: If decryption fails (wrong key or corrupted data)

    Example:
        >>> encrypted = encrypt_nuc_token(nuc_hash, keys)
        >>> decrypted = decrypt_nuc_token(encrypted, keys)
        >>> decrypted == nuc_hash
        True
    """
    if len(keys) != 3:
        raise ValueError(f"Expected 3 decryption keys, got {len(keys)}")

    for i, key in enumerate(keys):
        if len(key) != 32:
            raise ValueError(f"Key {i} must be 32 bytes, got {len(key)}")

    # Decrypt in reverse order
    ciphertext = encrypted_token
    for key in reversed(keys):
        aesgcm = AESGCM(key)

        # Extract nonce (first 12 bytes)
        if len(ciphertext) < 12:
            raise ValueError(f"Ciphertext too short: {len(ciphertext)} bytes")

        nonce = ciphertext[:12]
        encrypted_data = ciphertext[12:]

        # Decrypt (this includes authentication tag verification)
        ciphertext = aesgcm.decrypt(nonce, encrypted_data, associated_data=None)

    # Final result should be 32-byte NUC hash
    if len(ciphertext) != 32:
        raise ValueError(
            f"Decrypted data has unexpected length: {len(ciphertext)} bytes "
            "(expected 32 for SHA-256 hash)"
        )

    return ciphertext


def encrypt_single_layer(plaintext: bytes, key: bytes) -> Tuple[bytes, bytes]:
    """
    Perform a single layer of AES-256-GCM encryption.

    This is a lower-level utility used by encrypt_nuc_token but can also
    be used standalone for testing.

    Args:
        plaintext: Data to encrypt
        key: 32-byte encryption key

    Returns:
        Tuple of (nonce, ciphertext+tag)

    Example:
        >>> key = secrets.token_bytes(32)
        >>> nonce, ciphertext = encrypt_single_layer(b"secret data", key)
        >>> len(nonce)
        12
    """
    if len(key) != 32:
        raise ValueError(f"Key must be 32 bytes, got {len(key)}")

    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=None)

    return nonce, ciphertext


def decrypt_single_layer(nonce: bytes, ciphertext: bytes, key: bytes) -> bytes:
    """
    Perform a single layer of AES-256-GCM decryption.

    This is a lower-level utility used by decrypt_nuc_token but can also
    be used standalone for testing.

    Args:
        nonce: 12-byte nonce
        ciphertext: Encrypted data (includes authentication tag)
        key: 32-byte decryption key

    Returns:
        Decrypted plaintext

    Raises:
        cryptography.exceptions.InvalidTag: If authentication fails

    Example:
        >>> nonce, ciphertext = encrypt_single_layer(b"secret", key)
        >>> plaintext = decrypt_single_layer(nonce, ciphertext, key)
        >>> plaintext
        b'secret'
    """
    if len(key) != 32:
        raise ValueError(f"Key must be 32 bytes, got {len(key)}")

    if len(nonce) != 12:
        raise ValueError(f"Nonce must be 12 bytes, got {len(nonce)}")

    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, associated_data=None)
