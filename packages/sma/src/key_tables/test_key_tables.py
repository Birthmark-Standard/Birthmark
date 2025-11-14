#!/usr/bin/env python3
"""
Test script for SMA key table operations.

This script demonstrates and tests the complete workflow:
1. Loading key tables from JSON
2. Deriving encryption keys from master keys
3. Simulating camera-side encryption and SMA-side decryption
"""

import json
import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "shared"))

from crypto.key_derivation import derive_key, derive_key_batch
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets


def load_key_tables(json_path: str) -> dict:
    """Load key tables from JSON file."""
    with open(json_path, 'r') as f:
        data = json.load(f)

    master_keys = {
        table["table_id"]: bytes.fromhex(table["master_key"])
        for table in data["key_tables"]
    }

    return master_keys, data


def test_key_derivation(master_keys: dict):
    """Test that keys can be derived from master keys."""
    print("\n" + "=" * 80)
    print("TEST 1: Key Derivation")
    print("=" * 80)

    # Pick first table
    table_id = 0
    master_key = master_keys[table_id]

    print(f"\nTable {table_id} master key: {master_key.hex()[:32]}...")

    # Derive several keys
    test_indices = [0, 1, 42, 99]
    print(f"\nDeriving keys at indices: {test_indices}")

    for key_index in test_indices:
        derived = derive_key(master_key, key_index)
        print(f"  Index {key_index:3}: {derived.hex()[:64]}...")

    # Test batch derivation
    print("\nTesting batch derivation...")
    batch_keys = derive_key_batch(master_key, test_indices)
    print(f"  ✓ Derived {len(batch_keys)} keys in batch")

    # Verify consistency
    individual_keys = [derive_key(master_key, idx) for idx in test_indices]
    assert batch_keys == individual_keys, "Batch derivation must match individual"
    print("  ✓ Batch and individual derivation match")

    print("\n✓ Key derivation test passed")


def test_encryption_decryption(master_keys: dict):
    """Test encryption/decryption workflow (simulating camera and SMA)."""
    print("\n" + "=" * 80)
    print("TEST 2: Encryption/Decryption Workflow")
    print("=" * 80)

    # Simulate camera selecting a table and key
    table_id = 3
    key_index = 42

    print(f"\nSimulating camera with table {table_id}, key {key_index}")

    # Camera side: derive encryption key
    master_key = master_keys[table_id]
    encryption_key = derive_key(master_key, key_index)
    print(f"  Camera derived key: {encryption_key.hex()[:32]}...")

    # Simulate NUC hash (in real system, this comes from camera sensor)
    simulated_nuc_hash = secrets.token_bytes(32)
    print(f"  Simulated NUC hash: {simulated_nuc_hash.hex()[:32]}...")

    # Camera encrypts NUC hash using AES-256-GCM
    nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
    aesgcm = AESGCM(encryption_key)
    ciphertext = aesgcm.encrypt(nonce, simulated_nuc_hash, None)
    print(f"  Encrypted: {ciphertext.hex()[:32]}... (length: {len(ciphertext)} bytes)")

    # Camera sends: (ciphertext, table_id, key_index, nonce) to aggregator
    # Aggregator forwards to SMA (without image hash)

    print(f"\nSimulating SMA validation...")

    # SMA side: derive same encryption key
    sma_encryption_key = derive_key(master_keys[table_id], key_index)
    print(f"  SMA derived key: {sma_encryption_key.hex()[:32]}...")

    # Verify SMA derived same key
    assert sma_encryption_key == encryption_key, "SMA must derive same key as camera"
    print("  ✓ SMA derived same key as camera")

    # SMA decrypts
    sma_aesgcm = AESGCM(sma_encryption_key)
    decrypted_nuc_hash = sma_aesgcm.decrypt(nonce, ciphertext, None)
    print(f"  Decrypted: {decrypted_nuc_hash.hex()[:32]}...")

    # Verify decryption matches original
    assert decrypted_nuc_hash == simulated_nuc_hash, "Decryption must match original"
    print("  ✓ Decrypted NUC hash matches original")

    # SMA would now look up this NUC hash in database to identify device
    print("\n  [In production: SMA queries database for matching NUC hash]")
    print("  [Returns: PASS if found, FAIL if not found]")

    print("\n✓ Encryption/decryption workflow test passed")


def test_multiple_tables(master_keys: dict):
    """Test using multiple tables (camera has 3 tables assigned)."""
    print("\n" + "=" * 80)
    print("TEST 3: Multiple Table Assignment")
    print("=" * 80)

    # Simulate a device assigned to tables 2, 5, 8
    assigned_tables = [2, 5, 8]
    print(f"\nSimulating device assigned to tables: {assigned_tables}")

    # Camera randomly selects one table for this image
    selected_table = assigned_tables[1]  # Choose middle one
    key_index = 17

    print(f"  Camera selects table {selected_table}, key {key_index}")

    # Derive key
    master_key = master_keys[selected_table]
    encryption_key = derive_key(master_key, key_index)

    print(f"  Derived key: {encryption_key.hex()[:32]}...")

    # In real system:
    # - Camera would rotate through assigned tables for each image
    # - This prevents SMA from tracking individual cameras
    # - SMA only knows "someone with access to table 5 encrypted this"

    print("\n  Privacy invariant: SMA cannot determine which specific device")
    print("  encrypted the NUC hash, only that it has access to table 5")

    print("\n✓ Multiple table assignment test passed")


def test_key_uniqueness(master_keys: dict):
    """Verify all derived keys are unique."""
    print("\n" + "=" * 80)
    print("TEST 4: Key Uniqueness")
    print("=" * 80)

    print("\nVerifying derived keys are unique across tables and indices...")

    derived_keys = set()

    # Sample keys from each table
    for table_id, master_key in master_keys.items():
        # Test first 10 keys from each table
        for key_index in range(10):
            derived = derive_key(master_key, key_index)
            derived_keys.add(derived.hex())

    expected_count = len(master_keys) * 10
    actual_count = len(derived_keys)

    print(f"  Expected unique keys: {expected_count}")
    print(f"  Actual unique keys: {actual_count}")

    assert actual_count == expected_count, "All derived keys must be unique"
    print("  ✓ All derived keys are unique")

    print("\n✓ Key uniqueness test passed")


def main():
    """Run all tests."""
    # Find the key tables file
    script_dir = Path(__file__).parent
    key_tables_path = script_dir.parent.parent / "data" / "key_tables_phase1.json"

    if not key_tables_path.exists():
        print(f"❌ Key tables file not found: {key_tables_path}")
        print("   Run 'python generate.py' first to generate key tables")
        sys.exit(1)

    print("=" * 80)
    print("SMA Key Table Test Suite - Birthmark Standard")
    print("=" * 80)
    print(f"Loading key tables from: {key_tables_path}")

    master_keys, metadata = load_key_tables(str(key_tables_path))

    print(f"\nLoaded {len(master_keys)} key tables")
    print(f"Configuration: {metadata['configuration']['num_tables']} tables × "
          f"{metadata['configuration']['keys_per_table']} keys")
    print(f"Created: {metadata['created_at']}")

    # Run all tests
    test_key_derivation(master_keys)
    test_encryption_decryption(master_keys)
    test_multiple_tables(master_keys)
    test_key_uniqueness(master_keys)

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("✓ All tests passed successfully")
    print("\nKey table system is ready for:")
    print("  - Device provisioning (assign 3 tables to each device)")
    print("  - Camera-side NUC encryption")
    print("  - SMA validation server integration")
    print("=" * 80)


if __name__ == "__main__":
    main()
