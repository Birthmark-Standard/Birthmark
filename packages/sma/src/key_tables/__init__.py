"""
Key table management for the SMA.

This module handles generation and retrieval of the 2,500 master keys
used for HKDF-based key derivation.
"""

from .generator import (
    generate_master_keys,
    get_master_key,
    get_master_keys,
    populate_key_tables,
)

__all__ = [
    "generate_master_keys",
    "populate_key_tables",
    "get_master_key",
    "get_master_keys",
]
