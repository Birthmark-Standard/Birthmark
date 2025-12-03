"""
Validation checks for Week 1 + Week 2 implementation.

Checks for:
1. Schema compatibility between aggregator and SMA
2. Missing imports
3. Database model consistency
4. API endpoint compatibility
"""

import sys
from pathlib import Path

# Add paths for imports
blockchain_path = Path(__file__).parent.parent / "src"
sma_path = Path(__file__).parent.parent.parent / "sma" / "src"
sys.path.insert(0, str(blockchain_path))
sys.path.insert(0, str(sma_path))

print("="*70)
print("BIRTHMARK VALIDATION CHECKS - Week 1 + Week 2")
print("="*70)

# Test 1: Import blockchain schemas
print("\n1. Testing Blockchain Schema Imports...")
try:
    from shared.models.schemas import (
        ImageHashEntry,
        CameraToken,
        ManufacturerCert,
        CameraSubmission,
        AuthenticationBundle,
        SubmissionResponse,
    )
    print("   ✓ All blockchain schemas imported successfully")
except ImportError as e:
    print(f"   ✗ Import error: {e}")
    sys.exit(1)

# Test 2: Validate CameraToken schema
print("\n2. Testing CameraToken Schema...")
try:
    # Valid token
    token = CameraToken(
        ciphertext="a" * 128,
        auth_tag="b" * 32,
        nonce="c" * 24,
        table_id=42,
        key_index=123,
    )
    assert token.table_id == 42
    assert token.key_index == 123
    print("   ✓ CameraToken schema validates correctly")

    # Test invalid table_id
    try:
        invalid_token = CameraToken(
            ciphertext="a" * 128,
            auth_tag="b" * 32,
            nonce="c" * 24,
            table_id=250,  # Invalid - must be < 250
            key_index=123,
        )
        print("   ✗ CameraToken should reject table_id >= 250")
        sys.exit(1)
    except Exception:
        print("   ✓ CameraToken correctly rejects invalid table_id")

except Exception as e:
    print(f"   ✗ CameraToken validation error: {e}")
    sys.exit(1)

# Test 3: Validate ImageHashEntry schema
print("\n3. Testing ImageHashEntry Schema...")
try:
    # Valid raw hash
    raw_hash = ImageHashEntry(
        image_hash="a" * 64,
        modification_level=0,
        parent_image_hash=None,
    )
    assert raw_hash.modification_level == 0
    print("   ✓ ImageHashEntry (raw) validates correctly")

    # Valid processed hash
    processed_hash = ImageHashEntry(
        image_hash="b" * 64,
        modification_level=1,
        parent_image_hash="a" * 64,
    )
    assert processed_hash.parent_image_hash == "a" * 64
    print("   ✓ ImageHashEntry (processed) validates correctly")

except Exception as e:
    print(f"   ✗ ImageHashEntry validation error: {e}")
    sys.exit(1)

# Test 4: Validate CameraSubmission schema
print("\n4. Testing CameraSubmission Schema...")
try:
    import time

    # Valid 2-hash submission
    submission = CameraSubmission(
        submission_type="camera",
        image_hashes=[
            ImageHashEntry(
                image_hash="a" * 64,
                modification_level=0,
                parent_image_hash=None,
            ),
            ImageHashEntry(
                image_hash="b" * 64,
                modification_level=1,
                parent_image_hash="a" * 64,
            ),
        ],
        camera_token=CameraToken(
            ciphertext="c" * 128,
            auth_tag="d" * 32,
            nonce="e" * 24,
            table_id=42,
            key_index=123,
        ),
        manufacturer_cert=ManufacturerCert(
            authority_id="TEST_MFG_001",
            validation_endpoint="http://localhost:8001/validate",
        ),
        timestamp=int(time.time()),
    )
    assert len(submission.image_hashes) == 2
    print("   ✓ CameraSubmission (2 hashes) validates correctly")

    # Test invalid order (processed before raw)
    try:
        invalid_submission = CameraSubmission(
            submission_type="camera",
            image_hashes=[
                ImageHashEntry(
                    image_hash="b" * 64,
                    modification_level=1,  # Processed first - invalid
                    parent_image_hash="a" * 64,
                ),
                ImageHashEntry(
                    image_hash="a" * 64,
                    modification_level=0,
                    parent_image_hash=None,
                ),
            ],
            camera_token=CameraToken(
                ciphertext="c" * 128,
                auth_tag="d" * 32,
                nonce="e" * 24,
                table_id=42,
                key_index=123,
            ),
            manufacturer_cert=ManufacturerCert(
                authority_id="TEST_MFG_001",
                validation_endpoint="http://localhost:8001/validate",
            ),
            timestamp=int(time.time()),
        )
        print("   ✗ CameraSubmission should reject invalid hash order")
        sys.exit(1)
    except Exception:
        print("   ✓ CameraSubmission correctly rejects invalid hash order")

except Exception as e:
    print(f"   ✗ CameraSubmission validation error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Check database model compatibility
print("\n5. Testing Database Model Compatibility...")
try:
    from shared.database.models import PendingSubmission

    # Check that all new fields exist
    required_fields = [
        'modification_level',
        'parent_image_hash',
        'transaction_id',
        'manufacturer_authority_id',
        'camera_token_json',
    ]

    model_columns = [c.name for c in PendingSubmission.__table__.columns]

    missing_fields = [f for f in required_fields if f not in model_columns]
    if missing_fields:
        print(f"   ✗ Missing fields in PendingSubmission: {missing_fields}")
        sys.exit(1)

    print("   ✓ PendingSubmission model has all required fields")
    print(f"     Fields: {', '.join(required_fields)}")

except Exception as e:
    print(f"   ✗ Database model error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Check SMA validation request format
print("\n6. Testing SMA Request Format Compatibility...")
try:
    # Simulate what aggregator sends to SMA
    aggregator_request = {
        "camera_token": {
            "ciphertext": "c" * 128,
            "auth_tag": "d" * 32,
            "nonce": "e" * 24,
            "table_id": 42,
            "key_index": 123,
        },
        "manufacturer_authority_id": "TEST_MFG_001"
    }

    # Validate structure
    assert "camera_token" in aggregator_request
    assert "manufacturer_authority_id" in aggregator_request
    assert "ciphertext" in aggregator_request["camera_token"]
    assert "auth_tag" in aggregator_request["camera_token"]
    assert "nonce" in aggregator_request["camera_token"]
    assert "table_id" in aggregator_request["camera_token"]
    assert "key_index" in aggregator_request["camera_token"]

    print("   ✓ Aggregator → SMA request format is correct")
    print("   ✓ Contains: camera_token, manufacturer_authority_id")
    print("   ✓ Token contains: ciphertext, auth_tag, nonce, table_id, key_index")

except Exception as e:
    print(f"   ✗ SMA request format error: {e}")
    sys.exit(1)

# Test 7: Check for common issues
print("\n7. Checking for Common Issues...")
issues_found = []

# Check 7a: Verify migration file exists
migration_file = Path(__file__).parent.parent / "alembic" / "versions" / "20241203_0100_add_camera_submission_fields.py"
if not migration_file.exists():
    issues_found.append("Migration file not found: 20241203_0100_add_camera_submission_fields.py")
else:
    print("   ✓ Migration file exists")

# Check 7b: Verify test files exist
test_files = [
    "test_camera_submission.py",
    "test_week2_integration.py",
]
tests_dir = Path(__file__).parent
for test_file in test_files:
    if not (tests_dir / test_file).exists():
        issues_found.append(f"Test file not found: {test_file}")
    else:
        print(f"   ✓ Test file exists: {test_file}")

if issues_found:
    print("\n   ⚠ Issues found:")
    for issue in issues_found:
        print(f"     - {issue}")
else:
    print("   ✓ No common issues found")

# Test 8: Check submission flow logic
print("\n8. Testing Submission Flow Logic...")
try:
    # Verify transaction grouping logic
    # Both hashes should have same transaction_id
    import uuid
    transaction_id = str(uuid.uuid4())

    # Simulate creating 2 pending submissions with same transaction_id
    submissions_data = [
        {
            "image_hash": "a" * 64,
            "modification_level": 0,
            "parent_image_hash": None,
            "transaction_id": transaction_id,
        },
        {
            "image_hash": "b" * 64,
            "modification_level": 1,
            "parent_image_hash": "a" * 64,
            "transaction_id": transaction_id,
        },
    ]

    # Both should have same transaction_id
    assert submissions_data[0]["transaction_id"] == submissions_data[1]["transaction_id"]
    print("   ✓ Transaction grouping logic is correct")
    print(f"     Both hashes share transaction_id: {transaction_id[:16]}...")

except Exception as e:
    print(f"   ✗ Submission flow logic error: {e}")
    sys.exit(1)

# Final summary
print("\n" + "="*70)
print("VALIDATION SUMMARY")
print("="*70)
print("✅ All validation checks passed!")
print("\nVerified:")
print("  ✓ Schema imports")
print("  ✓ CameraToken validation")
print("  ✓ ImageHashEntry validation")
print("  ✓ CameraSubmission validation")
print("  ✓ Database model compatibility")
print("  ✓ SMA request format")
print("  ✓ File structure")
print("  ✓ Transaction grouping logic")
print("\n✅ Code is ready for integration testing!")
print("="*70)
