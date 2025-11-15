"""
Shared types for Birthmark Standard.

This module exports core data structures used across all Birthmark components.
"""

from .submission import AuthenticationBundle
from .validation import ValidationRequest, ValidationResponse

__all__ = [
    "AuthenticationBundle",
    "ValidationRequest",
    "ValidationResponse",
]
