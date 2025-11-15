"""
Key table management module for Birthmark SMA.

Handles key derivation and table assignment.
"""

from .key_derivation import (
    derive_encryption_key,
    verify_key_derivation,
    KeyDerivationManager,
    generate_test_vectors,
    validate_implementation,
    HKDF_CONTEXT
)

from .table_manager import (
    KeyTable,
    KeyTableManager,
    Phase2DatabaseTableManager
)

__all__ = [
    "derive_encryption_key",
    "verify_key_derivation",
    "KeyDerivationManager",
    "generate_test_vectors",
    "validate_implementation",
    "HKDF_CONTEXT",
    "KeyTable",
    "KeyTableManager",
    "Phase2DatabaseTableManager",
]
