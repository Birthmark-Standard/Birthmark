#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Mock Camera Client - Simulates Raspberry Pi camera submissions for testing

This script simulates a camera device submitting 2-hash bundles to the aggregator:
- Raw Bayer hash (modification_level=0)
- Processed JPEG hash (modification_level=1)

Usage:
    # Single capture
    python scripts/mock_camera_client.py

    # Continuous capture (10 images)
    python scripts/mock_camera_client.py --continuous 10

    # Load testing (250 images)
    python scripts/mock_camera_client.py --continuous 250 --interval 0.1
"""

import asyncio
import argparse
import hashlib
import secrets
import time
from typing import Dict, Any, Optional
import httpx


# Configuration
AGGREGATOR_URL = "http://localhost:8545"
MANUFACTURER_AUTHORITY_ID = "TEST_MFG_001"
SMA_VALIDATION_ENDPOINT = "http://localhost:8001/validate"


def generate_mock_hashes() -> tuple[str, str]:
    """
    Generate mock image hashes simulating raw Bayer and processed JPEG.

    Returns:
        tuple: (raw_hash, processed_hash)
    """
    # Simulate raw Bayer data hash
    raw_data = secrets.token_bytes(24 * 1024 * 1024)  # ~24MB raw sensor data
    raw_hash = hashlib.sha256(raw_data).hexdigest()

    # Simulate processed JPEG hash (different from raw)
    processed_data = secrets.token_bytes(3 * 1024 * 1024)  # ~3MB JPEG
    processed_hash = hashlib.sha256(processed_data).hexdigest()

    return raw_hash, processed_hash


def generate_mock_camera_token() -> Dict[str, Any]:
    """
    Generate mock camera token with AES-GCM components.

    Phase 1: Uses placeholder values since no real TPM encryption.
    Phase 2: Will use real LetsTrust TPM encryption.

    Returns:
        dict: CameraToken structure
    """
    return {
        "ciphertext": secrets.token_hex(64),  # 128 hex chars
        "auth_tag": secrets.token_hex(16),    # 32 hex chars (16 bytes)
        "nonce": secrets.token_hex(12),       # 24 hex chars (12 bytes)
        "table_id": 0,                        # Use table 0 (must exist in SMA)
        "key_index": 0,                       # Use key index 0
    }


async def submit_camera_capture(
    raw_hash: str,
    processed_hash: str,
    camera_token: Dict[str, Any],
    timestamp: int,
) -> Optional[str]:
    """
    Submit 2-hash camera bundle to aggregator.

    Args:
        raw_hash: SHA-256 of raw Bayer data
        processed_hash: SHA-256 of processed JPEG
        camera_token: Camera token structure
        timestamp: Unix timestamp

    Returns:
        str: Receipt ID if successful, None otherwise
    """
    submission = {
        "submission_type": "camera",
        "image_hashes": [
            {
                "image_hash": raw_hash,
                "modification_level": 0,
                "parent_image_hash": None,
            },
            {
                "image_hash": processed_hash,
                "modification_level": 1,
                "parent_image_hash": raw_hash,
            },
        ],
        "camera_token": camera_token,
        "manufacturer_cert": {
            "authority_id": MANUFACTURER_AUTHORITY_ID,
            "validation_endpoint": SMA_VALIDATION_ENDPOINT,
        },
        "timestamp": timestamp,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{AGGREGATOR_URL}/api/v1/submit",
                json=submission,
            )

            if response.status_code == 202:
                data = response.json()
                print(f"✓ Submission accepted")
                print(f"  Receipt ID: {data['receipt_id']}")
                print(f"  Status: {data['status']}")
                print(f"  Raw hash: {raw_hash[:16]}...")
                print(f"  Processed hash: {processed_hash[:16]}...")
                return data['receipt_id']
            else:
                print(f"✗ Submission failed: {response.status_code}")
                print(f"  Response: {response.text}")
                return None

    except httpx.ConnectError:
        print(f"✗ Cannot connect to aggregator at {AGGREGATOR_URL}")
        print(f"  Start aggregator with: cd packages/blockchain && uvicorn src.main:app --port 8545")
        return None
    except Exception as e:
        print(f"✗ Error submitting: {e}")
        return None


async def verify_hash(image_hash: str) -> bool:
    """
    Query aggregator to verify hash status.

    Args:
        image_hash: SHA-256 hash to verify

    Returns:
        bool: True if verified on blockchain, False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{AGGREGATOR_URL}/api/v1/verify/{image_hash}"
            )

            if response.status_code == 200:
                data = response.json()

                if data["verified"]:
                    print(f"✓ Hash verified on blockchain")
                    print(f"  Block height: {data.get('block_height', 'N/A')}")
                    print(f"  Timestamp: {data.get('timestamp', 'N/A')}")
                    return True
                elif data.get("status") == "pending":
                    print(f"⚠ Hash pending validation/batching")
                    return False
                else:
                    print(f"✗ Hash not found")
                    return False
            else:
                print(f"✗ Verification query failed: {response.status_code}")
                return False

    except Exception as e:
        print(f"✗ Error verifying: {e}")
        return False


async def capture_and_verify() -> bool:
    """
    Simulate single camera capture with verification.

    Returns:
        bool: True if submission and verification successful
    """
    print("\n" + "="*60)
    print("MOCK CAMERA - Single Capture")
    print("="*60)

    # Step 1: Generate mock hashes
    print("\n[1/4] Generating mock image hashes...")
    raw_hash, processed_hash = generate_mock_hashes()
    print(f"  Raw hash: {raw_hash}")
    print(f"  Processed hash: {processed_hash}")

    # Step 2: Generate mock camera token
    print("\n[2/4] Generating mock camera token...")
    camera_token = generate_mock_camera_token()
    print(f"  Table ID: {camera_token['table_id']}")
    print(f"  Key Index: {camera_token['key_index']}")
    print(f"  Ciphertext: {camera_token['ciphertext'][:32]}...")

    # Step 3: Submit to aggregator
    print("\n[3/4] Submitting to aggregator...")
    timestamp = int(time.time())
    receipt_id = await submit_camera_capture(
        raw_hash=raw_hash,
        processed_hash=processed_hash,
        camera_token=camera_token,
        timestamp=timestamp,
    )

    if not receipt_id:
        print("\n❌ Submission failed")
        return False

    # Step 4: Wait and verify
    print("\n[4/4] Waiting 2 seconds for validation...")
    await asyncio.sleep(2)

    print("\nVerifying raw hash...")
    raw_verified = await verify_hash(raw_hash)

    print("\nVerifying processed hash...")
    processed_verified = await verify_hash(processed_hash)

    # Summary
    print("\n" + "="*60)
    print("CAPTURE SUMMARY")
    print("="*60)
    print(f"Receipt ID: {receipt_id}")
    print(f"Raw hash verified: {'✓' if raw_verified else '⚠ Pending'}")
    print(f"Processed hash verified: {'✓' if processed_verified else '⚠ Pending'}")
    print("="*60)

    return receipt_id is not None


async def continuous_capture(count: int, interval: float = 1.0) -> Dict[str, int]:
    """
    Simulate continuous camera captures for load testing.

    Args:
        count: Number of captures to simulate
        interval: Seconds between captures

    Returns:
        dict: Statistics (submitted, failed, verified)
    """
    print("\n" + "="*60)
    print(f"MOCK CAMERA - Continuous Capture ({count} images)")
    print("="*60)

    stats = {
        "submitted": 0,
        "failed": 0,
        "verified": 0,
    }

    start_time = time.time()

    for i in range(count):
        print(f"\n--- Capture {i+1}/{count} ---")

        # Generate and submit
        raw_hash, processed_hash = generate_mock_hashes()
        camera_token = generate_mock_camera_token()
        timestamp = int(time.time())

        receipt_id = await submit_camera_capture(
            raw_hash=raw_hash,
            processed_hash=processed_hash,
            camera_token=camera_token,
            timestamp=timestamp,
        )

        if receipt_id:
            stats["submitted"] += 1
        else:
            stats["failed"] += 1

        # Wait before next capture
        if i < count - 1:  # Don't wait after last capture
            await asyncio.sleep(interval)

    elapsed = time.time() - start_time

    # Final summary
    print("\n" + "="*60)
    print("CONTINUOUS CAPTURE SUMMARY")
    print("="*60)
    print(f"Total captures: {count}")
    print(f"Submitted: {stats['submitted']}")
    print(f"Failed: {stats['failed']}")
    print(f"Elapsed time: {elapsed:.2f} seconds")
    print(f"Average rate: {count/elapsed:.2f} captures/second")
    print("="*60)

    # Wait for batching
    print("\n⏳ Waiting 30 seconds for batching service...")
    await asyncio.sleep(30)

    # Verify a sample (first 5 hashes)
    print("\n📊 Verifying sample hashes...")
    # Note: We don't have the hashes from the loop anymore
    # In production, we'd store them for verification
    print("  (Verification would check first 5 submitted hashes)")

    return stats


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Mock camera client for testing Birthmark submission flow"
    )
    parser.add_argument(
        "--continuous",
        type=int,
        metavar="COUNT",
        help="Continuous capture mode (submit COUNT images)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        metavar="SECONDS",
        help="Interval between captures in continuous mode (default: 1.0)",
    )

    args = parser.parse_args()

    if args.continuous:
        await continuous_capture(args.continuous, args.interval)
    else:
        await capture_and_verify()


if __name__ == "__main__":
    asyncio.run(main())
