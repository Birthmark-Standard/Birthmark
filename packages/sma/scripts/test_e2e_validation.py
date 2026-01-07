#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
End-to-end test for camera token validation.

This script simulates the complete flow:
1. Camera generates encrypted NUC token
2. Token is submitted to SMA /validate endpoint
3. SMA decrypts and validates the token
4. Returns PASS/FAIL

This demonstrates the complete authentication protocol without
requiring a running FastAPI server.
"""

import sys
import secrets
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.key_tables.key_derivation import derive_encryption_key
from src.key_tables.table_manager import KeyTableManager
from src.identity.device_registry import DeviceRegistry, DeviceRegistration
from src.validation.token_validator import validate_camera_token
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_step(num, text):
    """Print formatted step."""
    print(f"\n[Step {num}] {text}")


def main():
    print_header("End-to-End Camera Token Validation Test")

    # Load actual SMA data
    data_dir = Path(__file__).parent.parent / "data"
    key_tables_path = data_dir / "key_tables.json"
    registry_path = data_dir / "device_registry.json"

    print_step(1, "Load SMA key tables and device registry")

    # Load key tables
    table_manager = KeyTableManager(
        total_tables=10,
        tables_per_device=3,
        storage_path=key_tables_path
    )

    if not key_tables_path.exists():
        print("  ✗ Key tables not found. Run: python scripts/setup_sma.py")
        return 1

    table_manager.load_from_file()
    print(f"  ✓ Loaded {len(table_manager.key_tables)} key tables")

    # Load device registry
    device_registry = DeviceRegistry(storage_path=registry_path)

    if not registry_path.exists():
        print("  ✗ Device registry not found. Run: python scripts/setup_sma.py")
        return 1

    device_registry.load_from_file()
    print(f"  ✓ Loaded {len(device_registry._registrations)} devices")

    # Find a test device
    test_devices = [d for d in device_registry._registrations.values()
                   if d.device_serial.startswith("TEST-CAMERA")]

    if not test_devices:
        print("  ✗ No test devices found. Run: python scripts/provision_device.py --serial TEST-CAMERA-001")
        return 1

    device = test_devices[0]
    print(f"  ✓ Using device: {device.device_serial}")
    print(f"    - NUC hash: {device.nuc_hash[:32]}...")
    print(f"    - Tables: {device.table_assignments}")

    print_step(2, "Camera side: Generate encrypted NUC token")

    # Select random table from device's assignments
    table_id = secrets.choice(device.table_assignments)
    key_index = secrets.randbelow(1000)

    print(f"  Selected table_id: {table_id}")
    print(f"  Selected key_index: {key_index}")

    # Derive encryption key (using master key from table)
    master_key = table_manager.key_tables[table_id]
    encryption_key = derive_encryption_key(master_key, key_index)
    print(f"  ✓ Derived encryption key: {encryption_key.hex()[:32]}...")

    # Encrypt NUC hash
    nuc_hash_bytes = bytes.fromhex(device.nuc_hash)
    nonce = secrets.token_bytes(12)

    aesgcm = AESGCM(encryption_key)
    ciphertext_with_tag = aesgcm.encrypt(nonce, nuc_hash_bytes, None)

    # Split ciphertext and auth tag
    ciphertext = ciphertext_with_tag[:-16]
    auth_tag = ciphertext_with_tag[-16:]

    print(f"  ✓ Encrypted NUC hash")
    print(f"    - Ciphertext: {ciphertext.hex()[:32]}...")
    print(f"    - Auth tag: {auth_tag.hex()}")
    print(f"    - Nonce: {nonce.hex()}")

    print_step(3, "SMA side: Validate encrypted token")

    # Validate token
    valid, message, validated_device = validate_camera_token(
        table_manager=table_manager,
        device_registry=device_registry,
        ciphertext=ciphertext.hex(),
        auth_tag=auth_tag.hex(),
        nonce=nonce.hex(),
        table_id=table_id,
        key_index=key_index
    )

    print_step(4, "Validation result")

    if valid:
        print(f"  ✓ VALIDATION PASSED")
        print(f"    - Status: {message}")
        print(f"    - Authenticated device: {validated_device.device_serial}")
        print(f"    - Device family: {validated_device.device_family}")
        print(f"    - Provisioned at: {validated_device.provisioned_at}")
        print()
        print("  🎉 End-to-end validation SUCCESSFUL!")
        print("  The camera authentication protocol is working correctly.")
        return 0
    else:
        print(f"  ✗ VALIDATION FAILED")
        print(f"    - Reason: {message}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
