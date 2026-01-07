#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
SMA Setup Script

Initializes the Simulated Manufacturer Authority:
1. Generate Root CA and Intermediate CA certificates
2. Generate key tables (Phase 1: 10 tables, Phase 2: 2500 tables)
3. Initialize device registry

Run this script once before starting the SMA service.
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.provisioning.certificate import (
    CertificateAuthority,
    save_certificate,
    save_private_key
)
from src.key_tables.table_manager import KeyTableManager


def setup_ca_certificates(data_dir: Path, force: bool = False):
    """
    Generate CA certificates (root and intermediate).

    Args:
        data_dir: Directory to store certificates
        force: Overwrite existing certificates if True
    """
    print("\n=== Setting up CA Certificates ===")

    root_cert_path = data_dir / "root-ca.crt"
    root_key_path = data_dir / "root-ca.key"
    intermediate_cert_path = data_dir / "intermediate-ca.crt"
    intermediate_key_path = data_dir / "intermediate-ca.key"

    # Check if certificates already exist
    if not force and all([
        root_cert_path.exists(),
        root_key_path.exists(),
        intermediate_cert_path.exists(),
        intermediate_key_path.exists()
    ]):
        print("✓ CA certificates already exist")
        print(f"  Root CA: {root_cert_path}")
        print(f"  Intermediate CA: {intermediate_cert_path}")
        print("  Use --force to regenerate")
        return

    # Generate Root CA
    print("\nGenerating Root CA...")
    root_cert, root_key = CertificateAuthority.generate_root_ca(
        common_name="Birthmark Simulated Root CA",
        validity_days=3650  # 10 years
    )

    save_certificate(root_cert, root_cert_path)
    save_private_key(root_key, root_key_path)

    print(f"✓ Generated Root CA")
    print(f"  Certificate: {root_cert_path}")
    print(f"  Private Key: {root_key_path}")

    # Generate Intermediate CA
    print("\nGenerating Intermediate CA...")
    intermediate_cert, intermediate_key = CertificateAuthority.generate_intermediate_ca(
        root_cert=root_cert,
        root_key=root_key,
        common_name="Birthmark Simulated Intermediate CA",
        validity_days=1825  # 5 years
    )

    save_certificate(intermediate_cert, intermediate_cert_path)
    save_private_key(intermediate_key, intermediate_key_path)

    print(f"✓ Generated Intermediate CA")
    print(f"  Certificate: {intermediate_cert_path}")
    print(f"  Private Key: {intermediate_key_path}")

    # Set restrictive permissions
    for path in [root_key_path, intermediate_key_path]:
        path.chmod(0o600)

    print("\n✓ CA certificates generated successfully!")


def setup_key_tables(data_dir: Path, num_tables: int = 10, force: bool = False):
    """
    Generate key tables.

    Args:
        data_dir: Directory to store key tables
        num_tables: Number of key tables to generate (Phase 1: 10, Phase 2: 2500)
        force: Overwrite existing key tables if True
    """
    print(f"\n=== Setting up Key Tables ({num_tables} tables) ===")

    key_tables_path = data_dir / "key_tables.json"

    # Check if key tables already exist
    if not force and key_tables_path.exists():
        print(f"✓ Key tables already exist at {key_tables_path}")
        print("  Use --force to regenerate")
        return

    # Generate key tables
    print(f"\nGenerating {num_tables} key tables...")
    table_manager = KeyTableManager(
        total_tables=num_tables,
        tables_per_device=3,
        storage_path=key_tables_path
    )

    table_manager.generate_all_tables()
    table_manager.save_to_file()

    print(f"✓ Generated {num_tables} key tables")
    print(f"  Saved to: {key_tables_path}")

    # Set restrictive permissions
    key_tables_path.chmod(0o600)

    stats = table_manager.get_statistics()
    print(f"  Total tables: {stats['total_tables']}")
    print(f"  Tables per device: {stats['tables_per_device']}")


def setup_device_registry(data_dir: Path):
    """
    Initialize empty device registry.

    Args:
        data_dir: Directory to store device registry
    """
    print("\n=== Setting up Device Registry ===")

    registry_path = data_dir / "device_registry.json"

    if registry_path.exists():
        print(f"✓ Device registry already exists at {registry_path}")
        return

    # Create empty registry file
    import json
    with open(registry_path, "w") as f:
        json.dump({
            "devices": [],
            "total_devices": 0,
            "last_updated": None
        }, f, indent=2)

    registry_path.chmod(0o600)

    print(f"✓ Initialized empty device registry")
    print(f"  Path: {registry_path}")


def main():
    """Main setup function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Setup Birthmark SMA (Simulated Manufacturer Authority)"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).parent.parent / "data",
        help="Directory to store SMA data (default: ../data)"
    )
    parser.add_argument(
        "--num-tables",
        type=int,
        default=10,
        help="Number of key tables to generate (Phase 1: 10, Phase 2: 2500)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files"
    )
    parser.add_argument(
        "--phase2",
        action="store_true",
        help="Setup for Phase 2 (2500 key tables)"
    )

    args = parser.parse_args()

    # Use Phase 2 table count if specified
    if args.phase2:
        args.num_tables = 2500

    print("╔════════════════════════════════════════════════════════════╗")
    print("║  Birthmark SMA Setup                                       ║")
    print("║  Simulated Manufacturer Authority Initialization           ║")
    print("╚════════════════════════════════════════════════════════════╝")

    # Create data directory
    args.data_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Data directory: {args.data_dir}")

    # Setup CA certificates
    setup_ca_certificates(args.data_dir, force=args.force)

    # Setup key tables
    setup_key_tables(args.data_dir, num_tables=args.num_tables, force=args.force)

    # Setup device registry
    setup_device_registry(args.data_dir)

    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║  ✓ SMA Setup Complete!                                     ║")
    print("╚════════════════════════════════════════════════════════════╝")

    print("\nNext steps:")
    print("  1. Start the SMA service:")
    print("     cd packages/sma")
    print("     uvicorn src.main:app --port 8001 --reload")
    print("\n  2. Provision a device:")
    print("     python scripts/provision_device.py --serial DEVICE001")
    print("\n  3. Check service health:")
    print("     curl http://localhost:8001/health")


if __name__ == "__main__":
    main()
