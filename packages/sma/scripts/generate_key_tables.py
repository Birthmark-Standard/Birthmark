#!/usr/bin/env python3
"""
Generate and populate the 2,500 key tables for the SMA.

This script should be run once during initial setup to create the master keys
used for HKDF-based key derivation.

WARNING: This script will fail if key tables already exist. To regenerate,
you must first delete the existing tables.
"""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from packages.sma.src.database import SessionLocal, init_database
from packages.sma.src.key_tables import generate_master_keys, populate_key_tables


def main():
    """Generate and populate key tables."""
    print("=" * 60)
    print("SMA KEY TABLE GENERATION")
    print("=" * 60)

    # Get database URL from environment or use default
    import os

    database_url = os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost/sma"
    )

    print(f"\nDatabase: {database_url}")

    try:
        # Initialize database
        print("\nInitializing database...")
        init_database(database_url)
        print("✓ Database initialized")

        # Generate master keys
        print("\nGenerating 2,500 master keys (256-bit each)...")
        master_keys = generate_master_keys(count=2500)
        print(f"✓ Generated {len(master_keys)} master keys")

        # Populate database
        print("\nPopulating key tables...")
        db = SessionLocal()
        populate_key_tables(db, master_keys)
        db.close()
        print("✓ Key tables populated successfully")

        print("\n" + "=" * 60)
        print("✓ KEY TABLE GENERATION COMPLETE")
        print("=" * 60)
        print("\nThe SMA is now ready to validate camera tokens.")
        print("\nNext steps:")
        print("  1. Register devices using the provisioning API")
        print("  2. Start the SMA server: uvicorn src.main:app --port 8001")

    except RuntimeError as e:
        print(f"\n✗ ERROR: {e}")
        print("\nIf key tables already exist and you want to regenerate them,")
        print("you must first delete the existing tables from the database.")
        sys.exit(1)

    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
