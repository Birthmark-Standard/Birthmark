"""
Birthmark Standard - Core Data Types

This module defines all data structures used throughout the Birthmark system.
Centralizing types ensures consistency and makes it easy to maintain API contracts.

Modules:
    submission: Camera submission data structures (AuthenticationBundle, etc.)
    validation: SMA validation data structures (ValidationRequest, etc.)
    merkle: Merkle tree and proof structures

Example Usage:
    >>> from shared.types import AuthenticationBundle, ValidationRequest, MerkleProof
    >>>
    >>> # Create authentication bundle
    >>> bundle = AuthenticationBundle(
    ...     image_hash="a" * 64,
    ...     encrypted_nuc_token="b" * 96,
    ...     nonce="c" * 24,
    ...     table_references=[0, 500, 1000],
    ...     key_indices=[0, 500, 999],
    ...     timestamp=1732000000
    ... )
    >>>
    >>> # Create validation request
    >>> request = ValidationRequest(
    ...     encrypted_nuc_hash="b" * 96,
    ...     table_id=42,
    ...     key_index=123,
    ...     nonce="c" * 24
    ... )
"""

__version__ = "0.1.0"
__author__ = "The Birthmark Standard Foundation"

# Import submission types
from .submission import (
    AuthenticationBundle,
    SubmissionResponse,
)

# Import validation types
from .validation import (
    ValidationRequest,
    ValidationResponse,
)

# Import merkle types
from .merkle import (
    MerkleProof,
    BatchInfo,
    VerificationResult,
)

# Define public API
__all__ = [
    # Submission types
    "AuthenticationBundle",
    "SubmissionResponse",
    # Validation types
    "ValidationRequest",
    "ValidationResponse",
    # Merkle types
    "MerkleProof",
    "BatchInfo",
    "VerificationResult",
]
