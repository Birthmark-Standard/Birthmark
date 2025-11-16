#!/usr/bin/env python3
"""Provision editing software wrapper with SSA certificate"""

import os
import sys
import json
import hashlib
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from datetime import datetime, timedelta

# CA password (in production, use environment variable or secure key management)
CA_PASSWORD = b"birthmark-ssa-dev-password"


def compute_wrapper_hash(wrapper_path: str) -> str:
    """Compute SHA-256 hash of wrapper executable/script"""
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
    version: str = "1.0.0",
    supported_editors: list = None
):
    """
    Provision editing software with certificate

    Args:
        software_id: Unique identifier for the software (e.g., "GIMP-Wrapper-POC-001")
        wrapper_path: Path to the wrapper plugin file
        output_dir: Directory to save provisioning data
        version: Version string (default: "1.0.0")
        supported_editors: List of supported editing software (default: ["GIMP"])
    """
    if supported_editors is None:
        supported_editors = ["GIMP"]

    print(f"[SSA] Provisioning software: {software_id}")
    print(f"[SSA] Wrapper path: {wrapper_path}")
    print(f"[SSA] Version: {version}")
    print()

    # 1. Compute wrapper baseline hash
    print("[SSA] Computing wrapper baseline hash...")
    if not os.path.exists(wrapper_path):
        print(f"[SSA] ERROR: Wrapper file not found: {wrapper_path}")
        sys.exit(1)

    baseline_hash = compute_wrapper_hash(wrapper_path)
    print(f"[SSA]   Baseline hash: {baseline_hash[:16]}...{baseline_hash[-16:]}")

    # 2. Compute versioned hash (baseline + version string)
    print(f"[SSA] Computing versioned hash for v{version}...")
    versioned_hash = compute_versioned_hash(baseline_hash, version)
    print(f"[SSA]   Versioned hash: {versioned_hash[:16]}...{versioned_hash[-16:]}")
    print()

    # 3. Generate software keypair
    print("[SSA] Generating software keypair...")
    software_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    software_public_key = software_private_key.public_key()

    # 4. Load SSA intermediate CA
    print("[SSA] Loading SSA intermediate CA credentials...")
    try:
        with open("certificates/ssa-intermediate-ca.crt", "rb") as f:
            intermediate_cert = x509.load_pem_x509_certificate(
                f.read(),
                backend=default_backend()
            )
        with open("certificates/ssa-intermediate-ca.key", "rb") as f:
            intermediate_key = serialization.load_pem_private_key(
                f.read(),
                password=CA_PASSWORD,
                backend=default_backend()
            )
    except FileNotFoundError as e:
        print(f"[SSA] ERROR: CA certificates not found. Run generate_ca.py first.")
        print(f"[SSA]   Missing file: {e.filename}")
        sys.exit(1)

    # 5. Create software certificate
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
    ).sign(intermediate_key, hashes.SHA256(), backend=default_backend())

    # 6. Save provisioning data
    print(f"[SSA] Saving provisioning data to {output_dir}/")
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
        with open("certificates/ssa-root-ca.crt", "rb") as root_f:
            f.write(root_f.read())

    # Save provisioning metadata
    provisioning_data = {
        "software_id": software_id,
        "baseline_hash": baseline_hash,
        "version": version,
        "versioned_hash": versioned_hash,
        "provisioned_at": datetime.utcnow().isoformat(),
        "authority": "SimulatedSoftwareAuthority",
        "supported_editors": supported_editors,
        "valid_versions": [version]  # SSA can add more versions here
    }

    with open(f"{output_dir}/provisioning_data.json", "w") as f:
        json.dump(provisioning_data, f, indent=2)

    print()
    print("=" * 60)
    print("[SSA] Provisioning complete!")
    print("=" * 60)
    print(f"  Software ID: {software_id}")
    print(f"  Baseline Hash: {baseline_hash[:16]}...{baseline_hash[-16:]}")
    print(f"  Version: {version}")
    print(f"  Versioned Hash: {versioned_hash[:16]}...{versioned_hash[-16:]}")
    print(f"  Supported Editors: {', '.join(supported_editors)}")
    print(f"  Valid Versions: {', '.join(provisioning_data['valid_versions'])}")
    print()
    print("Files saved:")
    print(f"  - {output_dir}/software_certificate.pem")
    print(f"  - {output_dir}/software_private_key.pem")
    print(f"  - {output_dir}/certificate_chain.pem")
    print(f"  - {output_dir}/provisioning_data.json")
    print()

    return provisioning_data


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Provision editing software wrapper with SSA certificate"
    )
    parser.add_argument(
        "--software-id",
        required=True,
        help="Unique identifier for the software (e.g., GIMP-Wrapper-POC-001)"
    )
    parser.add_argument(
        "--wrapper-path",
        required=True,
        help="Path to the wrapper plugin file"
    )
    parser.add_argument(
        "--output-dir",
        help="Directory to save provisioning data (default: ./provisioned_software/<software-id-slug>)"
    )
    parser.add_argument(
        "--version",
        default="1.0.0",
        help="Version string (default: 1.0.0)"
    )
    parser.add_argument(
        "--supported-editors",
        nargs="+",
        default=["GIMP"],
        help="List of supported editing software (default: GIMP)"
    )

    args = parser.parse_args()

    # Default output directory
    if not args.output_dir:
        slug = args.software_id.lower().replace(" ", "-")
        args.output_dir = f"./provisioned_software/{slug}"

    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Provision software
    provision_software(
        software_id=args.software_id,
        wrapper_path=args.wrapper_path,
        output_dir=args.output_dir,
        version=args.version,
        supported_editors=args.supported_editors
    )


if __name__ == "__main__":
    main()
