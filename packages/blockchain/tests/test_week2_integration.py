"""
Integration test for Week 2 - Camera Submission Flow

Tests the complete flow:
1. Camera submits 2-hash bundle to aggregator
2. Aggregator validates with SMA
3. Hashes are queued for batching

Requirements:
- Aggregator server running on http://localhost:8545
- SMA server running on http://localhost:8001
- PostgreSQL database initialized with migrations
"""

import asyncio
import httpx
import time
from typing import Dict, Any


# Test data
SAMPLE_CAMERA_SUBMISSION = {
    "submission_type": "camera",
    "image_hashes": [
        {
            "image_hash": "a" * 64,  # Raw hash
            "modification_level": 0,
            "parent_image_hash": None,
        },
        {
            "image_hash": "b" * 64,  # Processed hash
            "modification_level": 1,
            "parent_image_hash": "a" * 64,
        },
    ],
    "camera_token": {
        "ciphertext": "c" * 128,
        "auth_tag": "d" * 32,
        "nonce": "e" * 24,
        "table_id": 0,  # Must exist in SMA key tables
        "key_index": 0,
    },
    "manufacturer_cert": {
        "authority_id": "TEST_MFG_001",
        "validation_endpoint": "http://localhost:8001/validate",
    },
    "timestamp": int(time.time()),
}

AGGREGATOR_URL = "http://localhost:8545"
SMA_URL = "http://localhost:8001"


async def test_sma_health():
    """Test 1: Verify SMA is running and healthy."""
    print("\n" + "="*60)
    print("TEST 1: SMA Health Check")
    print("="*60)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{SMA_URL}/health")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ SMA is healthy")
                print(f"  Total devices: {data['total_devices']}")
                print(f"  Total tables: {data['total_tables']}")
                return True
            else:
                print(f"✗ SMA returned {response.status_code}")
                return False

    except httpx.ConnectError:
        print(f"✗ Cannot connect to SMA at {SMA_URL}")
        print(f"  Start SMA with: cd packages/sma && python -m src.main")
        return False


async def test_aggregator_health():
    """Test 2: Verify aggregator is running."""
    print("\n" + "="*60)
    print("TEST 2: Aggregator Health Check")
    print("="*60)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{AGGREGATOR_URL}/")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ Aggregator is running")
                print(f"  Service: {data.get('service', 'Unknown')}")
                print(f"  Node ID: {data.get('node_id', 'Unknown')}")
                return True
            else:
                print(f"✗ Aggregator returned {response.status_code}")
                return False

    except httpx.ConnectError:
        print(f"✗ Cannot connect to aggregator at {AGGREGATOR_URL}")
        print(f"  Start aggregator with: cd packages/blockchain && uvicorn src.main:app --port 8545")
        return False


async def test_direct_sma_validation():
    """Test 3: Test SMA validation endpoint directly."""
    print("\n" + "="*60)
    print("TEST 3: Direct SMA Validation")
    print("="*60)

    validation_request = {
        "camera_token": SAMPLE_CAMERA_SUBMISSION["camera_token"],
        "manufacturer_authority_id": SAMPLE_CAMERA_SUBMISSION["manufacturer_cert"]["authority_id"]
    }

    print(f"Sending validation request to {SMA_URL}/validate")
    print(f"  table_id: {validation_request['camera_token']['table_id']}")
    print(f"  key_index: {validation_request['camera_token']['key_index']}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{SMA_URL}/validate",
                json=validation_request
            )

            if response.status_code == 200:
                data = response.json()
                if data["valid"]:
                    print(f"✓ SMA validation PASSED")
                    print(f"  Message: {data.get('message', 'N/A')}")
                    return True
                else:
                    print(f"✗ SMA validation FAILED")
                    print(f"  Message: {data.get('message', 'N/A')}")
                    return False
            else:
                print(f"✗ SMA returned {response.status_code}")
                print(f"  Response: {response.text}")
                return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_camera_submission():
    """Test 4: Submit camera bundle to aggregator."""
    print("\n" + "="*60)
    print("TEST 4: Camera Submission to Aggregator")
    print("="*60)

    print(f"Submitting 2-hash bundle:")
    print(f"  Raw hash: {SAMPLE_CAMERA_SUBMISSION['image_hashes'][0]['image_hash'][:16]}...")
    print(f"  Processed hash: {SAMPLE_CAMERA_SUBMISSION['image_hashes'][1]['image_hash'][:16]}...")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{AGGREGATOR_URL}/api/v1/submit",
                json=SAMPLE_CAMERA_SUBMISSION
            )

            if response.status_code == 202:
                data = response.json()
                print(f"✓ Submission accepted")
                print(f"  Receipt ID: {data['receipt_id']}")
                print(f"  Status: {data['status']}")
                print(f"  Message: {data['message']}")
                return data['receipt_id']
            else:
                print(f"✗ Submission failed with {response.status_code}")
                print(f"  Response: {response.text}")
                return None

    except Exception as e:
        print(f"✗ Error: {e}")
        return None


async def test_verification(image_hash: str):
    """Test 5: Verify image hash in blockchain."""
    print("\n" + "="*60)
    print("TEST 5: Verification Query")
    print("="*60)

    print(f"Querying hash: {image_hash[:16]}...")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{AGGREGATOR_URL}/api/v1/verify/{image_hash}"
            )

            if response.status_code == 200:
                data = response.json()
                print(f"Status: {data['verified']}")

                if data["verified"]:
                    print(f"✓ Image verified on blockchain")
                    print(f"  Block height: {data.get('block_height', 'N/A')}")
                    print(f"  Timestamp: {data.get('timestamp', 'N/A')}")
                elif data.get("status") == "pending":
                    print(f"⚠ Image pending (not yet batched)")
                    return "pending"
                else:
                    print(f"✗ Image not found")
                    return False

                return data["verified"]
            else:
                print(f"✗ Verification failed with {response.status_code}")
                return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def main():
    """Run all integration tests."""
    print("\n" + "="*60)
    print("BIRTHMARK WEEK 2 INTEGRATION TESTS")
    print("2-Hash Camera Submission with SMA Validation")
    print("="*60)

    # Test 1: SMA health
    sma_ok = await test_sma_health()
    if not sma_ok:
        print("\n❌ SMA is not running. Please start SMA first.")
        return False

    # Test 2: Aggregator health
    agg_ok = await test_aggregator_health()
    if not agg_ok:
        print("\n❌ Aggregator is not running. Please start aggregator first.")
        return False

    # Test 3: Direct SMA validation
    sma_valid = await test_direct_sma_validation()
    if not sma_valid:
        print("\n❌ SMA validation failed. Check SMA key tables.")
        return False

    # Test 4: Camera submission
    receipt_id = await test_camera_submission()
    if not receipt_id:
        print("\n❌ Camera submission failed.")
        return False

    # Wait for validation to complete
    print("\n⏳ Waiting 2 seconds for inline validation...")
    await asyncio.sleep(2)

    # Test 5: Verification
    raw_hash = SAMPLE_CAMERA_SUBMISSION["image_hashes"][0]["image_hash"]
    verified = await test_verification(raw_hash)

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"SMA Health: {'✓' if sma_ok else '✗'}")
    print(f"Aggregator Health: {'✓' if agg_ok else '✗'}")
    print(f"SMA Validation: {'✓' if sma_valid else '✗'}")
    print(f"Camera Submission: {'✓' if receipt_id else '✗'}")
    print(f"Verification: {'✓' if verified == True else '⚠ Pending' if verified == 'pending' else '✗'}")

    all_passed = sma_ok and agg_ok and sma_valid and receipt_id and (verified == True or verified == "pending")

    if all_passed:
        print("\n✅ All tests passed! Week 2 integration is working.")
    else:
        print("\n❌ Some tests failed. Check the output above.")

    return all_passed


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)
