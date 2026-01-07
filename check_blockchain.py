#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Check Birthmark blockchain status and recent blocks.
"""

import requests
import json

def check_status():
    """Query blockchain status."""
    url = "http://localhost:8545/api/v1/blockchain/status"

    try:
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            status = response.json()

            print("=" * 60)
            print("BIRTHMARK BLOCKCHAIN STATUS")
            print("=" * 60)
            print(f"Node ID: {status.get('node_id')}")
            print(f"Blockchain Height: {status.get('height')} blocks")
            print(f"Total Transactions: {status.get('transaction_count')}")
            print(f"Total Submissions: {status.get('submission_count')}")
            print(f"Pending Validations: {status.get('pending_validations')}")
            print(f"Status: {status.get('status')}")
            print("=" * 60)

            if status.get('height', 0) > 0:
                print("\n✅ Blockchain is operational with data")
                return True
            else:
                print("\n⚠️  Blockchain is running but has no blocks yet")
                return False
        else:
            print(f"Error: HTTP {response.status_code}")
            print(response.text)
            return False

    except requests.ConnectionError:
        print("❌ Cannot connect to blockchain node at http://localhost:8545")
        print("   Make sure the Birthmark Media Registry is running")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def get_recent_blocks():
    """Get recent blocks to see what was added."""
    url = "http://localhost:8545/api/v1/blockchain/blocks/recent"

    try:
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            blocks = response.json().get('blocks', [])

            if blocks:
                print("\n" + "=" * 60)
                print("RECENT BLOCKS")
                print("=" * 60)

                for block in blocks[:5]:  # Show last 5 blocks
                    print(f"\nBlock #{block.get('height')}")
                    print(f"  Hash: {block.get('hash', '')[:32]}...")
                    print(f"  Timestamp: {block.get('timestamp')}")
                    print(f"  Transactions: {len(block.get('transactions', []))}")

                    for i, tx in enumerate(block.get('transactions', [])[:3], 1):
                        print(f"    TX{i}: {tx.get('image_hash', '')[:16]}... (Level {tx.get('modification_level')})")

            else:
                print("\n⚠️  No blocks found")

    except Exception as e:
        print(f"\nCouldn't fetch recent blocks: {e}")


if __name__ == "__main__":
    if check_status():
        get_recent_blocks()
