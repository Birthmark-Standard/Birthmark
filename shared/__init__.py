"""
Birthmark Standard - Shared Package

This package contains core data structures, cryptographic utilities, and protocol
definitions shared across all Birthmark components.

Modules:
    types: Core data structures (AuthenticationBundle, ValidationRequest, etc.)
    crypto: Cryptographic utilities (hashing, encryption, key derivation)
    protocols: API contracts and interface specifications

Example:
    >>> from shared.types import AuthenticationBundle
    >>> from shared.crypto import compute_sha256
    >>>
    >>> image_hash = compute_sha256(b"raw sensor data")
    >>> bundle = AuthenticationBundle(image_hash=image_hash, ...)
"""

__version__ = "0.1.0"
__author__ = "The Birthmark Standard Foundation"

__all__ = [
    "types",
    "crypto",
    "protocols",
]
