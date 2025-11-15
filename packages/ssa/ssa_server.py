#!/usr/bin/env python3
"""SSA validation server for software certificate validation"""

from flask import Flask, request, jsonify
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from datetime import datetime
import json
import os
import hashlib

app = Flask(__name__)

# Load provisioned software registry
PROVISIONED_SOFTWARE = {}


def load_registry():
    """Load all provisioned software data"""
    registry_dir = "./provisioned_software"
    if not os.path.exists(registry_dir):
        print("[SSA] Warning: No provisioned_software directory found")
        return

    for software_dir in os.listdir(registry_dir):
        data_path = f"{registry_dir}/{software_dir}/provisioning_data.json"
        if os.path.exists(data_path):
            with open(data_path) as f:
                data = json.load(f)
                PROVISIONED_SOFTWARE[data["software_id"]] = data
                print(f"[SSA] Loaded software: {data['software_id']} (v{data['version']})")


def compute_versioned_hash(baseline_hash: str, version: str) -> str:
    """Derive version-specific hash from baseline hash and version string"""
    hasher = hashlib.sha256()
    hasher.update(baseline_hash.encode())
    hasher.update(version.encode())
    return hasher.hexdigest()


# Load registry on startup
print("=" * 60)
print("SSA Validation Server - Starting")
print("=" * 60)
load_registry()
print(f"[SSA] Loaded {len(PROVISIONED_SOFTWARE)} provisioned software entries")
print("=" * 60)
print()


@app.route("/api/v1/validate/software", methods=["POST"])
def validate_software():
    """
    Validate software certificate and integrity

    Expected body:
    {
        "software_certificate": "<PEM encoded certificate>",
        "current_wrapper_hash": "<SHA-256 hash of wrapper baseline>",
        "version": "<version string>"
    }
    """
    try:
        data = request.get_json()
        cert_pem = data["software_certificate"]
        current_baseline_hash = data["current_wrapper_hash"]
        version = data["version"]

        # Parse certificate
        cert = x509.load_pem_x509_certificate(
            cert_pem.encode(),
            backend=default_backend()
        )
        software_id = cert.subject.get_attributes_for_oid(
            x509.oid.NameOID.COMMON_NAME
        )[0].value

        # Check if software is registered
        if software_id not in PROVISIONED_SOFTWARE:
            return jsonify({
                "validation_result": "FAIL",
                "reason": "Software not registered",
                "software_id": software_id,
                "timestamp": datetime.utcnow().isoformat()
            }), 400

        # Verify certificate chain (simplified for POC)
        # In production: full chain validation against SSA root

        # Check certificate expiry
        if cert.not_valid_after_utc < datetime.now(cert.not_valid_after_utc.tzinfo):
            return jsonify({
                "validation_result": "FAIL",
                "reason": "Certificate expired",
                "software_id": software_id,
                "timestamp": datetime.utcnow().isoformat()
            }), 400

        # Verify version is in valid versions list
        provisioned_data = PROVISIONED_SOFTWARE[software_id]
        if version not in provisioned_data.get("valid_versions", []):
            return jsonify({
                "validation_result": "FAIL",
                "reason": f"Version {version} not authorized",
                "valid_versions": provisioned_data.get("valid_versions", []),
                "software_id": software_id,
                "timestamp": datetime.utcnow().isoformat()
            }), 400

        # Compute expected versioned hash from stored baseline
        expected_hash = compute_versioned_hash(
            provisioned_data["baseline_hash"],
            version
        )

        # Compute actual versioned hash from provided baseline
        actual_hash = compute_versioned_hash(current_baseline_hash, version)

        if actual_hash != expected_hash:
            return jsonify({
                "validation_result": "FAIL",
                "reason": "Wrapper integrity check failed",
                "software_id": software_id,
                "timestamp": datetime.utcnow().isoformat()
            }), 400

        # All checks passed
        return jsonify({
            "validation_result": "PASS",
            "software_id": software_id,
            "version": version,
            "authority": provisioned_data["authority"],
            "supported_editors": provisioned_data.get("supported_editors", []),
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except KeyError as e:
        return jsonify({
            "validation_result": "FAIL",
            "reason": f"Missing required field: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }), 400
    except Exception as e:
        return jsonify({
            "validation_result": "FAIL",
            "reason": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@app.route("/api/v1/versions/add", methods=["POST"])
def add_valid_version():
    """
    Add a new valid version for existing software

    Expected body:
    {
        "software_id": "<registered software ID>",
        "version": "<new version string>"
    }
    """
    try:
        data = request.get_json()
        software_id = data["software_id"]
        new_version = data["version"]

        if software_id not in PROVISIONED_SOFTWARE:
            return jsonify({
                "status": "error",
                "reason": "Software not registered"
            }), 400

        # Add version to valid list
        if new_version not in PROVISIONED_SOFTWARE[software_id]["valid_versions"]:
            PROVISIONED_SOFTWARE[software_id]["valid_versions"].append(new_version)

            # Persist to disk
            software_dir = f"./provisioned_software/{software_id.lower().replace(' ', '-')}"
            with open(f"{software_dir}/provisioning_data.json", "w") as f:
                json.dump(PROVISIONED_SOFTWARE[software_id], f, indent=2)

            return jsonify({
                "status": "success",
                "software_id": software_id,
                "valid_versions": PROVISIONED_SOFTWARE[software_id]["valid_versions"],
                "timestamp": datetime.utcnow().isoformat()
            }), 200
        else:
            return jsonify({
                "status": "success",
                "message": "Version already in valid list",
                "software_id": software_id,
                "valid_versions": PROVISIONED_SOFTWARE[software_id]["valid_versions"],
                "timestamp": datetime.utcnow().isoformat()
            }), 200

    except KeyError as e:
        return jsonify({
            "status": "error",
            "reason": f"Missing required field: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "reason": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "SSA Validation Server",
        "registered_software": len(PROVISIONED_SOFTWARE),
        "software_list": list(PROVISIONED_SOFTWARE.keys()),
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route("/", methods=["GET"])
def root():
    """Root endpoint with API information"""
    return jsonify({
        "service": "Birthmark SSA Validation Server",
        "version": "1.0.0",
        "endpoints": {
            "validate": "POST /api/v1/validate/software",
            "add_version": "POST /api/v1/versions/add",
            "health": "GET /health"
        },
        "registered_software": len(PROVISIONED_SOFTWARE)
    })


if __name__ == "__main__":
    print()
    print("=" * 60)
    print("SSA Validation Server - Running")
    print("=" * 60)
    print("Listening on: http://0.0.0.0:8001")
    print("Health check: http://localhost:8001/health")
    print("=" * 60)
    print()
    app.run(host="0.0.0.0", port=8001, debug=True)
