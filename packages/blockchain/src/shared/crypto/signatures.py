# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""Cryptographic signature utilities for validators."""

import base64
from pathlib import Path
from typing import Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature


class ValidatorKeys:
    """Manages validator signing keys."""

    def __init__(self, private_key: ec.EllipticCurvePrivateKey):
        """Initialize with private key."""
        self.private_key = private_key
        self.public_key = private_key.public_key()

    @classmethod
    def generate(cls) -> "ValidatorKeys":
        """Generate new ECDSA P-256 key pair."""
        private_key = ec.generate_private_key(ec.SECP256R1())
        return cls(private_key)

    @classmethod
    def load_from_file(cls, path: Path) -> "ValidatorKeys":
        """Load private key from PEM file."""
        with open(path, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
            )
        if not isinstance(private_key, ec.EllipticCurvePrivateKey):
            raise ValueError("Key must be ECDSA")
        return cls(private_key)

    def save_to_file(self, path: Path) -> None:
        """Save private key to PEM file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        with open(path, "wb") as f:
            f.write(pem)

    def sign(self, data: bytes) -> str:
        """Sign data and return base64-encoded signature."""
        signature = self.private_key.sign(
            data,
            ec.ECDSA(hashes.SHA256()),
        )
        return base64.b64encode(signature).decode('utf-8')

    def verify(self, data: bytes, signature_b64: str) -> bool:
        """Verify signature (for testing)."""
        try:
            signature = base64.b64decode(signature_b64)
            self.public_key.verify(
                signature,
                data,
                ec.ECDSA(hashes.SHA256()),
            )
            return True
        except (InvalidSignature, Exception):
            return False

    def get_public_key_pem(self) -> str:
        """Export public key as PEM string."""
        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return pem.decode('utf-8')


def verify_signature_with_public_key(
    data: bytes,
    signature_b64: str,
    public_key_pem: str,
) -> bool:
    """
    Verify signature using public key PEM.

    Args:
        data: Original data that was signed
        signature_b64: Base64-encoded signature
        public_key_pem: Public key in PEM format

    Returns:
        True if signature is valid
    """
    try:
        # Load public key
        public_key = serialization.load_pem_public_key(public_key_pem.encode('utf-8'))
        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            return False

        # Decode signature
        signature = base64.b64decode(signature_b64)

        # Verify
        public_key.verify(
            signature,
            data,
            ec.ECDSA(hashes.SHA256()),
        )
        return True
    except (InvalidSignature, Exception):
        return False
