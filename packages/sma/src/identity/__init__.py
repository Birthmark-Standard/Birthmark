"""
Device identity management for the SMA.

This module handles device registration and lookup by NUC hash.
"""

from .device_lookup import (
    get_device_by_nuc_hash,
    get_device_by_serial,
    get_device_count,
    list_devices,
    register_device,
)

__all__ = [
    "get_device_by_serial",
    "get_device_by_nuc_hash",
    "register_device",
    "list_devices",
    "get_device_count",
]
