#!/usr/bin/env python3
"""Generate SSA Certificate Authority hierarchy"""

import os
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

# CA password (in production, use environment variable or secure key management)
CA_PASSWORD = b"birthmark-ssa-dev-password"

def generate_root_ca():
    """Generate SSA root CA certificate (10-year validity)"""
    print("[SSA] Generating root CA private key...")

    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
        backend=default_backend()
    )

    # Create certificate
    print("[SSA] Creating root CA certificate...")
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Oregon"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Birthmark Software Authority"),
        x509.NameAttribute(NameOID.COMMON_NAME, "SSA Root CA"),
    ])

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=3650)  # 10 years
    ).add_extension(
        x509.BasicConstraints(ca=True, path_length=1),
        critical=True,
    ).add_extension(
        x509.KeyUsage(
            digital_signature=False,
            content_commitment=False,
            key_encipherment=False,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=True,
            crl_sign=True,
            encipher_only=False,
            decipher_only=False,
        ),
        critical=True,
    ).sign(private_key, hashes.SHA256(), backend=default_backend())

    # Save private key (encrypted)
    print("[SSA] Saving root CA private key...")
    with open("certificates/ssa-root-ca.key", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(CA_PASSWORD)
        ))

    # Save certificate
    print("[SSA] Saving root CA certificate...")
    with open("certificates/ssa-root-ca.crt", "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print("[SSA] Root CA generated successfully!")
    print(f"  Subject: {cert.subject.rfc4514_string()}")
    print(f"  Valid until: {cert.not_valid_after}")

    return private_key, cert


def generate_intermediate_ca(root_key, root_cert):
    """Generate SSA intermediate CA certificate (5-year validity)"""
    print("\n[SSA] Generating intermediate CA private key...")

    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
        backend=default_backend()
    )

    # Create certificate
    print("[SSA] Creating intermediate CA certificate...")
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Oregon"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Birthmark Software Authority"),
        x509.NameAttribute(NameOID.COMMON_NAME, "SSA Intermediate CA"),
    ])

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        root_cert.subject
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=1825)  # 5 years
    ).add_extension(
        x509.BasicConstraints(ca=True, path_length=0),
        critical=True,
    ).add_extension(
        x509.KeyUsage(
            digital_signature=False,
            content_commitment=False,
            key_encipherment=False,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=True,
            crl_sign=True,
            encipher_only=False,
            decipher_only=False,
        ),
        critical=True,
    ).sign(root_key, hashes.SHA256(), backend=default_backend())

    # Save private key (encrypted)
    print("[SSA] Saving intermediate CA private key...")
    with open("certificates/ssa-intermediate-ca.key", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(CA_PASSWORD)
        ))

    # Save certificate
    print("[SSA] Saving intermediate CA certificate...")
    with open("certificates/ssa-intermediate-ca.crt", "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print("[SSA] Intermediate CA generated successfully!")
    print(f"  Subject: {cert.subject.rfc4514_string()}")
    print(f"  Issuer: {cert.issuer.rfc4514_string()}")
    print(f"  Valid until: {cert.not_valid_after}")

    return private_key, cert


def main():
    print("=" * 60)
    print("SSA Certificate Authority Generation")
    print("=" * 60)
    print()

    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Generate root CA
    root_key, root_cert = generate_root_ca()

    # Generate intermediate CA
    intermediate_key, intermediate_cert = generate_intermediate_ca(root_key, root_cert)

    print("\n" + "=" * 60)
    print("Certificate Authority hierarchy created successfully!")
    print("=" * 60)
    print("\nCertificates stored in ./certificates/")
    print("  - ssa-root-ca.crt (10-year validity)")
    print("  - ssa-root-ca.key (encrypted)")
    print("  - ssa-intermediate-ca.crt (5-year validity)")
    print("  - ssa-intermediate-ca.key (encrypted)")
    print(f"\nPassword for encrypted keys: {CA_PASSWORD.decode()}")
    print("\nIMPORTANT: In production, store private keys securely!")
    print()


if __name__ == "__main__":
    main()
