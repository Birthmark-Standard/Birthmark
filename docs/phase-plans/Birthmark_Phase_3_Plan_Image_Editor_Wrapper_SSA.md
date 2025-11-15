# Birthmark Phase 3 Plan - Image Editor Wrapper and Simulated Software Authority (SSA)

**Version:** 1.0  
**Date:** November 2025  
**Component:** Image Editor Wrapper + Simulated Software Authority  
**Timeline:** Phase 3 (Proof of Concept for Partnership Pitches)

---

## Purpose

The Image Editor Wrapper and Simulated Software Authority (SSA) demonstrate how the Birthmark Standard maintains provenance through the editing workflow. This proof of concept shows potential partners that we're designing for the complete image lifecycle, not just capture authentication.

**Critical Function:** The wrapper tracks modification levels for authenticated images, while the SSA validates that the editing software hasn't been tampered with. Together they ensure that post-capture modifications are recorded in a trustworthy chain.

---

## System Overview

```
Editing Software                 SSA                          Aggregation Server
     │                           │                                    │
     │  1. Certificate Request   │                                    │
     ├──────────────────────────>│                                    │
     │                           │                                    │
     │  2. Software Certificate  │                                    │
     │<──────────────────────────┤                                    │
     │                           │                                    │
     │  3. User Loads Image      │                                    │
     │     Query Authentication  │                                    │
     ├───────────────────────────┼───────────────────────────────────>│
     │                           │                                    │
     │  4. Image Authenticated   │                                    │
     │     Wrapper Activates     │                                    │
     │<──────────────────────────┼────────────────────────────────────┤
     │                           │                                    │
     │  5. Monitor Operations    │                                    │
     │     Track Mod Level       │                                    │
     │                           │                                    │
     │  6. Export Image          │                                    │
     │     Submit Mod Record     │                                    │
     ├───────────────────────────┼───────────────────────────────────>│
     │                           │                                    │
     │                           │  7. Validate Software Cert         │
     │                           │<───────────────────────────────────┤
     │                           │                                    │
     │                           │  8. PASS/FAIL Response             │
     │                           ├───────────────────────────────────>│
     │                           │                                    │
```

---

## Modification Level System

### Level Definitions

**Level 0 - Unmodified**
- Original authenticated image with no edits
- Highest trust: exact capture from validated camera

**Level 1 - Minor Modifications**
- Routine adjustments that don't alter substantive content
- Standard photojournalism-compliant edits
- Whitelist-based: only approved tools remain at Level 1

**Level 2 - Heavy Modifications**
- Significant alterations to image content
- Default for any non-whitelisted operation
- Still authenticated but indicates substantial editing

### Trust Model

The modification level is **sticky upward only**:
- Level 0 → Level 1: Any approved edit
- Level 1 → Level 2: Any non-approved operation
- Level 2 → Level 1: Not possible
- Level 1 → Level 0: Not possible

This ensures verifiers get accurate information about the image's modification history.

---

## Component 1: Simulated Software Authority (SSA)

### Purpose

The SSA validates that the editing software wrapper is legitimate and unmodified. Without this validation, a malicious actor could create a fake wrapper that reports all operations as Level 1 while actually performing Level 2 operations.

### Architecture

The SSA follows the same trust model as the Simulated Manufacturer Authority (SMA):
- Issues certificates to validated editing software
- Provides validation endpoint for aggregation server
- Maintains registry of certified software installations

### SSA Certificate Authority

**Tasks:**
- [ ] Generate SSA root CA certificate (10-year validity)
- [ ] Generate SSA intermediate CA certificate (5-year validity)
- [ ] Document certificate hierarchy separate from SMA
- [ ] Secure private key storage

**Commands:**
```bash
# Generate SSA root CA
openssl genrsa -aes256 -out ssa-root-ca.key 4096
openssl req -x509 -new -nodes -key ssa-root-ca.key \
  -sha256 -days 3650 -out ssa-root-ca.crt \
  -subj "/C=US/ST=Oregon/O=Birthmark Software Authority/CN=SSA Root CA"

# Generate SSA intermediate CA
openssl genrsa -aes256 -out ssa-intermediate-ca.key 4096
openssl req -new -key ssa-intermediate-ca.key \
  -out ssa-intermediate-ca.csr \
  -subj "/C=US/ST=Oregon/O=Birthmark Software Authority/CN=SSA Intermediate CA"
openssl x509 -req -in ssa-intermediate-ca.csr \
  -CA ssa-root-ca.crt -CAkey ssa-root-ca.key \
  -CAcreateserial -out ssa-intermediate-ca.crt \
  -days 1825 -sha256
```

### Software Provisioning

**Script:** `provision_software.py`

```python
#!/usr/bin/env python3
"""Provision editing software wrapper with SSA certificate"""

import os
import json
import hashlib
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta

def compute_wrapper_hash(wrapper_path: str) -> str:
    """Compute SHA-256 hash of wrapper executable"""
    hasher = hashlib.sha256()
    with open(wrapper_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def compute_versioned_hash(baseline_hash: str, version: str) -> str:
    """Derive version-specific hash from baseline hash and version string"""
    hasher = hashlib.sha256()
    hasher.update(baseline_hash.encode())
    hasher.update(version.encode())
    return hasher.hexdigest()

def provision_software(
    software_id: str,
    wrapper_path: str,
    output_dir: str,
    version: str = "1.0.0"
):
    """Provision editing software with certificate"""
    
    print(f"[SSA] Provisioning software: {software_id}")
    
    # 1. Compute wrapper baseline hash
    print("[SSA] Computing wrapper baseline hash...")
    baseline_hash = compute_wrapper_hash(wrapper_path)
    
    # 2. Compute versioned hash (baseline + version string)
    print(f"[SSA] Computing versioned hash for v{version}...")
    wrapper_hash = compute_versioned_hash(baseline_hash, version)
    
    # 2. Generate software keypair
    print("[SSA] Generating software keypair...")
    software_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    software_public_key = software_private_key.public_key()
    
    # 3. Load SSA intermediate CA
    print("[SSA] Loading SSA intermediate CA credentials...")
    with open("ssa-intermediate-ca.crt", "rb") as f:
        intermediate_cert = x509.load_pem_x509_certificate(f.read())
    with open("ssa-intermediate-ca.key", "rb") as f:
        intermediate_key = serialization.load_pem_private_key(
            f.read(),
            password=b"your-secure-password"  # Use environment variable
        )
    
    # 4. Create software certificate
    print("[SSA] Creating software certificate...")
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Oregon"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Birthmark Software Authority"),
        x509.NameAttribute(NameOID.COMMON_NAME, software_id),
    ])
    
    software_cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        intermediate_cert.subject
    ).public_key(
        software_public_key
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=365)  # 1-year validity
    ).add_extension(
        x509.SubjectAlternativeName([x509.DNSName(software_id)]),
        critical=False,
    ).sign(intermediate_key, hashes.SHA256())
    
    # 5. Save provisioning data
    print(f"[SSA] Saving provisioning data to {output_dir}...")
    os.makedirs(output_dir, exist_ok=True)
    
    # Save software private key
    with open(f"{output_dir}/software_private_key.pem", "wb") as f:
        f.write(software_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Save software certificate
    with open(f"{output_dir}/software_certificate.pem", "wb") as f:
        f.write(software_cert.public_bytes(serialization.Encoding.PEM))
    
    # Save certificate chain
    with open(f"{output_dir}/certificate_chain.pem", "wb") as f:
        f.write(software_cert.public_bytes(serialization.Encoding.PEM))
        f.write(intermediate_cert.public_bytes(serialization.Encoding.PEM))
        with open("ssa-root-ca.crt", "rb") as root_f:
            f.write(root_f.read())
    
    # Save provisioning metadata
    provisioning_data = {
        "software_id": software_id,
        "baseline_hash": baseline_hash,
        "version": version,
        "versioned_hash": wrapper_hash,
        "provisioned_at": datetime.utcnow().isoformat(),
        "authority": "SimulatedSoftwareAuthority",
        "supported_editors": ["GIMP"],
        "valid_versions": [version]  # SSA can add more versions here
    }
    
    with open(f"{output_dir}/provisioning_data.json", "w") as f:
        json.dump(provisioning_data, f, indent=2)
    
    print("[SSA] Provisioning complete!")
    print(f"  Software ID: {software_id}")
    print(f"  Baseline Hash: {baseline_hash[:16]}...")
    print(f"  Version: {version}")
    print(f"  Versioned Hash: {wrapper_hash[:16]}...")
    
    return provisioning_data

if __name__ == "__main__":
    provision_software(
        software_id="GIMP-Wrapper-POC-001",
        wrapper_path="./birthmark_gimp_wrapper.py",
        output_dir="./provisioned_software/gimp-wrapper-001",
        version="1.0.0"
    )
```

### SSA Validation Server

**Script:** `ssa_server.py`

```python
#!/usr/bin/env python3
"""SSA validation server for software certificate validation"""

from flask import Flask, request, jsonify
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from datetime import datetime
import json
import os

app = Flask(__name__)

# Load provisioned software registry
PROVISIONED_SOFTWARE = {}

def load_registry():
    """Load all provisioned software data"""
    registry_dir = "./provisioned_software"
    for software_dir in os.listdir(registry_dir):
        data_path = f"{registry_dir}/{software_dir}/provisioning_data.json"
        if os.path.exists(data_path):
            with open(data_path) as f:
                data = json.load(f)
                PROVISIONED_SOFTWARE[data["software_id"]] = data

def compute_versioned_hash(baseline_hash: str, version: str) -> str:
    """Derive version-specific hash from baseline hash and version string"""
    import hashlib
    hasher = hashlib.sha256()
    hasher.update(baseline_hash.encode())
    hasher.update(version.encode())
    return hasher.hexdigest()

load_registry()

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
        cert = x509.load_pem_x509_certificate(cert_pem.encode())
        software_id = cert.subject.get_attributes_for_oid(
            x509.oid.NameOID.COMMON_NAME
        )[0].value
        
        # Check if software is registered
        if software_id not in PROVISIONED_SOFTWARE:
            return jsonify({
                "validation_result": "FAIL",
                "reason": "Software not registered",
                "timestamp": datetime.utcnow().isoformat()
            }), 400
        
        # Verify certificate chain (simplified for POC)
        # In production: full chain validation against SSA root
        
        # Check certificate expiry
        if cert.not_valid_after < datetime.utcnow():
            return jsonify({
                "validation_result": "FAIL",
                "reason": "Certificate expired",
                "timestamp": datetime.utcnow().isoformat()
            }), 400
        
        # Verify version is in valid versions list
        provisioned_data = PROVISIONED_SOFTWARE[software_id]
        if version not in provisioned_data.get("valid_versions", []):
            return jsonify({
                "validation_result": "FAIL",
                "reason": f"Version {version} not authorized",
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
                "timestamp": datetime.utcnow().isoformat()
            }), 400
        
        # All checks passed
        return jsonify({
            "validation_result": "PASS",
            "software_id": software_id,
            "version": version,
            "authority": provisioned_data["authority"],
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
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
            "valid_versions": PROVISIONED_SOFTWARE[software_id]["valid_versions"]
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "reason": str(e)
        }), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "SSA Validation Server",
        "registered_software": len(PROVISIONED_SOFTWARE),
        "timestamp": datetime.utcnow().isoformat()
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001, debug=True)
```

---

## Component 2: GIMP Plugin (Manual Logging)

### Purpose

The GIMP plugin provides manual operation logging for authenticated images. Due to GIMP's plugin architecture limitations (no automatic PDB interception), users manually invoke logging operations. This demonstrates the concept for partnership pitches while acknowledging that production implementations would integrate directly into editing software.

**POC Limitation:** This proof of concept requires manual user interaction. In production, editing software vendors (Adobe, etc.) would integrate modification tracking directly into their tools, providing seamless automatic logging.

### Architecture

```
User Action                    Plugin                          GIMP
     │                           │                               │
     │  1. Menu: Initialize      │                               │
     │     Tracking              │                               │
     ├──────────────────────────>│                               │
     │                           │  2. Check Authentication      │
     │                           ├──────────────────────────────>│ (Agg Server)
     │                           │                               │
     │                           │  3. Attach Parasite           │
     │                           │     (tracking metadata)       │
     │                           ├──────────────────────────────>│
     │                           │                               │
     │  4. Edit Image Normally   │                               │
     │                           │                               │
     │  5. Menu: Log Level 2     │                               │
     │     Operation             │                               │
     ├──────────────────────────>│                               │
     │                           │  6. Update Parasite           │
     │                           │     (set level = 2)           │
     │                           ├──────────────────────────────>│
     │                           │                               │
     │  7. Menu: Export with     │                               │
     │     Birthmark Record      │                               │
     ├──────────────────────────>│                               │
     │                           │  8. Read Parasite             │
     │                           │     Create Mod Record         │
     │                           │     Submit to Agg Server      │
     │                           │                               │
```

### GIMP Parasites

GIMP parasites are metadata attachments that persist with images (in XCF format). The plugin uses parasites to store:
- Original image hash
- Current modification level
- Software ID
- Tracking initialization timestamp

### Plugin Implementation

**File:** `birthmark_gimp_plugin.py`

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Birthmark GIMP Plugin - Manual Modification Level Tracker
Proof of Concept for Phase 3 Partnership Demonstrations

Place this file in GIMP's plug-ins directory:
  Windows: %APPDATA%\GIMP\2.10\plug-ins\
  Linux: ~/.config/GIMP/2.10/plug-ins/
  
Make executable on Linux: chmod +x birthmark_gimp_plugin.py
"""

from gimpfu import *
import gimp
import json
import hashlib
import os
from datetime import datetime

# Plugin version - must match SSA valid versions
PLUGIN_VERSION = "1.0.0"

# Configuration
AGGREGATION_SERVER_URL = "http://localhost:8000"
SSA_SERVER_URL = "http://localhost:8001"
CERT_PATH = os.path.expanduser("~/.birthmark/software_certificate.pem")
KEY_PATH = os.path.expanduser("~/.birthmark/software_private_key.pem")

# Parasite names
PARASITE_TRACKING = "birthmark-tracking"
PARASITE_MOD_LEVEL = "birthmark-mod-level"
PARASITE_ORIGINAL_HASH = "birthmark-original-hash"

def compute_file_hash(filepath):
    """Compute SHA-256 hash of file"""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()

def compute_image_hash(image):
    """Compute hash of image pixel data"""
    # Flatten to get composite, hash the result
    # This is simplified - production would be more sophisticated
    hasher = hashlib.sha256()
    for layer in image.layers:
        region = layer.get_pixel_rgn(0, 0, layer.width, layer.height)
        hasher.update(str(region[0:layer.width, 0:layer.height]))
    return hasher.hexdigest()

def check_authentication(image_hash):
    """Query aggregation server for image authentication"""
    try:
        import urllib2
        url = "{}/api/v1/verify/{}".format(AGGREGATION_SERVER_URL, image_hash)
        response = urllib2.urlopen(url, timeout=10)
        data = json.loads(response.read())
        return data.get("authenticated", False)
    except Exception as e:
        gimp.message("Authentication check failed: {}".format(str(e)))
        return False

def validate_software():
    """Validate this plugin installation against SSA"""
    try:
        import urllib2
        
        # Compute baseline hash of this plugin file
        plugin_path = os.path.realpath(__file__)
        baseline_hash = compute_file_hash(plugin_path)
        
        # Load certificate
        with open(CERT_PATH, "r") as f:
            cert_pem = f.read()
        
        # Prepare validation request
        request_data = json.dumps({
            "software_certificate": cert_pem,
            "current_wrapper_hash": baseline_hash,
            "version": PLUGIN_VERSION
        })
        
        req = urllib2.Request(
            "{}/api/v1/validate/software".format(SSA_SERVER_URL),
            data=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        response = urllib2.urlopen(req, timeout=10)
        data = json.loads(response.read())
        
        if data.get("validation_result") == "PASS":
            return data.get("software_id", "Unknown")
        else:
            return None
            
    except Exception as e:
        gimp.message("Software validation failed: {}".format(str(e)))
        return None

def get_tracking_data(image):
    """Retrieve tracking data from image parasite"""
    try:
        parasite = image.parasite_find(PARASITE_TRACKING)
        if parasite:
            return json.loads(parasite.data)
    except:
        pass
    return None

def set_tracking_data(image, data):
    """Store tracking data in image parasite"""
    json_data = json.dumps(data)
    parasite = gimp.Parasite(
        PARASITE_TRACKING,
        PARASITE_PERSISTENT,  # Survives save/load
        json_data
    )
    image.parasite_attach(parasite)

def initialize_tracking(image, drawable):
    """
    Initialize Birthmark tracking for current image.
    Checks authentication and attaches tracking parasite.
    """
    gimp.progress_init("Initializing Birthmark tracking...")
    
    # Check if already tracking
    existing = get_tracking_data(image)
    if existing:
        gimp.message("Tracking already initialized for this image.\n"
                    "Current level: {}".format(existing.get("modification_level", 0)))
        return
    
    # Validate software certificate
    gimp.progress_update(0.2)
    software_id = validate_software()
    if not software_id:
        gimp.message("ERROR: Plugin failed SSA validation.\n"
                    "Cannot initialize tracking without valid certificate.")
        return
    
    # Compute current image hash
    gimp.progress_update(0.4)
    image_hash = compute_image_hash(image)
    
    # Check if image is authenticated
    gimp.progress_update(0.6)
    if not check_authentication(image_hash):
        gimp.message("Image is NOT authenticated.\n"
                    "Tracking will remain dormant.\n"
                    "Only Birthmark-authenticated images can be tracked.")
        return
    
    # Initialize tracking data
    gimp.progress_update(0.8)
    tracking_data = {
        "original_hash": image_hash,
        "modification_level": 0,
        "software_id": software_id,
        "initialized_at": datetime.utcnow().isoformat(),
        "original_dimensions": [image.width, image.height]
    }
    
    set_tracking_data(image, tracking_data)
    
    gimp.progress_update(1.0)
    gimp.message("Birthmark tracking initialized!\n"
                "Image authenticated: YES\n"
                "Current modification level: 0 (unmodified)\n\n"
                "Use 'Log Level 1 Operation' or 'Log Level 2 Operation' "
                "after making edits.")

def log_level_1_operation(image, drawable):
    """
    Log that a Level 1 (minor) operation was performed.
    Examples: exposure, white balance, crop, rotation
    """
    tracking = get_tracking_data(image)
    if not tracking:
        gimp.message("Tracking not initialized.\n"
                    "Run 'Initialize Tracking' first.")
        return
    
    current_level = tracking.get("modification_level", 0)
    
    if current_level == 0:
        tracking["modification_level"] = 1
        set_tracking_data(image, tracking)
        gimp.message("Modification level updated: 0 → 1\n"
                    "Image now marked as having minor modifications.")
    elif current_level == 1:
        gimp.message("Modification level remains: 1\n"
                    "Already at Level 1 (minor modifications).")
    else:  # level == 2
        gimp.message("Modification level remains: 2\n"
                    "Cannot reduce from Level 2.")

def log_level_2_operation(image, drawable):
    """
    Log that a Level 2 (heavy) operation was performed.
    Examples: clone stamp, content-aware fill, compositing
    """
    tracking = get_tracking_data(image)
    if not tracking:
        gimp.message("Tracking not initialized.\n"
                    "Run 'Initialize Tracking' first.")
        return
    
    current_level = tracking.get("modification_level", 0)
    
    if current_level < 2:
        tracking["modification_level"] = 2
        set_tracking_data(image, tracking)
        gimp.message("Modification level updated: {} → 2\n"
                    "Image now marked as having heavy modifications.".format(current_level))
    else:
        gimp.message("Modification level remains: 2\n"
                    "Already at Level 2 (heavy modifications).")

def show_tracking_status(image, drawable):
    """Display current tracking status for the image"""
    tracking = get_tracking_data(image)
    
    if not tracking:
        gimp.message("Birthmark Tracking Status\n"
                    "==========================\n"
                    "Status: NOT INITIALIZED\n\n"
                    "Run 'Initialize Tracking' to begin.")
        return
    
    level_desc = {
        0: "Unmodified",
        1: "Minor Modifications",
        2: "Heavy Modifications"
    }
    
    status = ("Birthmark Tracking Status\n"
             "==========================\n"
             "Status: ACTIVE\n"
             "Modification Level: {} ({})\n"
             "Software ID: {}\n"
             "Original Hash: {}...\n"
             "Initialized: {}\n"
             "Original Size: {}x{}").format(
                 tracking.get("modification_level", 0),
                 level_desc.get(tracking.get("modification_level", 0), "Unknown"),
                 tracking.get("software_id", "Unknown"),
                 tracking.get("original_hash", "")[:16],
                 tracking.get("initialized_at", "Unknown"),
                 tracking.get("original_dimensions", [0, 0])[0],
                 tracking.get("original_dimensions", [0, 0])[1]
             )
    
    gimp.message(status)

def export_with_birthmark(image, drawable, filepath):
    """
    Export image with Birthmark modification record.
    Creates sidecar JSON file and submits to aggregation server.
    """
    tracking = get_tracking_data(image)
    
    if not tracking:
        gimp.message("Tracking not initialized.\n"
                    "Cannot export with Birthmark record.")
        return
    
    gimp.progress_init("Exporting with Birthmark record...")
    
    # Save the image first (user should have already done this)
    gimp.progress_update(0.3)
    
    # Compute final image hash
    final_hash = compute_image_hash(image)
    
    # Create modification record
    gimp.progress_update(0.5)
    modification_record = {
        "original_image_hash": tracking.get("original_hash"),
        "final_image_hash": final_hash,
        "modification_level": tracking.get("modification_level", 0),
        "original_dimensions": tracking.get("original_dimensions"),
        "final_dimensions": [image.width, image.height],
        "software_id": tracking.get("software_id"),
        "timestamp": datetime.utcnow().isoformat(),
        "authority_type": "software",
        "plugin_version": PLUGIN_VERSION
    }
    
    # Save sidecar file
    gimp.progress_update(0.7)
    sidecar_path = filepath + ".birthmark.json"
    with open(sidecar_path, "w") as f:
        json.dump(modification_record, f, indent=2)
    
    # Submit to aggregation server
    gimp.progress_update(0.9)
    try:
        import urllib2
        request_data = json.dumps(modification_record)
        req = urllib2.Request(
            "{}/api/v1/modifications".format(AGGREGATION_SERVER_URL),
            data=request_data,
            headers={"Content-Type": "application/json"}
        )
        response = urllib2.urlopen(req, timeout=10)
        server_response = json.loads(response.read())
        
        gimp.progress_update(1.0)
        gimp.message("Birthmark Export Complete!\n"
                    "==========================\n"
                    "Modification Level: {}\n"
                    "Sidecar File: {}\n"
                    "Server Status: {}\n"
                    "Chain ID: {}".format(
                        modification_record["modification_level"],
                        sidecar_path,
                        server_response.get("status", "unknown"),
                        server_response.get("chain_id", "N/A")
                    ))
    except Exception as e:
        gimp.progress_update(1.0)
        gimp.message("Birthmark Export Complete (Offline)\n"
                    "====================================\n"
                    "Modification Level: {}\n"
                    "Sidecar File: {}\n\n"
                    "WARNING: Could not submit to server: {}\n"
                    "Record saved locally only.".format(
                        modification_record["modification_level"],
                        sidecar_path,
                        str(e)
                    ))

# Register plugin procedures
register(
    "birthmark_initialize_tracking",
    "Initialize Birthmark modification tracking for authenticated image",
    "Checks if image is Birthmark-authenticated and begins tracking modifications",
    "Birthmark Standard Foundation",
    "Birthmark Standard Foundation",
    "2025",
    "<Image>/Birthmark/Initialize Tracking",
    "*",
    [],
    [],
    initialize_tracking
)

register(
    "birthmark_log_level_1",
    "Log Level 1 (minor) modification",
    "Mark that a minor edit was performed (exposure, crop, rotation, etc.)",
    "Birthmark Standard Foundation",
    "Birthmark Standard Foundation",
    "2025",
    "<Image>/Birthmark/Log Level 1 Operation",
    "*",
    [],
    [],
    log_level_1_operation
)

register(
    "birthmark_log_level_2",
    "Log Level 2 (heavy) modification",
    "Mark that a heavy edit was performed (clone, composite, content-aware, etc.)",
    "Birthmark Standard Foundation",
    "Birthmark Standard Foundation",
    "2025",
    "<Image>/Birthmark/Log Level 2 Operation",
    "*",
    [],
    [],
    log_level_2_operation
)

register(
    "birthmark_status",
    "Show Birthmark tracking status",
    "Display current modification tracking status for the image",
    "Birthmark Standard Foundation",
    "Birthmark Standard Foundation",
    "2025",
    "<Image>/Birthmark/Show Status",
    "*",
    [],
    [],
    show_tracking_status
)

register(
    "birthmark_export",
    "Export image with Birthmark modification record",
    "Save modification record to sidecar file and submit to aggregation server",
    "Birthmark Standard Foundation",
    "Birthmark Standard Foundation",
    "2025",
    "<Image>/Birthmark/Export with Record",
    "*",
    [
        (PF_STRING, "filepath", "Export filepath", "")
    ],
    [],
    export_with_birthmark
)

main()
```

### Installation Instructions

1. **Locate GIMP plugins directory:**
   - Windows: `%APPDATA%\GIMP\2.10\plug-ins\`
   - Or check: Edit → Preferences → Folders → Plug-ins

2. **Copy plugin file** to plugins directory

3. **Create Birthmark config directory:**
   ```bash
   mkdir ~/.birthmark  # or %USERPROFILE%\.birthmark on Windows
   ```

4. **Copy certificates** from SSA provisioning:
   - `software_certificate.pem`
   - `software_private_key.pem`

5. **Restart GIMP** to load plugin

6. **Verify installation:**
   - Look for "Birthmark" menu under Filters or main menu
   - Run "Show Status" to test

### User Workflow

1. **Open authenticated image** in GIMP
2. **Birthmark → Initialize Tracking**
   - Plugin validates its certificate with SSA
   - Checks image authentication with aggregation server
   - Attaches tracking parasite (Level 0)
3. **Edit image normally** (exposure, crop, etc.)
4. **Birthmark → Log Level 1 Operation** (after minor edits)
   - Or **Log Level 2 Operation** (after heavy edits)
5. **Continue editing** as needed, logging operations
6. **Birthmark → Export with Record**
   - Creates sidecar JSON with modification record
   - Submits to aggregation server
7. **Save/export image** normally from GIMP

### Level Classification Guide

**Level 1 Operations** (minor, routine):
- Brightness/contrast adjustment
- Color balance/white balance
- Exposure correction
- Cropping (any amount)
- Rotation/flipping
- Sharpening
- Noise reduction
- Lens correction

**Level 2 Operations** (heavy, content-altering):
- Clone stamp / healing brush
- Content-aware fill
- Layer compositing
- Adding/removing objects
- Text overlay
- Filters that significantly alter appearance
- Any AI-powered editing tools

Users should log the highest level of operation performed. If any Level 2 operation is used, log Level 2. The modification level is sticky upward - once Level 2, always Level 2 for that image.

---

## Component 3: Aggregation Server Integration

### New Endpoints Required

The aggregation server needs to accept modification records alongside capture authentication records.

**Modification Record Submission:**
```
POST /api/v1/modifications
Body: {
    "original_image_hash": "<hash of authenticated original>",
    "final_image_hash": "<hash of modified image>",
    "modification_level": 0 | 1 | 2,
    "original_dimensions": [width, height],
    "software_id": "<certified software ID>",
    "timestamp": "<ISO timestamp>",
    "authority_type": "software",
    "signature": "<signed with software certificate>",
    "certificate_id": "<software certificate ID>"
}

Response: {
    "status": "recorded",
    "chain_id": "<blockchain reference>",
    "verification_url": "<URL to verify full chain>"
}
```

**Extended Verification:**
```
GET /api/v1/verify/<image_hash>
Response: {
    "authenticated": true,
    "authority_type": "manufacturer" | "software",
    "modification_level": 0 | 1 | 2,
    "provenance_chain": [
        {
            "hash": "<original capture hash>",
            "type": "capture",
            "camera_id": "<pseudonymous ID>",
            "timestamp": "<capture time>"
        },
        {
            "hash": "<modified image hash>",
            "type": "modification",
            "software_id": "<certified editor>",
            "level": 1,
            "timestamp": "<edit time>"
        }
    ]
}
```

### Database Schema Addition

```sql
-- Modification records table
CREATE TABLE modification_records (
    id SERIAL PRIMARY KEY,
    original_image_hash VARCHAR(64) NOT NULL,
    final_image_hash VARCHAR(64) NOT NULL,
    modification_level INTEGER NOT NULL CHECK (modification_level IN (0, 1, 2)),
    original_width INTEGER,
    original_height INTEGER,
    software_id VARCHAR(255) NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    blockchain_tx VARCHAR(66),
    
    FOREIGN KEY (original_image_hash) REFERENCES image_hashes(image_hash),
    INDEX idx_final_hash (final_image_hash),
    INDEX idx_software (software_id)
);
```

---

## Development Timeline

### Week 1-2: SSA Infrastructure

**Tasks:**
- [ ] Generate SSA certificate authority
- [ ] Implement software provisioning script with versioned hashing
- [ ] Build SSA validation server with version management
- [ ] Test certificate issuance and validation
- [ ] Document SSA API contract
- [ ] Add endpoint for registering new valid versions

**Deliverables:**
- SSA root and intermediate certificates
- `provision_software.py` script with version support
- `ssa_server.py` with versioned validation endpoint
- API documentation including version management

### Week 3-4: GIMP Plugin Core

**Tasks:**
- [ ] Set up GIMP Python-Fu development environment
- [ ] Implement plugin registration and menu structure
- [ ] Build certificate validation on initialization
- [ ] Create parasite-based tracking data storage
- [ ] Implement manual operation logging (Level 1/2)
- [ ] Build export with sidecar generation
- [ ] Test plugin installation and basic workflow

**Deliverables:**
- `birthmark_gimp_plugin.py` with all menu functions
- Installation documentation for Windows
- User workflow guide
- Level classification reference

### Week 5-6: Aggregation Server Integration

**Tasks:**
- [ ] Add modification record endpoint to aggregation server
- [ ] Extend verification endpoint for modification chain
- [ ] Implement software certificate validation in aggregation server
- [ ] Test end-to-end flow (plugin → aggregation server)
- [ ] Handle offline scenarios gracefully

**Deliverables:**
- Updated aggregation server with modification support
- Database schema for modification records
- Integration test suite
- Error handling documentation

### Week 7-8: Testing and Documentation

**Tasks:**
- [ ] End-to-end testing with real authenticated images
- [ ] Validate complete workflow from Pi capture through editing
- [ ] Create partnership demonstration materials
- [ ] Document architectural decisions and POC limitations
- [ ] Gather feedback from photojournalism community
- [ ] Prepare honest framing for partnership pitches

**Deliverables:**
- Test results and validation report
- Partnership pitch deck integration
- Technical whitepaper section on editing workflow
- Feedback summary from professional photographers
- "POC Limitations" document for transparent communication

---

## Security Model

### Trust Assumptions

1. **Software Authority is Honest:** The SSA only authorizes valid versions of legitimate plugins
2. **Certificate Chain is Secure:** SSA private keys are properly protected
3. **Baseline Hash is Immutable:** Original plugin hash stored at provisioning time is trusted
4. **Version String is Embedded:** Plugin contains its version as a constant that matches SSA's valid versions
5. **Network Communication is Secure:** HTTPS for all API calls (in production)

### Versioned Hash Validation

The versioned hash system allows legitimate software updates without requiring re-provisioning:

1. **Provisioning:** SSA stores baseline hash of plugin code + initial version
2. **Update:** Developer increments version constant in plugin code
3. **SSA Registration:** New version added to valid versions list
4. **Validation:** Both SSA and plugin compute `SHA256(baseline_hash + version_string)`
5. **Match:** If hashes match and version is in valid list, validation passes

This prevents:
- Modified plugins claiming to be original (hash mismatch)
- Old versions with known vulnerabilities (version not in valid list)
- Forked plugins (different baseline hash)

### Attack Vectors and Mitigations

**Attack:** Malicious plugin that misclassifies operations  
**Mitigation:** SSA validates plugin hash before issuing certificate; only authorized versions pass  
**Residual Risk:** Initial baseline must be trusted; SSA must properly vet versions

**Attack:** Man-in-the-middle modifying API responses  
**Mitigation:** HTTPS with certificate pinning (production)  
**Residual Risk:** Low with proper TLS configuration

**Attack:** User lies about operation level (logs Level 1 when actually Level 2)  
**Mitigation:** None in POC; production integration would track automatically  
**Residual Risk:** High for POC (acceptable - it's a demonstration, not production)

**Attack:** Tampering with plugin after installation  
**Mitigation:** Validation on each initialization; modified code fails hash check  
**Residual Risk:** Runtime memory attacks possible but high effort

**Attack:** Removing or modifying parasite data  
**Mitigation:** If parasite missing/corrupted, tracking fails; no false positives  
**Residual Risk:** Acceptable - absence of valid record signals issue

### Non-Goals for POC

- Comprehensive anti-tamper protection
- Runtime integrity monitoring
- User behavior enforcement (they could lie about Level)
- Obfuscation or anti-debugging
- Protection against kernel-level attacks
- Prevention of deliberate circumvention

These limitations are acceptable because:
1. This is a proof of concept for partnership pitches
2. Production implementations would be integrated into editing software by vendors
3. The goal is demonstrating data flow and trust architecture, not bulletproof security
4. Honest framing of limitations builds credibility with partners

---

## Community Outreach

### Level 1 Tool Validation

**Target Communities:**
- r/photojournalism on Reddit
- National Press Photographers Association (NPPA)
- Local photography clubs in Phase 2 beta test

**Questions to Validate:**
1. Does the Level 1 classification (minor adjustments) cover routine professional workflows?
2. Are there common operations missing from the Level 1 category?
3. Should any operations currently classified as Level 1 actually be Level 2?
4. Would professionals use a tool that tracks modification levels?

**Draft Outreach Message:**
```
I'm working on an open-source image authentication standard that tracks 
modification levels for authenticated photos. The system has three levels:
- Level 0: Unmodified original
- Level 1: Minor adjustments (exposure, white balance, cropping, rotation)
- Level 2: Heavy modifications (cloning, content-aware fill, compositing)

Level 1 includes: brightness/contrast, color balance, white balance, 
rotation, cropping (any amount), sharpening, and noise reduction.

Level 2 includes: clone stamp, healing brush, content-aware fill, 
layer compositing, adding/removing objects, AI-powered editing tools.

Questions for working professionals:
1. Does this classification match your intuition about "routine" vs 
   "substantive" modifications?
2. Are there any operations that should move between categories?
3. Does unlimited cropping at Level 1 make sense, given that framing 
   choices happen at capture time anyway?

The goal is a system where news organizations can set policy like "we 
publish Level 0 and Level 1 images" while preserving editorial flexibility 
for legitimate adjustments.

Appreciate any thoughts from those who do this work daily.
```

---

## Resource Requirements

### Development Environment

**Hardware:**
- Windows PC (primary development)
- Test images (authenticated via Pi prototype)

**Software:**
- Python 2.7 (bundled with GIMP 2.10)
- GIMP 2.10 (Windows installer with Python-Fu support)
- Python 3.10+ (for SSA server development)
- Flask for SSA server
- SQLite or PostgreSQL for aggregation server
- OpenSSL for certificate generation
- Text editor with Python syntax highlighting

**Estimated Costs:**
- Development: $0 (existing equipment)
- Cloud hosting for SSA: $0 (Heroku/Railway free tier)
- Domain/SSL: ~$15/year (optional for POC)

### Time Investment

- SSA Infrastructure: ~25 hours (including version management)
- GIMP Plugin: ~25 hours (simpler than wrapper approach)
- Aggregation Server Updates: ~15 hours
- Testing and Documentation: ~15 hours
- Community Outreach: ~5 hours
- Partnership Materials: ~10 hours

**Total: ~95 hours over 8 weeks**

### GIMP Python-Fu Notes

GIMP 2.10 uses Python 2.7 for scripting, which is deprecated but stable. Key considerations:

- Use `urllib2` instead of `requests` library
- String formatting uses `%` or `.format()` not f-strings
- `print` is a statement, not a function (unless importing from __future__)
- No walrus operator (`:=`)
- Division behavior differs from Python 3

The plugin code is written to be compatible with Python 2.7 as bundled with GIMP.

---

## Success Criteria

### Technical Validation

- [ ] SSA issues and validates software certificates with versioned hashing
- [ ] Plugin validates its certificate on initialization
- [ ] Plugin activates only for authenticated images
- [ ] Modification levels correctly tracked through manual logging
- [ ] Tracking data persists in image parasites
- [ ] Sidecar records properly generated on export
- [ ] Aggregation server accepts modification records
- [ ] Full provenance chain verifiable (capture → edit → verify)

### Partnership Demonstration

- [ ] Clear visual demonstration of workflow (even with manual steps)
- [ ] Compelling narrative about ecosystem completeness
- [ ] Technical credibility with potential partners
- [ ] Addresses "what about editing?" question proactively
- [ ] Honest framing: "POC shows data flow; production would be integrated"

### Community Feedback

- [ ] Level 1/2 classification validated by professionals
- [ ] No major conceptual objections identified
- [ ] Positive reception of modification tracking concept
- [ ] Input gathered for future refinement

### POC Scope Acknowledgment

This proof of concept is **not intended for beta testing or real-world use**. It demonstrates:
- The trust architecture (SSA validates software integrity)
- The data flow (tracking → aggregation server → blockchain)
- The modification level concept (three-tier system)
- The provenance chain (capture authentication → editing → final verification)

It does **not** demonstrate:
- Seamless automatic operation tracking
- Production-ready user experience
- Cross-editor compatibility
- Performance optimization

---

## Risk Management

### Technical Risks

**Risk:** GIMP Python-Fu uses Python 2.7 (deprecated)  
**Impact:** Compatibility issues, no modern Python features  
**Mitigation:** GIMP 2.10 ships with Python 2.7; plugin written for compatibility  
**Status:** Low (working within GIMP's constraints)

**Risk:** Aggregation server performance with modification records  
**Impact:** Slow verification responses  
**Mitigation:** Proper indexing, query optimization  
**Status:** Low (small scale for POC)

**Risk:** Parasite data doesn't persist in non-XCF formats  
**Impact:** Tracking lost when saving as JPEG/PNG  
**Mitigation:** Document limitation; sidecar file preserves record  
**Status:** Medium (acceptable for POC demonstration)

### Operational Risks

**Risk:** SSA private key compromise  
**Impact:** All software certificates invalid  
**Mitigation:** Encrypted storage, limited access  
**Status:** Medium (development environment)

**Risk:** Plugin hash changes during development  
**Impact:** Must add new version to SSA valid versions list  
**Mitigation:** Versioned hashing allows legitimate updates without re-provisioning  
**Status:** Low (versioning solves this)

**Risk:** Certificate validation requires network connectivity  
**Impact:** Plugin won't initialize tracking offline  
**Mitigation:** Cache validation status, graceful offline handling  
**Status:** Medium (acceptable for POC)

### Adoption Risks

**Risk:** Manual logging seen as too cumbersome  
**Impact:** POC dismissed as impractical  
**Mitigation:** Clear framing: "POC shows architecture, not final UX"  
**Status:** Medium (requires careful messaging)

**Risk:** Photographers reject modification tracking as surveillance  
**Impact:** Feature seen as overreach  
**Mitigation:** Emphasize: tracking only for already-authenticated images, no logging of edits on non-authenticated images, user controls when to log  
**Status:** Medium (requires careful messaging)

**Risk:** Level classification disagreements  
**Impact:** Professionals argue about what belongs where  
**Mitigation:** Community validation before finalizing; acknowledge this is governance question for Foundation  
**Status:** Medium (expected - classification is subjective)

**Risk:** Partners dismiss POC due to manual workflow  
**Impact:** Lose credibility  
**Mitigation:** Honest framing upfront; explain production integration path  
**Status:** Low (honesty builds trust)

---

## Future Considerations

### Beyond POC

**Production Implementation Path:**
- Native integration into editing software (not plugin/wrapper)
- Automatic operation tracking via editor's internal event system
- Adobe Photoshop/Lightroom: Hook into adjustment stack and tool invocations
- Capture One: Integrate with processing pipeline
- Affinity Photo: Native plugin architecture
- Seamless user experience with zero manual logging

**What POC Demonstrates to Partners:**
- Trust architecture (SSA validates software authority)
- Data flow (tracking → aggregation → blockchain)
- Modification level concept (three-tier classification)
- Provenance chain integrity (capture → edit → verify)
- API contracts and integration points

**What Partners Would Implement:**
- Automatic operation interception for their specific tools
- User-friendly interface for modification status
- Batch processing workflows
- Export format handling (JPEG, TIFF, PNG with sidecar or embedded metadata)

### Standard Evolution

**Tool Classification Governance:**
- Foundation maintains authoritative Level 1/2 definitions
- Version updates for new editing features
- Community input process for classification disputes
- Regular review cycle (annual or when major tools release)

**Cross-Editor Consistency:**
- Same operation = same level regardless of software
- Photoshop clone stamp = GIMP clone stamp = Level 2
- Foundation publishes mapping guides for each major editor

### Ecosystem Growth

**Multiple Software Authorities:**
- Each editing software vendor could run their own SA
- Aggregation server recognizes multiple SA certificate chains
- Foundation certifies SAs meet standard requirements

**Interoperability:**
- C2PA integration for metadata that survives social media
- Standard sidecar format that works across tools
- API versioning for backward compatibility

### Lessons for Phase 4+

This POC will reveal:
- What information partners actually need to see
- Which API contracts work well vs. need refinement
- How to pitch the value proposition effectively
- Community reception to modification tracking concept
- Technical gaps that need addressing before production

---

## Next Steps

### Immediate Actions

1. [ ] Set up GIMP 2.10 development environment on Windows
2. [ ] Verify Python-Fu console works (Filters → Python-Fu → Console)
3. [ ] Generate SSA certificate authority
4. [ ] Create initial plugin skeleton with menu registration
5. [ ] Post Level 1/2 classification question to photography communities

### Week 1 Goals

- [ ] SSA provisioning script working with versioned hashing
- [ ] Basic plugin installs and shows in GIMP menu
- [ ] "Show Status" function operational
- [ ] Community feedback on classification initiated

### Documentation Updates Needed

- [ ] Add editing workflow to main architecture document
- [ ] Update grant materials to mention ecosystem completeness
- [ ] Create partnership pitch slide on modification tracking
- [ ] Document POC limitations honestly for partner conversations
- [ ] Prepare "production integration path" narrative

### Partnership Pitch Framing

Key message for partners: *"This proof of concept demonstrates the trust architecture and data flow for tracking image modifications. The manual logging workflow is intentional for the POC - in production, your native editor would integrate automatic tracking directly into its tool pipeline. We're showing you the standard you'd implement, not the final user experience."*

This positions the POC as:
- A technical demonstration, not a finished product
- An invitation for partnership, not competition
- Evidence of comprehensive ecosystem thinking
- A starting point for discussion, not a take-it-or-leave-it solution

---

**Document Owner:** Samuel C. Ryan  
**Project:** The Birthmark Standard Foundation  
**Last Updated:** November 2025  
**Status:** Planning Complete - Ready for POC Implementation  
**Scope:** Proof of Concept Only (Not for Beta Testing or Production Use)
