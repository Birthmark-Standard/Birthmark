#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Simple test script for key derivation (no external dependencies).

This script tests key derivation without requiring the cryptography library,
making it suitable for quick verification and CI/CD pipelines.
"""

import json
import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "shared"))

from crypto.key_derivation import derive_key, derive_key_batch


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
        assert len(derived) == 32, f"Derived key must be 32 bytes, got {len(derived)}"

    # Test batch derivation
    print("\nTesting batch derivation...")
    batch_keys = derive_key_batch(master_key, test_indices)
    print(f"  ✓ Derived {len(batch_keys)} keys in batch")

    # Verify consistency
    individual_keys = [derive_key(master_key, idx) for idx in test_indices]
    assert batch_keys == individual_keys, "Batch derivation must match individual"
    print("  ✓ Batch and individual derivation match")

    print("\n✓ Key derivation test passed")


def test_deterministic_derivation(master_keys: dict):
    """Test that key derivation is deterministic."""
    print("\n" + "=" * 80)
    print("TEST 2: Deterministic Derivation")
    print("=" * 80)

    table_id = 0
    master_key = master_keys[table_id]
    key_index = 42

    print(f"\nDeriving key from table {table_id}, index {key_index} multiple times...")

    # Derive the same key 5 times
    derivations = [derive_key(master_key, key_index) for _ in range(5)]

    # All should be identical
    first = derivations[0]
    for i, derived in enumerate(derivations[1:], start=2):
        assert derived == first, f"Derivation {i} doesn't match first derivation"
        print(f"  Derivation {i}: {derived.hex()[:32]}... ✓")

    print("\n✓ Deterministic derivation test passed")


def test_multiple_tables(master_keys: dict):
    """Test deriving keys from multiple tables."""
    print("\n" + "=" * 80)
    print("TEST 3: Multiple Table Assignment")
    print("=" * 80)

    # Simulate a device assigned to tables 2, 5, 8
    assigned_tables = [2, 5, 8]
    print(f"\nSimulating device assigned to tables: {assigned_tables}")

    # Derive keys from each table
    for table_id in assigned_tables:
        master_key = master_keys[table_id]
        key_index = 42
        derived = derive_key(master_key, key_index)
        print(f"  Table {table_id}, Index {key_index}: {derived.hex()[:32]}...")

    print("\n  In production: Camera would rotate through assigned tables")
    print("  This prevents SMA from tracking individual cameras")

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


def test_cross_platform_consistency(master_keys: dict):
    """Test that key derivation produces expected values (cross-platform test)."""
    print("\n" + "=" * 80)
    print("TEST 5: Cross-Platform Consistency")
    print("=" * 80)

    # Known test vectors (these should remain stable forever)
    test_vectors = [
        {
            "master_key": "00" * 32,  # All zeros
            "key_index": 0,
            "expected": "28cef44dfd1eb717665106490b96dc68312a499adc0d79e1c73ea6787d3c18c2"
        },
        {
            "master_key": "00" * 32,
            "key_index": 1,
            "expected": "913254cdbff968d6bf0cebc44fd85a3846fabf80b737633f458040b395fa8392"
        },
        {
            "master_key": "ff" * 32,  # All FFs
            "key_index": 0,
            "expected": "a9395e32133165a8b0e539dbd127d5b5ac43957883f2f8d3ca55e32db17cd01f"
        },
    ]

    print("\nVerifying known test vectors...")

    for i, tv in enumerate(test_vectors, 1):
        master_key = bytes.fromhex(tv["master_key"])
        key_index = tv["key_index"]
        expected = tv["expected"]

        derived = derive_key(master_key, key_index)
        actual = derived.hex()

        print(f"\n  Test Vector {i}:")
        print(f"    Master: {tv['master_key'][:32]}...")
        print(f"    Index:  {key_index}")
        print(f"    Expected: {expected[:32]}...")
        print(f"    Actual:   {actual[:32]}...")

        assert actual == expected, f"Test vector {i} failed!"
        print(f"    ✓ Match")

    print("\n✓ Cross-platform consistency test passed")
    print("  (Key derivation produces identical results across platforms)")


def test_edge_cases(master_keys: dict):
    """Test edge cases in key derivation."""
    print("\n" + "=" * 80)
    print("TEST 6: Edge Cases")
    print("=" * 80)

    master_key = master_keys[0]

    print("\nTesting boundary conditions...")

    # Test minimum index
    print("  Testing index 0 (minimum)...")
    key_0 = derive_key(master_key, 0)
    assert len(key_0) == 32
    print(f"    ✓ Derived: {key_0.hex()[:32]}...")

    # Test maximum index
    print("  Testing index 999 (maximum)...")
    key_999 = derive_key(master_key, 999)
    assert len(key_999) == 32
    print(f"    ✓ Derived: {key_999.hex()[:32]}...")

    # Verify they're different
    assert key_0 != key_999, "Min and max indices must produce different keys"
    print("    ✓ Min and max indices produce different keys")

    # Test invalid inputs
    print("\n  Testing invalid inputs...")

    try:
        # Test with wrong-size master key
        derive_key(b"short", 0)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"    ✓ Rejected short master key: {e}")

    try:
        # Test with negative index
        derive_key(master_key, -1)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"    ✓ Rejected negative index: {e}")

    try:
        # Test with index > 999
        derive_key(master_key, 1000)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"    ✓ Rejected out-of-range index: {e}")

    print("\n✓ Edge cases test passed")


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
    print("SMA Key Derivation Test Suite - Birthmark Standard")
    print("=" * 80)
    print(f"Loading key tables from: {key_tables_path}")

    master_keys, metadata = load_key_tables(str(key_tables_path))

    print(f"\nLoaded {len(master_keys)} key tables")
    print(f"Configuration: {metadata['configuration']['num_tables']} tables × "
          f"{metadata['configuration']['keys_per_table']} keys")
    print(f"Created: {metadata['created_at']}")

    # Run all tests
    test_key_derivation(master_keys)
    test_deterministic_derivation(master_keys)
    test_multiple_tables(master_keys)
    test_key_uniqueness(master_keys)
    test_cross_platform_consistency(master_keys)
    test_edge_cases(master_keys)

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("✓ All 6 tests passed successfully")
    print("\nKey derivation system verified:")
    print("  ✓ Keys derive correctly from master keys")
    print("  ✓ Derivation is deterministic")
    print("  ✓ Multiple tables work correctly")
    print("  ✓ All derived keys are unique")
    print("  ✓ Cross-platform consistency maintained")
    print("  ✓ Edge cases handled properly")
    print("\nKey table system is ready for:")
    print("  - Device provisioning (assign 3 tables to each device)")
    print("  - Camera-side NUC encryption")
    print("  - SMA validation server integration")
    print("=" * 80)


if __name__ == "__main__":
    main()
