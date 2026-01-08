# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
TPM (Trusted Platform Module) interface for secure operations.

Phase 1: Software-based crypto (development)
Phase 2: Hardware TPM integration (LetsTrust SLB 9670)

Provides hashing and signing using device private key.
"""

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .crypto.signing import load_private_key_from_pem, sign_data


@dataclass
class TPMConfig:
    """TPM configuration."""
    device_path: str = '/dev/tpm0'
    use_hardware: bool = False  # Phase 1: False, Phase 2: True


class TPMInterface:
    """
    Interface to TPM for secure operations.

    Phase 1: Software-based (uses Python cryptography library)
    Phase 2: Hardware-based (uses tpm2-tools or tpm2-pytss)
    """

    def __init__(
        self,
        config: Optional[TPMConfig] = None,
        private_key_pem: Optional[str] = None
    ):
        """
        Initialize TPM interface.

        Args:
            config: Optional TPM configuration
            private_key_pem: Device private key in PEM format
        """
        if config is None:
            config = TPMConfig()

        self.config = config
        self._private_key = None

        if private_key_pem:
            self._private_key = load_private_key_from_pem(private_key_pem)

    def verify_tpm_available(self) -> bool:
        """
        Check if hardware TPM is available.

        Returns:
            True if TPM device exists and responds

        Example:
            >>> tpm = TPMInterface()
            >>> tpm.verify_tpm_available()  # doctest: +SKIP
            False
        """
        if not self.config.use_hardware:
            return True  # Software mode always available

        # Check if TPM device exists
        tpm_device = Path(self.config.device_path)
        if not tpm_device.exists():
            print(f"⚠ TPM device not found: {self.config.device_path}")
            return False

        # Try to communicate with TPM
        try:
            result = subprocess.run(
                ['tpm2_getrandom', '16', '--hex'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"✓ TPM verified: {result.stdout.strip()}")
                return True
            else:
                print(f"⚠ TPM error: {result.stderr}")
                return False

        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("⚠ TPM tools not available")
            return False

    def hash_data(self, data: bytes) -> bytes:
        """
        Compute SHA-256 hash of data.

        Phase 1: Software hash (hashlib)
        Phase 2: Hardware TPM hash (tpm2_hash)

        Args:
            data: Data to hash

        Returns:
            32-byte SHA-256 hash

        Example:
            >>> tpm = TPMInterface()
            >>> data = b"test data"
            >>> hash_val = tpm.hash_data(data)
            >>> len(hash_val)
            32
        """
        if self.config.use_hardware:
            return self._hash_data_tpm(data)
        else:
            return self._hash_data_software(data)

    def _hash_data_software(self, data: bytes) -> bytes:
        """Compute hash using software (hashlib)."""
        return hashlib.sha256(data).digest()

    def _hash_data_tpm(self, data: bytes) -> bytes:
        """Compute hash using hardware TPM."""
        # Write data to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(data)
            input_file = f.name

        try:
            # Hash with TPM
            output_file = input_file + '.hash'
            result = subprocess.run([
                'tpm2_hash',
                '-g', 'sha256',
                '-o', output_file,
                input_file
            ], capture_output=True, check=True, timeout=10)

            # Read hash
            with open(output_file, 'rb') as f:
                hash_bytes = f.read()

            # Cleanup
            Path(output_file).unlink()
            return hash_bytes

        finally:
            Path(input_file).unlink()

    def sign_data(self, data: bytes) -> bytes:
        """
        Sign data with device private key.

        Args:
            data: Data to sign

        Returns:
            DER-encoded ECDSA signature

        Raises:
            RuntimeError: If private key not loaded

        Example:
            >>> from cryptography.hazmat.primitives.asymmetric import ec
            >>> private_key = ec.generate_private_key(ec.SECP256R1())
            >>> from .crypto.signing import sign_data as _sign_data
            >>> pem = private_key.private_bytes(
            ...     encoding=serialization.Encoding.PEM,
            ...     format=serialization.PrivateFormat.PKCS8,
            ...     encryption_algorithm=serialization.NoEncryption()
            ... ).decode()  # doctest: +SKIP
            >>> tpm = TPMInterface(private_key_pem=pem)  # doctest: +SKIP
            >>> signature = tpm.sign_data(b"test")  # doctest: +SKIP
            >>> len(signature) > 0  # doctest: +SKIP
            True
        """
        if self._private_key is None:
            raise RuntimeError("Private key not loaded")

        return sign_data(data, self._private_key)

    def load_private_key(self, pem_data: str) -> None:
        """
        Load device private key from PEM format.

        Args:
            pem_data: PEM-encoded private key
        """
        self._private_key = load_private_key_from_pem(pem_data)

    def has_private_key(self) -> bool:
        """
        Check if private key is loaded.

        Returns:
            True if private key is available
        """
        return self._private_key is not None


def create_tpm_interface_from_provisioning(provisioning_data) -> TPMInterface:
    """
    Create TPMInterface from provisioning data.

    Args:
        provisioning_data: ProvisioningData instance

    Returns:
        TPMInterface with loaded private key
    """
    return TPMInterface(
        config=TPMConfig(use_hardware=False),  # Phase 1: software
        private_key_pem=provisioning_data.device_private_key
    )


if __name__ == "__main__":
    # Example usage
    print("=== TPM Interface Test ===\n")

    # Create TPM interface (software mode)
    tpm = TPMInterface()

    # Check TPM availability
    available = tpm.verify_tpm_available()
    print(f"TPM available: {available}\n")

    # Test hashing
    test_data = b"Hello, Birthmark!"
    hash_result = tpm.hash_data(test_data)
    print(f"Hash test:")
    print(f"  Input: {test_data}")
    print(f"  SHA-256: {hash_result.hex()}")

    # Test signing (requires private key)
    print(f"\nSigning test:")
    print("  (Requires provisioning data with private key)")
