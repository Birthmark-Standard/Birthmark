#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Quick script to verify a hash on the Birthmark blockchain.
Usage: python verify_hash.py <hash>
"""

import sys
import requests

def verify_hash(image_hash):
    """Query the blockchain to verify a hash."""
    url = f"http://localhost:8545/api/v1/blockchain/verify/{image_hash}"

    try:
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()

            if data.get('verified'):
                print(f"✅ VERIFIED on blockchain!")
                print(f"   Hash: {image_hash[:32]}...")
                print(f"   Modification Level: {data.get('modification_level')}")
                print(f"   Timestamp: {data.get('timestamp')}")
                print(f"   Block Height: {data.get('block_height')}")
                print(f"   Transaction ID: {data.get('tx_id')}")
                if data.get('owner_hash'):
                    print(f"   Owner Hash: {data.get('owner_hash')[:32]}...")
            else:
                print(f"❌ NOT VERIFIED - Hash not found on blockchain")
                print(f"   Hash: {image_hash}")
        else:
            print(f"Error: HTTP {response.status_code}")
            print(response.text)

    except requests.ConnectionError:
        print("❌ Cannot connect to blockchain node at http://localhost:8545")
        print("   Make sure the Birthmark Media Registry is running")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python verify_hash.py <hash>")
        print("\nExample:")
        print("python verify_hash.py ca2e22ffc93e2454f9b7a8f3c5b6d4e8a1f2c3d4e5f6a7b8c9d0e1f2a3b4c5d6")
        sys.exit(1)

    verify_hash(sys.argv[1])
