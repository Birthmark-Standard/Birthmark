#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
AES-256-GCM encryption utilities for Birthmark Standard

This module provides authenticated encryption for NUC tokens sent from cameras
to the SMA (Simulated Manufacturer Authority). AES-256-GCM provides both
confidentiality and authentication in a single operation.

Critical: Encryption parameters (algorithm, key size, nonce size) must remain
stable. Any changes break compatibility with existing devices.
"""

import secrets
from typing import Tuple, NamedTuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag


class EncryptedToken(NamedTuple):
    """
    Result of encrypting a NUC token.

    Attributes:
        ciphertext: Encrypted NUC hash (32 bytes encrypted = 32 bytes output)
        nonce: 96-bit nonce used for this encryption (12 bytes)
        tag: 128-bit authentication tag (16 bytes) - included in ciphertext by AESGCM
    """
    ciphertext: bytes  # Includes authentication tag
    nonce: bytes


def encrypt_nuc_token(nuc_hash: bytes, encryption_key: bytes) -> EncryptedToken:
    """
    Encrypt NUC hash with AES-256-GCM.

    This function is used by cameras to encrypt their NUC hash before sending
    it to the aggregation server. The encryption ensures that only the SMA
    (which has the encryption key) can decrypt and validate the NUC hash.

    Args:
        nuc_hash: 32-byte SHA-256 hash of camera's NUC map
        encryption_key: 32-byte (256-bit) encryption key derived from key table

    Returns:
        EncryptedToken containing ciphertext (with embedded auth tag) and nonce

    Raises:
        ValueError: If nuc_hash or encryption_key have wrong length
        TypeError: If inputs are not bytes

    Example:
        >>> nuc_hash = b"0" * 32  # 32 bytes (simulated)
        >>> key = b"k" * 32  # 32 bytes
        >>> token = encrypt_nuc_token(nuc_hash, key)
        >>> len(token.ciphertext)  # 32 bytes data + 16 bytes tag
        48
        >>> len(token.nonce)
        12

    Security Notes:
        - Nonce is randomly generated for each encryption (never reused)
        - Authentication tag prevents tampering
        - Same plaintext + different nonce = different ciphertext (semantic security)
        - GCM mode provides both confidentiality and authenticity
    """
    # Validate inputs
    if not isinstance(nuc_hash, bytes):
        raise TypeError(f"nuc_hash must be bytes, got {type(nuc_hash).__name__}")

    if not isinstance(encryption_key, bytes):
        raise TypeError(f"encryption_key must be bytes, got {type(encryption_key).__name__}")

    if len(nuc_hash) != 32:
        raise ValueError(
            f"nuc_hash must be exactly 32 bytes (SHA-256), got {len(nuc_hash)} bytes"
        )

    if len(encryption_key) != 32:
        raise ValueError(
            f"encryption_key must be exactly 32 bytes (256 bits), got {len(encryption_key)} bytes"
        )

    # Generate random nonce (96 bits = 12 bytes for GCM)
    # CRITICAL: Nonce must be unique for each encryption with same key
    nonce = secrets.token_bytes(12)

    # Create AES-256-GCM cipher
    aesgcm = AESGCM(encryption_key)

    # Encrypt and authenticate
    # AESGCM automatically includes the authentication tag in the ciphertext
    # Output will be 48 bytes: 32 bytes (plaintext) + 16 bytes (tag)
    ciphertext = aesgcm.encrypt(nonce, nuc_hash, associated_data=None)

    return EncryptedToken(ciphertext=ciphertext, nonce=nonce)


def decrypt_nuc_token(
    ciphertext: bytes,
    nonce: bytes,
    encryption_key: bytes
) -> bytes:
    """
    Decrypt and authenticate NUC token with AES-256-GCM.

    This function is used by the SMA to decrypt NUC tokens received from the
    aggregation server. If decryption succeeds, the token is authentic (not
    tampered with) and was encrypted by a device with access to the encryption key.

    Args:
        ciphertext: Encrypted NUC hash (48 bytes: 32 data + 16 tag)
        nonce: 12-byte nonce used during encryption
        encryption_key: 32-byte encryption key derived from key table

    Returns:
        32-byte decrypted NUC hash

    Raises:
        InvalidTag: If authentication fails (tampered/corrupted data or wrong key)
        ValueError: If inputs have wrong length
        TypeError: If inputs are not bytes

    Example:
        >>> key = b"k" * 32
        >>> nuc_hash = b"0" * 32
        >>> token = encrypt_nuc_token(nuc_hash, key)
        >>> decrypted = decrypt_nuc_token(token.ciphertext, token.nonce, key)
        >>> decrypted == nuc_hash
        True

    Security Notes:
        - InvalidTag exception means either:
          1. Data was tampered with
          2. Wrong encryption key was used
          3. Data was corrupted in transit
        - Never ignore InvalidTag - it indicates a security issue
        - Decryption and authentication happen atomically
    """
    # Validate inputs
    if not isinstance(ciphertext, bytes):
        raise TypeError(f"ciphertext must be bytes, got {type(ciphertext).__name__}")

    if not isinstance(nonce, bytes):
        raise TypeError(f"nonce must be bytes, got {type(nonce).__name__}")

    if not isinstance(encryption_key, bytes):
        raise TypeError(f"encryption_key must be bytes, got {type(encryption_key).__name__}")

    if len(ciphertext) != 48:  # 32 bytes data + 16 bytes tag
        raise ValueError(
            f"ciphertext must be exactly 48 bytes (32 data + 16 tag), got {len(ciphertext)} bytes"
        )

    if len(nonce) != 12:
        raise ValueError(f"nonce must be exactly 12 bytes (96 bits), got {len(nonce)} bytes")

    if len(encryption_key) != 32:
        raise ValueError(
            f"encryption_key must be exactly 32 bytes (256 bits), got {len(encryption_key)} bytes"
        )

    # Create AES-256-GCM cipher with same key
    aesgcm = AESGCM(encryption_key)

    # Decrypt and verify authentication tag
    # Will raise InvalidTag if:
    # - Data was tampered with
    # - Wrong key used
    # - Wrong nonce used
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
        return plaintext
    except InvalidTag:
        # Re-raise with more context
        raise InvalidTag(
            "Token authentication failed. Possible causes: "
            "(1) tampered data, (2) wrong encryption key, (3) wrong nonce"
        )


def generate_encryption_key() -> bytes:
    """
    Generate a cryptographically secure 256-bit encryption key.

    This is used for testing or when master keys need to be generated.
    In production, keys are derived from master keys using HKDF.

    Returns:
        32 bytes (256 bits) of cryptographically secure random data

    Example:
        >>> key = generate_encryption_key()
        >>> len(key)
        32

    Security Notes:
        - Uses secrets.token_bytes() which is cryptographically secure
        - Never use random.randbytes() or similar - not cryptographically secure
        - Keys should be stored securely (environment variables, HSM, key management)
    """
    return secrets.token_bytes(32)


def validate_encryption_key(key: bytes) -> bool:
    """
    Validate that a key is suitable for AES-256-GCM.

    Args:
        key: Key to validate

    Returns:
        True if key is valid, False otherwise

    Example:
        >>> good_key = generate_encryption_key()
        >>> validate_encryption_key(good_key)
        True
        >>> bad_key = b"too short"
        >>> validate_encryption_key(bad_key)
        False
    """
    if not isinstance(key, bytes):
        return False

    if len(key) != 32:
        return False

    # All 32-byte keys are valid for AES-256
    # (but all-zeros is weak, though technically valid)
    return True


def benchmark_encryption(iterations: int = 1000) -> dict:
    """
    Benchmark encryption/decryption performance.

    This is useful for verifying that encryption meets performance targets
    on specific hardware (e.g., Raspberry Pi).

    Args:
        iterations: Number of encrypt/decrypt cycles to run

    Returns:
        Dictionary with benchmark results

    Example:
        >>> results = benchmark_encryption(1000)
        >>> print(f"Encrypt: {results['encrypt_us_per_op']:.1f}µs per operation")
        >>> print(f"Decrypt: {results['decrypt_us_per_op']:.1f}µs per operation")
    """
    import time

    # Generate test data
    key = generate_encryption_key()
    nuc_hash = secrets.token_bytes(32)

    # Benchmark encryption
    start = time.perf_counter()
    tokens = []
    for _ in range(iterations):
        token = encrypt_nuc_token(nuc_hash, key)
        tokens.append(token)
    encrypt_time = time.perf_counter() - start

    # Benchmark decryption
    start = time.perf_counter()
    for token in tokens:
        decrypt_nuc_token(token.ciphertext, token.nonce, key)
    decrypt_time = time.perf_counter() - start

    return {
        'iterations': iterations,
        'encrypt_total_ms': encrypt_time * 1000,
        'encrypt_us_per_op': (encrypt_time / iterations) * 1_000_000,
        'decrypt_total_ms': decrypt_time * 1000,
        'decrypt_us_per_op': (decrypt_time / iterations) * 1_000_000,
        'encrypt_meets_target': (encrypt_time / iterations) < 0.01,  # <10ms
        'decrypt_meets_target': (decrypt_time / iterations) < 0.01,  # <10ms
    }


if __name__ == "__main__":
    print("=" * 80)
    print("Birthmark Encryption Utilities - Test Vectors")
    print("=" * 80)

    # Test 1: Basic encryption/decryption
    print("\nTest 1: Basic Encryption/Decryption")
    key = generate_encryption_key()
    nuc_hash = b"0" * 32  # Simulated NUC hash
    print(f"  Key: {key.hex()[:32]}...")
    print(f"  NUC hash: {nuc_hash.hex()[:32]}...")

    token = encrypt_nuc_token(nuc_hash, key)
    print(f"  Ciphertext: {token.ciphertext.hex()[:32]}... ({len(token.ciphertext)} bytes)")
    print(f"  Nonce: {token.nonce.hex()} ({len(token.nonce)} bytes)")

    decrypted = decrypt_nuc_token(token.ciphertext, token.nonce, key)
    print(f"  Decrypted: {decrypted.hex()[:32]}...")
    print(f"  Match: {decrypted == nuc_hash}")

    # Test 2: Nonce uniqueness
    print("\nTest 2: Nonce Uniqueness (Semantic Security)")
    token1 = encrypt_nuc_token(nuc_hash, key)
    token2 = encrypt_nuc_token(nuc_hash, key)
    print(f"  Same plaintext + same key = different ciphertext")
    print(f"  Token 1 nonce: {token1.nonce.hex()}")
    print(f"  Token 2 nonce: {token2.nonce.hex()}")
    print(f"  Nonces differ: {token1.nonce != token2.nonce}")
    print(f"  Ciphertexts differ: {token1.ciphertext != token2.ciphertext}")

    # Test 3: Authentication (tampering detection)
    print("\nTest 3: Authentication (Tampering Detection)")
    token = encrypt_nuc_token(nuc_hash, key)

    # Tamper with ciphertext
    tampered = bytearray(token.ciphertext)
    tampered[0] ^= 0x01  # Flip one bit
    tampered = bytes(tampered)

    try:
        decrypt_nuc_token(tampered, token.nonce, key)
        print("  ✗ FAILED: Tampered data was accepted")
    except InvalidTag:
        print("  ✓ PASSED: Tampered data rejected (InvalidTag)")

    # Test 4: Wrong key detection
    print("\nTest 4: Wrong Key Detection")
    wrong_key = generate_encryption_key()
    try:
        decrypt_nuc_token(token.ciphertext, token.nonce, wrong_key)
        print("  ✗ FAILED: Wrong key was accepted")
    except InvalidTag:
        print("  ✓ PASSED: Wrong key rejected (InvalidTag)")

    # Test 5: Input validation
    print("\nTest 5: Input Validation")
    try:
        encrypt_nuc_token(b"too short", key)
        print("  ✗ FAILED: Short NUC hash accepted")
    except ValueError as e:
        print(f"  ✓ PASSED: Short NUC hash rejected ({str(e)[:40]}...)")

    try:
        encrypt_nuc_token(nuc_hash, b"short key")
        print("  ✗ FAILED: Short key accepted")
    except ValueError as e:
        print(f"  ✓ PASSED: Short key rejected ({str(e)[:40]}...)")

    # Test 6: Key validation
    print("\nTest 6: Key Validation")
    print(f"  Valid key: {validate_encryption_key(key)}")
    print(f"  Invalid (short): {validate_encryption_key(b'short')}")
    print(f"  Invalid (not bytes): {validate_encryption_key('string')}")

    # Performance benchmark
    print(f"\n" + "=" * 80)
    print("Performance Benchmark")
    print("=" * 80)
    results = benchmark_encryption(1000)
    print(f"\n{results['iterations']} encrypt/decrypt operations:")
    print(f"  Encryption:")
    print(f"    Total: {results['encrypt_total_ms']:.1f}ms")
    print(f"    Per operation: {results['encrypt_us_per_op']:.1f}µs")
    print(f"    Meets <10ms target: {'✓ YES' if results['encrypt_meets_target'] else '✗ NO'}")
    print(f"  Decryption:")
    print(f"    Total: {results['decrypt_total_ms']:.1f}ms")
    print(f"    Per operation: {results['decrypt_us_per_op']:.1f}µs")
    print(f"    Meets <10ms target: {'✓ YES' if results['decrypt_meets_target'] else '✗ NO'}")

    print("\n" + "=" * 80)
    print("✓ All encryption utilities ready for use")
    print("=" * 80)
