"""
Key derivation utilities using HKDF for Birthmark Standard.

HKDF (HMAC-based Key Derivation Function) is used to derive encryption keys
from master keys stored in the SMA's key tables.
"""

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def derive_key_from_master(
    master_key: bytes, table_id: int, key_index: int, info: bytes = b"birthmark-v1"
) -> bytes:
    """
    Derive a 256-bit AES key from a master key using HKDF.

    This function implements deterministic key derivation so that the same
    (master_key, table_id, key_index) triple always produces the same output key.

    Args:
        master_key: 32-byte master key from key table
        table_id: Key table ID (0-2499)
        key_index: Index within the table (0-999)
        info: Context string for key derivation (default: b"birthmark-v1")

    Returns:
        32-byte derived AES-256 key

    Example:
        >>> master_key = secrets.token_bytes(32)
        >>> derived = derive_key_from_master(master_key, table_id=42, key_index=7)
        >>> len(derived)
        32
    """
    if len(master_key) != 32:
        raise ValueError(f"Master key must be 32 bytes, got {len(master_key)}")

    if not (0 <= table_id < 2500):
        raise ValueError(f"Table ID {table_id} out of range [0, 2499]")

    if not (0 <= key_index < 1000):
        raise ValueError(f"Key index {key_index} out of range [0, 999]")

    # Create salt from table_id and key_index
    # This ensures different keys for each (table, index) pair
    salt = table_id.to_bytes(4, byteorder="big") + key_index.to_bytes(4, byteorder="big")

    # Use HKDF to derive the key
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,  # 256 bits for AES-256
        salt=salt,
        info=info,
    )

    return hkdf.derive(master_key)


def derive_multiple_keys(master_keys: list[bytes], key_indices: list[int]) -> list[bytes]:
    """
    Derive multiple keys from corresponding master keys.

    This is a convenience function for deriving all 3 keys needed to decrypt
    a NUC token.

    Args:
        master_keys: List of 3 master keys (32 bytes each)
        key_indices: List of 3 key indices (0-999)

    Returns:
        List of 3 derived keys (32 bytes each)

    Example:
        >>> master_keys = [secrets.token_bytes(32) for _ in range(3)]
        >>> key_indices = [7, 99, 512]
        >>> derived_keys = derive_multiple_keys(master_keys, key_indices)
        >>> len(derived_keys)
        3
    """
    if len(master_keys) != 3:
        raise ValueError(f"Expected 3 master keys, got {len(master_keys)}")

    if len(key_indices) != 3:
        raise ValueError(f"Expected 3 key indices, got {len(key_indices)}")

    # For multiple keys, we use table_id=0 as a placeholder since we're given
    # the master keys directly. The actual table_id is encoded in which master
    # key we're using.
    return [
        derive_key_from_master(master_key, table_id=0, key_index=idx)
        for master_key, idx in zip(master_keys, key_indices)
    ]
