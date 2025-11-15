"""
Validation module for the SMA.

This module implements the core validation logic for verifying
camera authenticity without seeing image content.
"""

from .validator import validate_authentication_token, validate_batch

__all__ = [
    "validate_authentication_token",
    "validate_batch",
]
