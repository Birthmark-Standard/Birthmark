#!/usr/bin/env python3
"""Test SSA validation endpoint"""

import json
import hashlib
import requests

def compute_file_hash(filepath):
    """Compute SHA-256 hash of file"""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def main():
    print("Testing SSA Validation Endpoint")
    print("=" * 60)
    print()

    # 1. Compute baseline hash
    print("1. Computing baseline hash...")
    baseline_hash = compute_file_hash("test_wrapper.py")
    print(f"   Baseline hash: {baseline_hash}")
    print()

    # 2. Load certificate
    print("2. Loading certificate...")
    with open("provisioned_software/test-wrapper-001/software_certificate.pem") as f:
        cert = f.read()
    print("   Certificate loaded")
    print()

    # 3. Test validation with valid version
    print("3. Testing validation with valid version 1.0.0...")
    response = requests.post(
        "http://localhost:8001/api/v1/validate/software",
        json={
            "software_certificate": cert,
            "current_wrapper_hash": baseline_hash,
            "version": "1.0.0"
        }
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    print()

    # 4. Test with invalid version
    print("4. Testing validation with invalid version 2.0.0 (should fail)...")
    response = requests.post(
        "http://localhost:8001/api/v1/validate/software",
        json={
            "software_certificate": cert,
            "current_wrapper_hash": baseline_hash,
            "version": "2.0.0"
        }
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    print()

    # 5. Test adding new version
    print("5. Adding version 1.1.0 to valid versions...")
    response = requests.post(
        "http://localhost:8001/api/v1/versions/add",
        json={
            "software_id": "Test-Wrapper-001",
            "version": "1.1.0"
        }
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    print()

    # 6. Test with wrong hash
    print("6. Testing validation with wrong hash (should fail)...")
    wrong_hash = "0" * 64
    response = requests.post(
        "http://localhost:8001/api/v1/validate/software",
        json={
            "software_certificate": cert,
            "current_wrapper_hash": wrong_hash,
            "version": "1.0.0"
        }
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    print()

    # 7. Test health endpoint
    print("7. Testing health endpoint...")
    response = requests.get("http://localhost:8001/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    print()

    print("=" * 60)
    print("Testing complete!")
    print()

if __name__ == "__main__":
    main()
