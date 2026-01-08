# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Camera token generation for SMA validation.

Generates encrypted NUC tokens that SMA can validate to prove camera authenticity.
"""

import secrets
from dataclasses import dataclass
from typing import Optional

from .crypto.key_derivation import derive_encryption_key
from .crypto.encryption import encrypt_aes_gcm, EncryptedData


@dataclass
class CameraToken:
    """
    Encrypted NUC token for SMA validation.

    The token proves the camera possesses the correct NUC hash
    without revealing the NUC hash itself (zero-knowledge proof).
    """
    ciphertext: str  # Hex-encoded encrypted NUC hash
    nonce: str       # Hex-encoded 12-byte nonce
    auth_tag: str    # Hex-encoded 16-byte GCM auth tag
    table_id: int    # Which table was used (0-9 in Phase 1, 0-2499 in Phase 2)
    key_index: int   # Which key in table (0-999)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'ciphertext': self.ciphertext,
            'nonce': self.nonce,
            'auth_tag': self.auth_tag,
            'table_id': self.table_id,
            'key_index': self.key_index
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CameraToken':
        """Create CameraToken from dictionary."""
        return cls(
            ciphertext=data['ciphertext'],
            nonce=data['nonce'],
            auth_tag=data['auth_tag'],
            table_id=data['table_id'],
            key_index=data['key_index']
        )


class TokenGenerator:
    """
    Generates camera tokens for authentication.

    Randomly selects a table and key index, derives encryption key,
    and encrypts NUC hash for SMA validation.
    """

    def __init__(
        self,
        nuc_hash: bytes,
        table_assignments: list[int],
        master_keys: dict[int, bytes]
    ):
        """
        Initialize token generator.

        Args:
            nuc_hash: 32-byte NUC hash from provisioning
            table_assignments: List of 3 assigned table IDs
            master_keys: Dictionary mapping table_id -> 32-byte master key

        Raises:
            ValueError: If nuc_hash is not 32 bytes or table_assignments invalid
        """
        if len(nuc_hash) != 32:
            raise ValueError(f"NUC hash must be 32 bytes, got {len(nuc_hash)}")

        if len(table_assignments) != 3:
            raise ValueError(f"Expected 3 table assignments, got {len(table_assignments)}")

        # Verify master keys exist for all assigned tables
        for table_id in table_assignments:
            if table_id not in master_keys:
                raise ValueError(f"Missing master key for table {table_id}")

            if len(master_keys[table_id]) != 32:
                raise ValueError(f"Master key for table {table_id} must be 32 bytes")

        self.nuc_hash = nuc_hash
        self.table_assignments = table_assignments
        self.master_keys = master_keys

    def generate_token(
        self,
        table_id: Optional[int] = None,
        key_index: Optional[int] = None
    ) -> CameraToken:
        """
        Generate encrypted NUC token.

        Steps:
        1. Select random table from assigned 3 (or use provided)
        2. Select random key index 0-999 (or use provided)
        3. Derive encryption key using HKDF-SHA256
        4. Encrypt NUC hash with AES-256-GCM
        5. Return CameraToken

        Args:
            table_id: Optional table ID (random if None)
            key_index: Optional key index (random if None)

        Returns:
            CameraToken with encrypted NUC hash

        Example:
            >>> import secrets
            >>> nuc_hash = secrets.token_bytes(32)
            >>> master_keys = {3: secrets.token_bytes(32)}
            >>> generator = TokenGenerator(nuc_hash, [3], master_keys)
            >>> token = generator.generate_token()
            >>> len(token.ciphertext)
            64
        """
        # Select random table if not provided
        if table_id is None:
            table_id = secrets.choice(self.table_assignments)
        elif table_id not in self.table_assignments:
            raise ValueError(f"table_id {table_id} not in assigned tables {self.table_assignments}")

        # Select random key index if not provided
        if key_index is None:
            key_index = secrets.randbelow(1000)  # 0-999
        elif not 0 <= key_index <= 999:
            raise ValueError(f"key_index must be 0-999, got {key_index}")

        # Get master key for selected table
        master_key = self.master_keys[table_id]

        # Derive encryption key using HKDF-SHA256
        encryption_key = derive_encryption_key(master_key, key_index)

        # Encrypt NUC hash with AES-256-GCM
        encrypted = encrypt_aes_gcm(self.nuc_hash, encryption_key)

        # Create camera token
        token = CameraToken(
            ciphertext=encrypted.ciphertext.hex(),
            nonce=encrypted.nonce.hex(),
            auth_tag=encrypted.auth_tag.hex(),
            table_id=table_id,
            key_index=key_index
        )

        return token

    def generate_multiple_tokens(self, count: int) -> list[CameraToken]:
        """
        Generate multiple tokens for testing.

        Each token uses random table and key selections.

        Args:
            count: Number of tokens to generate

        Returns:
            List of CameraToken instances
        """
        return [self.generate_token() for _ in range(count)]


def create_token_generator_from_provisioning(provisioning_data) -> TokenGenerator:
    """
    Create TokenGenerator from provisioning data.

    Args:
        provisioning_data: ProvisioningData instance

    Returns:
        TokenGenerator instance
    """
    return TokenGenerator(
        nuc_hash=provisioning_data.get_nuc_hash_bytes(),
        table_assignments=provisioning_data.table_assignments,
        master_keys=provisioning_data.get_all_master_keys_bytes()
    )


if __name__ == "__main__":
    # Example usage with mock data
    import secrets

    print("=== Camera Token Test ===\n")

    # Generate mock provisioning data
    nuc_hash = secrets.token_bytes(32)
    table_assignments = [3, 7, 9]
    master_keys = {
        3: secrets.token_bytes(32),
        7: secrets.token_bytes(32),
        9: secrets.token_bytes(32)
    }

    # Create token generator
    generator = TokenGenerator(nuc_hash, table_assignments, master_keys)

    # Generate token
    token = generator.generate_token()

    print("Generated Camera Token:")
    print(f"  Table ID: {token.table_id}")
    print(f"  Key Index: {token.key_index}")
    print(f"  Ciphertext: {token.ciphertext[:32]}...")
    print(f"  Nonce: {token.nonce}")
    print(f"  Auth Tag: {token.auth_tag}")

    # Generate multiple tokens
    print("\nGenerating 3 tokens:")
    tokens = generator.generate_multiple_tokens(3)
    for i, t in enumerate(tokens):
        print(f"  Token {i+1}: table={t.table_id}, key_index={t.key_index}")
