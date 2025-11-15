#!/usr/bin/env python3
"""
Test script for SMA validation endpoint.

This script:
1. Initializes the database
2. Generates key tables
3. Registers a test device
4. Encrypts a NUC token
5. Validates it through the endpoint
"""

import base64
import hashlib
import secrets
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.crypto import derive_key_from_master, encrypt_nuc_token
from shared.types import ValidationRequest

from packages.sma.src.database import SessionLocal, init_database
from packages.sma.src.identity import register_device
from packages.sma.src.key_tables import generate_master_keys, populate_key_tables
from packages.sma.src.validation import validate_authentication_token


def setup_test_database():
    """Initialize test database with key tables."""
    print("Initializing test database...")
    database_url = "postgresql://postgres:postgres@localhost/sma_test"
    init_database(database_url)

    db = SessionLocal()

    # Check if key tables already exist
    from packages.sma.src.database import KeyTable

    existing_count = db.query(KeyTable).count()

    if existing_count == 0:
        print("Generating 2,500 master keys...")
        master_keys = generate_master_keys()

        print("Populating key tables...")
        populate_key_tables(db, master_keys)
        print("✓ Key tables populated")
    else:
        print(f"✓ Key tables already exist ({existing_count} tables)")

    db.close()
    return database_url


def register_test_device():
    """Register a test Raspberry Pi device."""
    print("\nRegistering test device...")

    db = SessionLocal()

    # Generate test NUC hash
    nuc_map = b"simulated_nuc_correction_map_for_test_device"
    nuc_hash = hashlib.sha256(nuc_map).digest()

    # Assign random key tables
    table_assignments = [42, 1337, 2001]

    # Mock certificate and public key
    device_certificate = "-----BEGIN CERTIFICATE-----\nMOCK_CERT\n-----END CERTIFICATE-----"
    device_public_key = "-----BEGIN PUBLIC KEY-----\nMOCK_KEY\n-----END PUBLIC KEY-----"

    try:
        device = register_device(
            db=db,
            device_serial="TEST-RPI-001",
            nuc_hash=nuc_hash,
            table_assignments=table_assignments,
            device_certificate=device_certificate,
            device_public_key=device_public_key,
            device_family="Raspberry Pi",
        )
        print(f"✓ Device registered: {device.device_serial}")
    except RuntimeError:
        print("✓ Device already registered")

    db.close()
    return nuc_hash, table_assignments


def test_validation(nuc_hash: bytes, table_assignments: list):
    """Test the validation endpoint."""
    print("\nTesting validation...")

    db = SessionLocal()

    # Step 1: Get master keys for the device's tables
    from packages.sma.src.key_tables import get_master_keys

    master_keys = get_master_keys(db, table_assignments)
    print(f"✓ Retrieved master keys for tables: {table_assignments}")

    # Step 2: Derive encryption keys (simulate what camera does)
    key_indices = [7, 99, 512]
    derived_keys = [
        derive_key_from_master(master_key, table_id, key_idx)
        for master_key, table_id, key_idx in zip(master_keys, table_assignments, key_indices)
    ]
    print(f"✓ Derived encryption keys for indices: {key_indices}")

    # Step 3: Encrypt NUC hash (simulate what camera does)
    encrypted_token = encrypt_nuc_token(nuc_hash, derived_keys)
    print(f"✓ Encrypted NUC token ({len(encrypted_token)} bytes)")

    # Step 4: Create validation request
    validation_request = ValidationRequest(
        encrypted_token=encrypted_token,
        table_references=table_assignments,
        key_indices=key_indices,
    )

    # Step 5: Validate
    result = validate_authentication_token(db, validation_request)

    if result.valid:
        print("✓ VALIDATION PASSED - Device authenticated successfully!")
    else:
        print("✗ VALIDATION FAILED - Device not authenticated")
        db.close()
        return False

    # Step 6: Test with wrong key indices (should fail)
    print("\nTesting with wrong key indices (should fail)...")
    wrong_request = ValidationRequest(
        encrypted_token=encrypted_token,
        table_references=table_assignments,
        key_indices=[0, 1, 2],  # Wrong indices
    )
    result = validate_authentication_token(db, wrong_request)

    if not result.valid:
        print("✓ VALIDATION CORRECTLY FAILED for wrong keys")
    else:
        print("✗ VALIDATION INCORRECTLY PASSED for wrong keys")
        db.close()
        return False

    # Step 7: Test with wrong table references (should fail)
    print("\nTesting with wrong table references (should fail)...")
    wrong_request = ValidationRequest(
        encrypted_token=encrypted_token,
        table_references=[0, 1, 2],  # Wrong tables
        key_indices=key_indices,
    )
    result = validate_authentication_token(db, wrong_request)

    if not result.valid:
        print("✓ VALIDATION CORRECTLY FAILED for wrong tables")
    else:
        print("✗ VALIDATION INCORRECTLY PASSED for wrong tables")
        db.close()
        return False

    db.close()
    return True


def test_api_endpoint(nuc_hash: bytes, table_assignments: list):
    """Test the FastAPI endpoint using HTTP."""
    print("\n" + "=" * 60)
    print("API ENDPOINT TEST")
    print("=" * 60)

    import base64

    from packages.sma.src.key_tables import get_master_keys

    db = SessionLocal()
    master_keys = get_master_keys(db, table_assignments)
    key_indices = [7, 99, 512]

    derived_keys = [
        derive_key_from_master(master_key, table_id, key_idx)
        for master_key, table_id, key_idx in zip(master_keys, table_assignments, key_indices)
    ]

    encrypted_token = encrypt_nuc_token(nuc_hash, derived_keys)
    encrypted_token_b64 = base64.b64encode(encrypted_token).decode("ascii")

    db.close()

    print("\nTo test the API endpoint, run:")
    print("  uvicorn packages.sma.src.main:app --port 8001 --reload")
    print("\nThen make this request:")
    print(f"""
curl -X POST http://localhost:8001/api/v1/validate \\
  -H "Content-Type: application/json" \\
  -d '{{
    "encrypted_token": "{encrypted_token_b64[:50]}...",
    "table_references": {table_assignments},
    "key_indices": {key_indices}
  }}'
""")

    print("\nExpected response: {\"valid\": true}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("SMA VALIDATION ENDPOINT TEST")
    print("=" * 60)

    try:
        # Setup
        setup_test_database()
        nuc_hash, table_assignments = register_test_device()

        # Test validation logic
        success = test_validation(nuc_hash, table_assignments)

        if success:
            print("\n" + "=" * 60)
            print("✓ ALL TESTS PASSED")
            print("=" * 60)

            # Show API endpoint test instructions
            test_api_endpoint(nuc_hash, table_assignments)
        else:
            print("\n" + "=" * 60)
            print("✗ SOME TESTS FAILED")
            print("=" * 60)
            sys.exit(1)

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
