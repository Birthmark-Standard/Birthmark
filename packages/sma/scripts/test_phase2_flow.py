#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Test Phase 2 provisioning and validation flow.

This script simulates the iOS app to test:
1. Device provisioning (get certificate + key tables)
2. Certificate bundle creation (sign with device key)
3. Certificate bundle validation (SMA validation)

Usage:
    # Start SMA server in another terminal:
    # uvicorn src.main:app --port 8001 --reload

    python scripts/test_phase2_flow.py
"""

import sys
import hashlib
import time
import base64
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


def generate_device_secret() -> str:
    """Generate a random device secret (simulating iOS)."""
    random_data = hashlib.sha256(str(time.time()).encode()).digest()
    return random_data.hex()


def create_canonical_data(image_hash: str, camera_cert: str, timestamp: int, gps_hash: str = None) -> bytes:
    """Create canonical data format for ECDSA signature (must match iOS and SMA)."""
    canonical = ""
    canonical += image_hash.lower() + "\n"
    canonical += camera_cert + "\n"
    canonical += str(timestamp) + "\n"
    canonical += (gps_hash.lower() if gps_hash else "") + "\n"
    return canonical.encode('utf-8')


async def test_provisioning(sma_url: str, device_serial: str, device_secret: str):
    """Test Phase 2 device provisioning."""
    print("\n" + "="*70)
    print("TEST 1: Device Provisioning")
    print("="*70)

    print(f"\nDevice Serial: {device_serial}")
    print(f"Device Secret: {device_secret[:16]}...")

    # Call provisioning endpoint
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{sma_url}/api/v1/devices/provision",
            json={
                "device_serial": device_serial,
                "device_family": "iOS",
                "device_secret": device_secret,
            },
            timeout=30.0
        )

        if response.status_code not in [200, 201]:
            print(f"❌ Provisioning failed: {response.status_code}")
            print(response.text)
            return None

        data = response.json()

        print(f"\n✓ Provisioning successful!")
        print(f"  Certificate length: {len(data['device_certificate'])} chars")
        print(f"  Private key length: {len(data['device_private_key'])} chars")
        print(f"  Key tables received: {len(data['key_tables'])}")
        print(f"  Keys per table: {len(data['key_tables'][0])}")
        print(f"  Key table indices: {data['key_table_indices']}")

        return data


async def test_validation(
    sma_url: str,
    device_cert_pem: str,
    device_key_pem: str,
    device_secret: str
):
    """Test Phase 2 certificate bundle validation."""
    print("\n" + "="*70)
    print("TEST 2: Certificate Bundle Validation")
    print("="*70)

    # Generate test image hash
    test_image_data = b"fake_image_data_" + str(time.time()).encode()
    image_hash = hashlib.sha256(test_image_data).hexdigest()
    timestamp = int(time.time())

    print(f"\nTest Image Hash: {image_hash[:16]}...")
    print(f"Timestamp: {timestamp}")

    # Base64-encode the device certificate for transmission
    device_cert_b64 = base64.b64encode(device_cert_pem.encode()).decode()

    # Load device private key
    device_private_key = serialization.load_pem_private_key(
        device_key_pem.encode(),
        password=None
    )

    # Create canonical data (uses base64-encoded cert, matching SMA expectation)
    canonical_data = create_canonical_data(image_hash, device_cert_b64, timestamp)

    print(f"\nCanonical data length: {len(canonical_data)} bytes")
    print(f"Canonical data (first 100 chars):")
    print(f"  {repr(canonical_data[:100])}")

    # Sign with device private key (ECDSA P-256)
    signature = device_private_key.sign(
        canonical_data,
        ec.ECDSA(hashes.SHA256())
    )
    signature_b64 = base64.b64encode(signature).decode()

    print(f"\nSignature length: {len(signature)} bytes")
    print(f"Signature (base64): {signature_b64[:50]}...")

    # Call validation endpoint
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{sma_url}/validate-cert",
            json={
                "camera_cert": device_cert_b64,  # Base64-encoded PEM
                "image_hash": image_hash,
                "timestamp": timestamp,
                "gps_hash": None,
                "bundle_signature": signature_b64,
            },
            timeout=30.0
        )

        if response.status_code != 200:
            print(f"\n❌ Validation request failed: {response.status_code}")
            print(response.text)
            return False

        data = response.json()

        print(f"\n{'✓' if data['valid'] else '❌'} Validation result: {data['message']}")

        return data['valid']


async def test_invalid_signature(
    sma_url: str,
    device_cert_pem: str,
    device_key_pem: str
):
    """Test that invalid signatures are rejected."""
    print("\n" + "="*70)
    print("TEST 3: Invalid Signature Detection")
    print("="*70)

    # Generate test image hash
    test_image_data = b"fake_image_data_2_" + str(time.time()).encode()
    image_hash = hashlib.sha256(test_image_data).hexdigest()
    timestamp = int(time.time())

    # Base64-encode the device certificate
    device_cert_b64 = base64.b64encode(device_cert_pem.encode()).decode()

    # Load device private key
    device_private_key = serialization.load_pem_private_key(
        device_key_pem.encode(),
        password=None
    )

    # Create canonical data with WRONG timestamp (use base64-encoded cert)
    wrong_canonical = create_canonical_data(image_hash, device_cert_b64, timestamp + 1000)

    # Sign with wrong data
    signature = device_private_key.sign(
        wrong_canonical,
        ec.ECDSA(hashes.SHA256())
    )
    signature_b64 = base64.b64encode(signature).decode()

    print(f"\nSending bundle with mismatched timestamp...")
    print(f"  Image hash: {image_hash[:16]}...")
    print(f"  Canonical timestamp: {timestamp + 1000}")
    print(f"  Request timestamp: {timestamp}")

    # Call validation endpoint with mismatched data
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{sma_url}/validate-cert",
            json={
                "camera_cert": device_cert_b64,  # Base64-encoded PEM
                "image_hash": image_hash,
                "timestamp": timestamp,  # Different from signed timestamp
                "gps_hash": None,
                "bundle_signature": signature_b64,
            },
            timeout=30.0
        )

        if response.status_code != 200:
            print(f"\n❌ Validation request failed: {response.status_code}")
            print(response.text)
            return False

        data = response.json()

        # Should FAIL validation
        if not data['valid']:
            print(f"\n✓ Invalid signature correctly rejected: {data['message']}")
            return True
        else:
            print(f"\n❌ Invalid signature was accepted! Security issue!")
            return False


async def main():
    """Run all tests."""
    sma_url = "http://localhost:8001"

    print("\n" + "="*70)
    print("Phase 2 Provisioning & Validation Flow Test")
    print("="*70)
    print(f"\nSMA URL: {sma_url}")

    # Check if SMA is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{sma_url}/health", timeout=5.0)
            if response.status_code != 200:
                print("\n❌ SMA server not healthy")
                print("Please start SMA server:")
                print("  cd packages/sma")
                print("  uvicorn src.main:app --port 8001 --reload")
                return
    except Exception as e:
        print(f"\n❌ Cannot connect to SMA at {sma_url}")
        print(f"Error: {e}")
        print("\nPlease start SMA server:")
        print("  cd packages/sma")
        print("  uvicorn src.main:app --port 8001 --reload")
        return

    print("✓ SMA server is running")

    # Generate test device
    device_serial = f"TEST-iOS-{int(time.time())}"
    device_secret = generate_device_secret()

    # Test 1: Provisioning
    provision_result = await test_provisioning(sma_url, device_serial, device_secret)
    if not provision_result:
        print("\n❌ Provisioning test failed, aborting")
        return

    device_cert_pem = provision_result['device_certificate']
    device_key_pem = provision_result['device_private_key']

    # Test 2: Valid bundle validation
    valid_result = await test_validation(sma_url, device_cert_pem, device_key_pem, device_secret)
    if not valid_result:
        print("\n❌ Validation test failed")
        return

    # Test 3: Invalid signature detection
    invalid_result = await test_invalid_signature(sma_url, device_cert_pem, device_key_pem)
    if not invalid_result:
        print("\n❌ Invalid signature test failed")
        return

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print("✓ Test 1: Device Provisioning - PASSED")
    print("✓ Test 2: Valid Certificate Bundle - PASSED")
    print("✓ Test 3: Invalid Signature Detection - PASSED")
    print("\n✓ All tests passed! Phase 2 backend is working correctly.")
    print("="*70)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
