#!/usr/bin/env python3
"""
Generate Root CA Certificate for Birthmark SMA

This script generates a self-signed root CA certificate that will be used
to sign device certificates during provisioning.

Run this ONCE during initial setup:
    python scripts/generate_ca_certificate.py

Outputs:
    - certs/ca_private_key.pem (KEEP SECURE! This signs all device certs)
    - certs/ca_certificate.pem (Public CA cert, distribute to clients)

Security:
    - Store ca_private_key.pem in secure location
    - Never commit private key to git
    - Backup both files securely
"""

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography import x509
from cryptography.x509.oid import NameOID
from datetime import datetime, timedelta
import os


def generate_ca_certificate(output_dir: str = "certs"):
    """
    Generate root CA certificate for SMA.

    Args:
        output_dir: Directory to save certificates (default: certs/)
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    print("🔐 Generating Birthmark SMA Root CA Certificate...")
    print()

    # 1. Generate CA private key (ECDSA P-256)
    print("1. Generating CA private key (ECDSA P-256)...")
    ca_private_key = ec.generate_private_key(ec.SECP256R1())
    print("   ✓ Private key generated")

    # 2. Create self-signed CA certificate
    print("2. Creating self-signed CA certificate...")
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Oregon"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Eugene"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Birthmark Standard Foundation"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Simulated Manufacturing Authority"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Birthmark SMA Root CA"),
    ])

    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(ca_private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=3650))  # 10 years
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False
            ),
            critical=True
        )
        .sign(ca_private_key, hashes.SHA256())
    )
    print("   ✓ CA certificate created")
    print(f"   - Valid for: 10 years")
    print(f"   - Serial: {ca_cert.serial_number}")

    # 3. Save CA private key
    print("3. Saving CA private key...")
    private_key_path = os.path.join(output_dir, "ca_private_key.pem")
    with open(private_key_path, "wb") as f:
        f.write(ca_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print(f"   ✓ Saved to: {private_key_path}")
    print("   ⚠️  KEEP THIS FILE SECURE! It signs all device certificates.")

    # 4. Save CA certificate
    print("4. Saving CA certificate...")
    cert_path = os.path.join(output_dir, "ca_certificate.pem")
    with open(cert_path, "wb") as f:
        f.write(ca_cert.public_bytes(serialization.Encoding.PEM))
    print(f"   ✓ Saved to: {cert_path}")
    print("   ℹ️  This is public - can be distributed to clients")

    print()
    print("=" * 70)
    print("✅ CA Certificate Generation Complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Backup both files securely")
    print(f"  2. Set SMA_CA_PRIVATE_KEY_PATH={private_key_path} in .env")
    print(f"  3. Set SMA_CA_CERT_PATH={cert_path} in .env")
    print("  4. Ensure ca_private_key.pem is in .gitignore")
    print("  5. Distribute ca_certificate.pem to iOS clients (if needed)")
    print()
    print("⚠️  WARNING: Never commit ca_private_key.pem to git!")
    print()

    # 5. Display certificate info
    print("Certificate Information:")
    print(f"  Subject: {ca_cert.subject.rfc4514_string()}")
    print(f"  Issuer: {ca_cert.issuer.rfc4514_string()}")
    print(f"  Valid From: {ca_cert.not_valid_before}")
    print(f"  Valid Until: {ca_cert.not_valid_after}")
    print(f"  Serial Number: {ca_cert.serial_number}")
    print()


if __name__ == "__main__":
    generate_ca_certificate()
