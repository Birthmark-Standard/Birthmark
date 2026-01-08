#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Generate Phase 2 key tables for SMA.

Creates 2,500 key tables with 1,000 derived keys each.
Total: 2.5 million keys.

WARNING: This creates a large file (~80MB).
Only run this once during SMA setup.

Usage:
    python scripts/generate_phase2_key_tables.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.key_tables.table_manager import Phase2KeyTableManager


def main():
    print("="*60)
    print("Phase 2 Key Table Generation")
    print("="*60)
    print()
    print("This will generate:")
    print("  - 2,500 key tables")
    print("  - 1,000 keys per table")
    print("  - Total: 2.5 million keys")
    print()
    print("Expected file size: ~80MB")
    print("Expected time: 2-5 minutes")
    print()

    # Confirm
    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("Aborted.")
        return

    # Set up storage path
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    key_tables_path = data_dir / "key_tables.json"

    # Check if file exists
    if key_tables_path.exists():
        print()
        print(f"⚠ WARNING: {key_tables_path} already exists!")
        response = input("Overwrite? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            return

    print()
    print("Generating key tables...")
    print()

    # Initialize Phase 2 manager
    manager = Phase2KeyTableManager(
        total_tables=2500,
        keys_per_table=1000,
        storage_path=key_tables_path
    )

    # Generate all tables with keys
    manager.generate_all_tables_with_keys()

    print()
    print("Saving to disk...")
    manager.save_to_file_with_keys()

    print()
    print("="*60)
    print("✓ Phase 2 key table generation complete!")
    print("="*60)
    print()
    print(f"File: {key_tables_path}")
    print(f"Master keys: {len(manager.key_tables)}")
    print(f"Derived key tables: {len(manager.derived_keys)}")
    print(f"Keys per table: {manager.keys_per_table}")
    print()
    print("You can now start the SMA server:")
    print("  cd packages/sma")
    print("  uvicorn src.main:app --port 8001 --reload")
    print()


if __name__ == "__main__":
    main()
