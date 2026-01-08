#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
SMA Key Table Generation Script

Generates master keys for the Simulated Manufacturer Authority (SMA).
Each table contains a master key from which individual encryption keys
are derived using HKDF.

For Phase 1: 10 tables × 100 keys each
For Phase 2: 2,500 tables × 1,000 keys each

The master keys are stored in JSON format for easy loading and use.
Individual keys are derived on-demand using the key_derivation module.
"""

import os
import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional
import sys

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "shared"))

from crypto.key_derivation import derive_key, verify_key_derivation_consistency


class KeyTableGenerator:
    """
    Generator for SMA key tables.

    This class handles the creation of master keys and their storage in JSON format.
    It does NOT store derived keys - those are computed on-demand using HKDF.
    """

    def __init__(self, num_tables: int = 10, keys_per_table: int = 100):
        """
        Initialize the key table generator.

        Args:
            num_tables: Number of key tables to generate (10 for Phase 1, 2500 for Phase 2)
            keys_per_table: Number of keys each table supports (100 for Phase 1, 1000 for Phase 2)
        """
        self.num_tables = num_tables
        self.keys_per_table = keys_per_table
        self.key_tables = {}

    def generate_master_keys(self) -> dict:
        """
        Generate cryptographically secure master keys for all tables.

        Each master key is 256 bits (32 bytes) of cryptographically secure
        random data generated using Python's secrets module.

        Returns:
            Dictionary mapping table_id -> master_key (as hex string)
        """
        print(f"[SMA] Generating {self.num_tables} master keys...")

        master_keys = {}
        for table_id in range(self.num_tables):
            # Generate 256-bit (32-byte) cryptographically secure random key
            master_key = secrets.token_bytes(32)
            master_keys[table_id] = master_key.hex()

            # Progress indicator for large generations
            if (table_id + 1) % 100 == 0:
                print(f"  Generated {table_id + 1}/{self.num_tables} master keys...")

        print(f"[SMA] ✓ Generated {len(master_keys)} master keys")
        return master_keys

    def verify_key_table_integrity(self, master_keys: dict) -> bool:
        """
        Verify that the generated master keys can derive valid encryption keys.

        This performs sanity checks on the master keys by deriving a few
        test keys and verifying they meet requirements.

        Args:
            master_keys: Dictionary of master keys to verify

        Returns:
            True if all checks pass

        Raises:
            AssertionError: If any verification fails
        """
        print("[SMA] Verifying key table integrity...")

        # Check 1: All master keys are 32 bytes
        for table_id, master_key_hex in master_keys.items():
            master_key = bytes.fromhex(master_key_hex)
            assert len(master_key) == 32, f"Table {table_id}: Master key must be 32 bytes"

        # Check 2: All master keys are unique
        unique_keys = set(master_keys.values())
        assert len(unique_keys) == len(master_keys), "All master keys must be unique"

        # Check 3: Can derive keys from each master key
        for table_id, master_key_hex in list(master_keys.items())[:5]:  # Test first 5
            master_key = bytes.fromhex(master_key_hex)

            # Derive first, middle, and last key from this table
            test_indices = [0, self.keys_per_table // 2, self.keys_per_table - 1]

            for key_index in test_indices:
                derived_key = derive_key(master_key, key_index)
                assert len(derived_key) == 32, "Derived key must be 32 bytes"

        # Check 4: Different indices produce different keys
        master_key = bytes.fromhex(master_keys[0])
        key_0 = derive_key(master_key, 0)
        key_1 = derive_key(master_key, 1)
        assert key_0 != key_1, "Different indices must produce different keys"

        print("[SMA] ✓ Key table integrity verified")
        return True

    def save_to_json(
        self,
        master_keys: dict,
        output_path: str,
        metadata: Optional[dict] = None
    ) -> None:
        """
        Save master keys to JSON file.

        The JSON file contains:
        - Master keys for each table
        - Metadata (creation time, version, configuration)
        - Schema version for future compatibility

        Args:
            master_keys: Dictionary of master keys to save
            output_path: Path to output JSON file
            metadata: Optional additional metadata to include
        """
        print(f"[SMA] Saving key tables to {output_path}...")

        # Build output structure
        output_data = {
            "schema_version": "1.0",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "configuration": {
                "num_tables": self.num_tables,
                "keys_per_table": self.keys_per_table,
                "key_size_bits": 256,
                "derivation_function": "HKDF-SHA256"
            },
            "key_tables": [
                {
                    "table_id": table_id,
                    "master_key": master_key_hex,
                    "status": "active"
                }
                for table_id, master_key_hex in master_keys.items()
            ],
            "metadata": metadata or {}
        }

        # Create output directory if it doesn't exist
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write JSON file
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)

        # Verify file was written
        file_size = Path(output_path).stat().st_size
        print(f"[SMA] ✓ Saved key tables ({file_size:,} bytes)")

    def load_from_json(self, input_path: str) -> dict:
        """
        Load master keys from JSON file.

        Args:
            input_path: Path to JSON file containing key tables

        Returns:
            Dictionary mapping table_id -> master_key (as hex string)

        Raises:
            FileNotFoundError: If input file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
            KeyError: If required fields are missing
        """
        print(f"[SMA] Loading key tables from {input_path}...")

        with open(input_path, 'r') as f:
            data = json.load(f)

        # Extract master keys
        master_keys = {
            table["table_id"]: table["master_key"]
            for table in data["key_tables"]
        }

        print(f"[SMA] ✓ Loaded {len(master_keys)} key tables")
        print(f"  Schema version: {data['schema_version']}")
        print(f"  Created at: {data['created_at']}")
        print(f"  Configuration: {data['configuration']['num_tables']} tables × "
              f"{data['configuration']['keys_per_table']} keys")

        return master_keys

    def generate_and_save(self, output_path: str, metadata: Optional[dict] = None) -> None:
        """
        Generate master keys and save to JSON file (convenience method).

        Args:
            output_path: Path to output JSON file
            metadata: Optional metadata to include
        """
        # Run key derivation self-tests first
        print("[SMA] Running key derivation self-tests...")
        verify_key_derivation_consistency()

        # Generate master keys
        master_keys = self.generate_master_keys()

        # Verify integrity
        self.verify_key_table_integrity(master_keys)

        # Save to file
        self.save_to_json(master_keys, output_path, metadata)

        print(f"\n[SMA] ✓ Key table generation complete!")
        print(f"  Tables: {self.num_tables}")
        print(f"  Keys per table: {self.keys_per_table}")
        print(f"  Total derivable keys: {self.num_tables * self.keys_per_table:,}")
        print(f"  Output file: {output_path}")


def derive_sample_keys(master_key_hex: str, num_samples: int = 5) -> None:
    """
    Derive and display sample keys from a master key.

    This is a utility function for testing and verification.

    Args:
        master_key_hex: Master key as hex string
        num_samples: Number of sample keys to derive
    """
    master_key = bytes.fromhex(master_key_hex)
    print(f"\nSample key derivations from master key: {master_key_hex[:16]}...")
    print("-" * 80)

    for i in range(num_samples):
        derived = derive_key(master_key, i)
        print(f"  Index {i:3}: {derived.hex()}")

    print("-" * 80)


def main():
    """
    Main entry point for key table generation script.

    Usage:
        # Generate Phase 1 key tables (10 tables × 100 keys)
        python generate.py

        # Generate Phase 2 key tables (2,500 tables × 1,000 keys)
        python generate.py --phase2

        # Custom configuration
        python generate.py --tables 50 --keys 500 --output custom_keys.json
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate SMA key tables for Birthmark Standard"
    )
    parser.add_argument(
        "--phase2",
        action="store_true",
        help="Generate Phase 2 tables (2,500 tables × 1,000 keys)"
    )
    parser.add_argument(
        "--tables",
        type=int,
        help="Number of tables to generate (default: 10 for Phase 1, 2500 for Phase 2)"
    )
    parser.add_argument(
        "--keys",
        type=int,
        help="Keys per table (default: 100 for Phase 1, 1000 for Phase 2)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON file path"
    )
    parser.add_argument(
        "--verify",
        type=str,
        help="Verify existing key table file"
    )
    parser.add_argument(
        "--sample-keys",
        type=str,
        help="Show sample derived keys for a given master key (hex string)"
    )

    args = parser.parse_args()

    # Handle sample key derivation
    if args.sample_keys:
        derive_sample_keys(args.sample_keys)
        return

    # Handle verification
    if args.verify:
        generator = KeyTableGenerator()
        master_keys = generator.load_from_json(args.verify)
        generator.verify_key_table_integrity(master_keys)
        print("\n[SMA] ✓ Verification complete - key tables are valid")
        return

    # Determine configuration
    if args.phase2:
        num_tables = 2500
        keys_per_table = 1000
        default_output = "key_tables_phase2.json"
    else:
        num_tables = 10
        keys_per_table = 100
        default_output = "key_tables_phase1.json"

    # Allow overrides
    if args.tables:
        num_tables = args.tables
    if args.keys:
        keys_per_table = args.keys

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        # Default to data directory in SMA package
        script_dir = Path(__file__).parent
        data_dir = script_dir.parent.parent / "data"
        output_path = str(data_dir / default_output)

    # Generate key tables
    print("=" * 80)
    print("SMA Key Table Generator - Birthmark Standard")
    print("=" * 80)
    print(f"Configuration: {num_tables} tables × {keys_per_table} keys")
    print(f"Output: {output_path}")
    print("=" * 80)
    print()

    generator = KeyTableGenerator(num_tables=num_tables, keys_per_table=keys_per_table)
    generator.generate_and_save(
        output_path=output_path,
        metadata={
            "phase": "Phase 2" if args.phase2 else "Phase 1",
            "generated_by": "generate.py",
            "generator_version": "1.0"
        }
    )

    print("\n" + "=" * 80)
    print("Next Steps:")
    print("  1. Securely store this JSON file (it contains sensitive cryptographic keys)")
    print("  2. Use this file to configure the SMA validation server")
    print("  3. During device provisioning, assign 3 random tables to each device")
    print("=" * 80)


if __name__ == "__main__":
    main()
