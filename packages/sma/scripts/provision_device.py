#!/usr/bin/env python3
"""
Device Provisioning Script

Manually provision a device with the SMA:
1. Generate device certificate
2. Assign key tables
3. Save provisioning data to file
4. Display instructions for device setup

Phase 1: Manual provisioning via this script
Phase 2: Automated provisioning via API endpoint
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.provisioning.certificate import CertificateAuthority
from src.provisioning.provisioner import (
    DeviceProvisioner,
    ProvisioningRequest,
    ProvisioningResponse
)
from src.key_tables.table_manager import KeyTableManager
from src.identity.device_registry import DeviceRegistry, DeviceRegistration


def save_provisioning_data(
    response: ProvisioningResponse,
    output_dir: Path
) -> Path:
    """
    Save provisioning data to JSON file.

    Args:
        response: Provisioning response
        output_dir: Directory to save provisioning file

    Returns:
        Path to provisioning file
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create provisioning file
    provisioning_file = output_dir / f"provisioning_{response.device_serial}.json"

    with open(provisioning_file, "w") as f:
        json.dump(response.to_dict(), f, indent=2)

    # Set restrictive permissions (contains private key!)
    provisioning_file.chmod(0o600)

    return provisioning_file


def display_provisioning_info(response: ProvisioningResponse):
    """
    Display provisioning information.

    Args:
        response: Provisioning response
    """
    print("\n" + "=" * 70)
    print(f"  Device Provisioned: {response.device_serial}")
    print("=" * 70)

    print(f"\n📱 Device Information:")
    print(f"  Serial:        {response.device_serial}")
    print(f"  Family:        {response.device_family}")
    print(f"  NUC Hash:      {response.nuc_hash[:32]}...")

    print(f"\n🔑 Key Table Assignments:")
    print(f"  Tables:        {response.table_assignments}")
    print(f"  Total:         {len(response.table_assignments)} tables")

    print(f"\n📜 Certificate Information:")
    print(f"  Device Cert:   {len(response.device_certificate)} bytes")
    print(f"  CA Chain:      {len(response.certificate_chain)} bytes")
    print(f"  Private Key:   {len(response.device_private_key)} bytes")
    print(f"  Public Key:    {len(response.device_public_key)} bytes")


def provision_device(
    device_serial: str,
    device_family: str,
    data_dir: Path,
    output_dir: Path,
    nuc_hash: str = None
) -> ProvisioningResponse:
    """
    Provision a single device.

    Args:
        device_serial: Unique device serial number
        device_family: Device type (e.g., "Raspberry Pi", "iOS")
        data_dir: SMA data directory
        output_dir: Output directory for provisioning file
        nuc_hash: Optional hex-encoded NUC hash

    Returns:
        ProvisioningResponse

    Raises:
        FileNotFoundError: If CA certificates or key tables not found
        ValueError: If device already provisioned
    """
    # Load CA certificates
    ca_cert_path = data_dir / "intermediate-ca.crt"
    ca_key_path = data_dir / "intermediate-ca.key"

    if not ca_cert_path.exists() or not ca_key_path.exists():
        raise FileNotFoundError(
            f"CA certificates not found. Run setup_sma.py first.\n"
            f"  Expected: {ca_cert_path} and {ca_key_path}"
        )

    ca = CertificateAuthority(ca_cert_path, ca_key_path)

    # Load key tables
    key_tables_path = data_dir / "key_tables.json"

    if not key_tables_path.exists():
        raise FileNotFoundError(
            f"Key tables not found. Run setup_sma.py first.\n"
            f"  Expected: {key_tables_path}"
        )

    table_manager = KeyTableManager(storage_path=key_tables_path)
    table_manager.load_from_file()

    # Load device registry
    registry_path = data_dir / "device_registry.json"
    device_registry = DeviceRegistry(storage_path=registry_path)

    if registry_path.exists():
        device_registry.load_from_file()

    # Check if device already provisioned
    if device_registry.device_exists(device_serial):
        raise ValueError(f"Device {device_serial} already provisioned")

    # Create provisioner
    provisioner = DeviceProvisioner(ca, table_manager)

    # Convert NUC hash if provided
    nuc_hash_bytes = None
    if nuc_hash:
        try:
            nuc_hash_bytes = bytes.fromhex(nuc_hash)
            if len(nuc_hash_bytes) != 32:
                raise ValueError("NUC hash must be 32 bytes (64 hex chars)")
        except ValueError as e:
            raise ValueError(f"Invalid NUC hash: {e}")

    # Provision device
    request = ProvisioningRequest(
        device_serial=device_serial,
        device_family=device_family,
        nuc_hash=nuc_hash_bytes
    )

    response = provisioner.provision_device(request)

    # Register device
    registration = DeviceRegistration(
        device_serial=response.device_serial,
        nuc_hash=response.nuc_hash,
        table_assignments=response.table_assignments,
        device_certificate=response.device_certificate,
        device_public_key=response.device_public_key,
        device_family=response.device_family,
        provisioned_at=datetime.utcnow().isoformat()
    )

    device_registry.register_device(registration)

    # Save registry
    device_registry.save_to_file()

    # Save key table assignments
    table_manager.save_to_file()

    return response


def main():
    """Main provisioning function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Provision a device with Birthmark SMA"
    )
    parser.add_argument(
        "--serial",
        required=True,
        help="Device serial number (e.g., DEVICE001, PI-12345)"
    )
    parser.add_argument(
        "--family",
        default="Raspberry Pi",
        help="Device family (default: Raspberry Pi)"
    )
    parser.add_argument(
        "--nuc-hash",
        help="Hex-encoded NUC hash (optional, will be simulated if not provided)"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).parent.parent / "data",
        help="SMA data directory (default: ../data)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent.parent / "provisioned_devices",
        help="Output directory for provisioning files (default: ../provisioned_devices)"
    )

    args = parser.parse_args()

    print("╔════════════════════════════════════════════════════════════╗")
    print("║  Birthmark Device Provisioning                            ║")
    print("╚════════════════════════════════════════════════════════════╝")

    try:
        # Provision device
        response = provision_device(
            device_serial=args.serial,
            device_family=args.family,
            data_dir=args.data_dir,
            output_dir=args.output_dir,
            nuc_hash=args.nuc_hash
        )

        # Display provisioning info
        display_provisioning_info(response)

        # Save provisioning data
        provisioning_file = save_provisioning_data(response, args.output_dir)

        print(f"\n💾 Provisioning Data Saved:")
        print(f"  File: {provisioning_file}")
        print(f"  ⚠️  Contains private key - keep secure!")

        print("\n" + "=" * 70)
        print("  ✓ Provisioning Complete!")
        print("=" * 70)

        print("\nNext steps:")
        print(f"  1. Copy provisioning file to device:")
        print(f"     scp {provisioning_file} pi@device:/home/pi/")
        print(f"\n  2. On device, install credentials:")
        print(f"     python install_credentials.py {provisioning_file.name}")
        print(f"\n  3. Test device authentication:")
        print(f"     python test_submission.py")

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nRun setup_sma.py first to initialize the SMA.")
        sys.exit(1)

    except ValueError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
