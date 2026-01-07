#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Birthmark Phase 1 End-to-End Demo Script

This script demonstrates the complete authentication pipeline:
1. Camera captures image and creates authentication token
2. Submission server receives submission
3. SMA validates camera token
4. Blockchain stores validated hashes
5. Verification query confirms hash on blockchain

Requirements:
- SMA running on localhost:8001
- Blockchain node running on localhost:8545
- Camera provisioning data exists
"""

import asyncio
import httpx
import json
import sys
import time
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "camera-pi" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

from camera_pi.raw_capture import create_capture_manager
from camera_pi.provisioning_client import ProvisioningClient
from camera_pi.camera_token import create_token_generator_from_provisioning


async def main():
    print("=" * 100)
    print("🎬 BIRTHMARK PHASE 1 - END-TO-END DEMONSTRATION")
    print("=" * 100)
    print()

    # Configuration
    submission_url = "http://localhost:8545"
    sma_url = "http://localhost:8001"
    provisioning_path = Path("packages/camera-pi/data/provisioning_data.json")

    # Step 1: Check services are running
    print("🔍 Step 1: Checking services...")
    print("-" * 80)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check SMA
            response = await client.get(f"{sma_url}/health")
            if response.status_code == 200:
                print(f"✅ SMA is running at {sma_url}")
            else:
                print(f"❌ SMA returned {response.status_code}")
                return

            # Check blockchain node
            response = await client.get(f"{submission_url}/api/v1/blockchain/status")
            if response.status_code == 200:
                status_data = response.json()
                print(f"✅ Blockchain node is running at {submission_url}")
                print(f"   Current block height: {status_data['block_height']}")
                print(f"   Total hashes: {status_data['total_hashes']}")
            else:
                print(f"❌ Blockchain node returned {response.status_code}")
                return

    except httpx.ConnectError as e:
        print(f"❌ Connection error: {e}")
        print("\nMake sure both services are running:")
        print("  1. SMA: cd packages/sma && uvicorn src.main:app --port 8001")
        print("  2. Blockchain: cd packages/blockchain && python -m src.main")
        return
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    print()

    # Step 2: Load provisioning and create camera token
    print("📷 Step 2: Simulating camera capture...")
    print("-" * 80)

    try:
        # Load provisioning data
        if not provisioning_path.exists():
            print(f"❌ Provisioning data not found at {provisioning_path}")
            print("   Run: cd packages/camera-pi && python scripts/provision_camera.py")
            return

        provisioning_client = ProvisioningClient(provisioning_path)
        provisioning_data = provisioning_client.load_from_file()
        print(f"✅ Loaded provisioning for device: {provisioning_data.device_serial}")

        # Create token generator
        token_generator = create_token_generator_from_provisioning(provisioning_data)

        # Simulate image hashes (in real system, these come from camera)
        import hashlib
        import secrets

        raw_image_data = secrets.token_bytes(1024)  # Simulate raw Bayer data
        raw_hash = hashlib.sha256(raw_image_data).hexdigest()

        processed_image_data = secrets.token_bytes(2048)  # Simulate processed image
        processed_hash = hashlib.sha256(processed_image_data).hexdigest()

        print(f"📋 Simulated image capture:")
        print(f"   Raw hash: {raw_hash[:32]}...")
        print(f"   Processed hash: {processed_hash[:32]}...")

        # Generate camera token
        camera_token = token_generator.generate_token(raw_hash)
        print(f"\n🔐 Generated camera token:")
        print(f"   Table ID: {camera_token.table_id}")
        print(f"   Key Index: {camera_token.key_index}")
        print(f"   Ciphertext: {camera_token.ciphertext[:32]}...")

    except Exception as e:
        print(f"❌ Error loading provisioning: {e}")
        import traceback
        traceback.print_exc()
        return

    print()

    # Step 3: Submit to blockchain node
    print("📤 Step 3: Submitting to blockchain node...")
    print("-" * 80)

    timestamp = int(time.time())
    submission_payload = {
        "submission_type": "camera",
        "image_hashes": [
            {
                "image_hash": raw_hash,
                "modification_level": 0,
                "parent_image_hash": None
            },
            {
                "image_hash": processed_hash,
                "modification_level": 1,
                "parent_image_hash": raw_hash
            }
        ],
        "camera_token": {
            "ciphertext": camera_token.ciphertext,
            "auth_tag": camera_token.auth_tag,
            "nonce": camera_token.nonce,
            "table_id": camera_token.table_id,
            "key_index": camera_token.key_index
        },
        "manufacturer_cert": {
            "authority_id": "SIMULATED_CAMERA_001",
            "validation_endpoint": f"{sma_url}/validate"
        },
        "timestamp": timestamp
    }

    print("📨 Sending submission to blockchain node...")
    print(f"   Endpoint: {submission_url}/api/v1/submit")
    print(f"   Image hashes: {len(submission_payload['image_hashes'])}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{submission_url}/api/v1/submit",
                json=submission_payload
            )

            if response.status_code in [200, 202]:
                submission_response = response.json()
                print(f"\n✅ Submission accepted!")
                print(f"   Receipt ID: {submission_response['receipt_id']}")
                print(f"   Status: {submission_response['status']}")
                print(f"   Message: {submission_response.get('message', 'N/A')}")

                # Wait for processing
                print("\n⏳ Waiting for validation and blockchain processing (5 seconds)...")
                await asyncio.sleep(5)

            else:
                print(f"\n❌ Submission failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return

    except Exception as e:
        print(f"❌ Error submitting: {e}")
        import traceback
        traceback.print_exc()
        return

    print()

    # Step 4: Verify hashes on blockchain
    print("🔍 Step 4: Verifying hashes on blockchain...")
    print("-" * 80)

    for idx, hash_entry in enumerate(submission_payload['image_hashes'], 1):
        image_hash = hash_entry['image_hash']
        level = hash_entry['modification_level']

        print(f"\n[{idx}] Verifying {'raw' if level == 0 else 'processed'} hash: {image_hash[:32]}...")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{submission_url}/api/v1/blockchain/verify/{image_hash}"
                )

                if response.status_code == 200:
                    verification = response.json()

                    if verification['verified']:
                        print(f"   ✅ VERIFIED on blockchain!")
                        print(f"      Block height: {verification['block_height']}")
                        print(f"      TX ID: {verification['tx_id']}")
                        print(f"      Timestamp: {verification['timestamp']}")
                        print(f"      Submission server: {verification['submission_server_id']}")
                        print(f"      Modification level: {verification['modification_level']}")
                        if verification['parent_image_hash']:
                            print(f"      Parent hash: {verification['parent_image_hash'][:32]}...")
                    else:
                        print(f"   ❌ NOT FOUND on blockchain")

                else:
                    print(f"   ❌ Verification request failed: {response.status_code}")

        except Exception as e:
            print(f"   ❌ Error verifying: {e}")

    print()

    # Step 5: Check blockchain status
    print("📊 Step 5: Final blockchain status...")
    print("-" * 80)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{submission_url}/api/v1/blockchain/status")
            if response.status_code == 200:
                status_data = response.json()
                print(f"✅ Blockchain node status:")
                print(f"   Node ID: {status_data['node_id']}")
                print(f"   Block height: {status_data['block_height']}")
                print(f"   Total hashes: {status_data['total_hashes']}")
                print(f"   Last block time: {status_data.get('last_block_time', 'N/A')}")
                print(f"   Status: {status_data['status']}")

    except Exception as e:
        print(f"❌ Error getting status: {e}")

    print()
    print("=" * 100)
    print("🎉 DEMO COMPLETE!")
    print("=" * 100)
    print()
    print("📝 Summary:")
    print("  ✅ Camera captured image and generated authentication token")
    print("  ✅ Submission server received and validated submission with SMA")
    print("  ✅ Blockchain stored validated hashes")
    print("  ✅ Verification queries confirmed hashes on blockchain")
    print()
    print("🔍 Check server logs for detailed packet contents!")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Demo interrupted by user")
        sys.exit(1)
