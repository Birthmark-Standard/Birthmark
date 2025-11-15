#!/usr/bin/env python3
"""
Test script to initialize a Birthmark Camera object with provisioning data.

Demonstrates loading provisioning data and creating a camera instance.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from camera_pi.provisioning_client import ProvisioningClient
from camera_pi.camera_token import create_token_generator_from_provisioning
from camera_pi.crypto.signing import load_private_key_from_pem


def test_provisioning_load():
    """Test loading provisioning data."""
    print("=" * 70)
    print("  Testing Camera Provisioning Data Load")
    print("=" * 70)

    # Initialize provisioning client
    provisioning_path = Path(__file__).parent / "data" / "provisioning.json"

    if not provisioning_path.exists():
        print(f"\n❌ Provisioning file not found: {provisioning_path}")
        print("Run the SMA provisioning script first.")
        return False

    print(f"\n📄 Loading provisioning data from:")
    print(f"   {provisioning_path}")

    try:
        client = ProvisioningClient(provisioning_path)
        data = client.load_from_file()

        print("\n✓ Provisioning data loaded successfully!\n")

        # Display device information
        print("=" * 70)
        print("  Device Information")
        print("=" * 70)
        print(f"Device Serial:     {data.device_serial}")
        print(f"Device Family:     {data.device_family}")
        print(f"NUC Hash:          {data.nuc_hash[:32]}...")
        print(f"Table Assignments: {data.table_assignments}")

        # Display master keys availability
        print("\n" + "=" * 70)
        print("  Master Keys (Phase 1 Only)")
        print("=" * 70)
        for table_id in data.table_assignments:
            master_key = data.get_master_key_bytes(table_id)
            print(f"Table {table_id}: {master_key.hex()[:32]}... ({len(master_key)} bytes)")

        # Display certificates
        print("\n" + "=" * 70)
        print("  Certificates")
        print("=" * 70)
        print(f"Device Cert:       {len(data.device_certificate)} bytes")
        print(f"CA Chain:          {len(data.certificate_chain)} bytes")
        print(f"Private Key:       {len(data.device_private_key)} bytes")
        print(f"Public Key:        {len(data.device_public_key)} bytes")

        return True, data

    except Exception as e:
        print(f"\n❌ Error loading provisioning data: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_token_generator(data):
    """Test creating token generator."""
    print("\n" + "=" * 70)
    print("  Testing Token Generator")
    print("=" * 70)

    try:
        # Create token generator
        generator = create_token_generator_from_provisioning(data)

        print("\n✓ Token generator created successfully!")

        # Generate a test token
        print("\nGenerating test token...")
        token = generator.generate_token()

        print(f"\n✓ Token generated:")
        print(f"  Table ID:   {token.table_id}")
        print(f"  Key Index:  {token.key_index}")
        print(f"  Ciphertext: {token.ciphertext[:32]}...")
        print(f"  Nonce:      {token.nonce}")
        print(f"  Auth Tag:   {token.auth_tag}")

        # Generate multiple tokens
        print("\nGenerating 5 test tokens:")
        tokens = generator.generate_multiple_tokens(5)
        for i, t in enumerate(tokens, 1):
            print(f"  Token {i}: table={t.table_id}, key_index={t.key_index}")

        return True

    except Exception as e:
        print(f"\n❌ Error creating token generator: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_key_loading(data):
    """Test loading cryptographic keys."""
    print("\n" + "=" * 70)
    print("  Testing Cryptographic Keys")
    print("=" * 70)

    try:
        # Load private key
        print("\nLoading device private key...")
        private_key = load_private_key_from_pem(data.device_private_key)
        print(f"✓ Private key loaded: {type(private_key).__name__}")

        # Get public key from private key
        public_key = private_key.public_key()
        print(f"✓ Public key derived: {type(public_key).__name__}")

        return True

    except Exception as e:
        print(f"\n❌ Error loading keys: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║  Birthmark Camera Initialization Test                     ║")
    print("╚════════════════════════════════════════════════════════════╝")

    # Test 1: Load provisioning data
    success, data = test_provisioning_load()
    if not success:
        print("\n❌ Provisioning load failed!")
        return 1

    # Test 2: Create token generator
    if not test_token_generator(data):
        print("\n❌ Token generator test failed!")
        return 1

    # Test 3: Load cryptographic keys
    if not test_key_loading(data):
        print("\n❌ Key loading test failed!")
        return 1

    # Success!
    print("\n" + "=" * 70)
    print("\n✅ All tests passed! Camera provisioning is working correctly.")
    print("\nNext steps:")
    print("  1. Test full camera initialization (BirthmarkCamera class)")
    print("  2. Test mock photo capture")
    print("  3. Test authentication bundle creation")
    print("\n" + "=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
