"""
Key table generation for the SMA.

This module handles the initial generation of the 2,500 master keys
used for HKDF-based key derivation.
"""

import secrets
from typing import List

from sqlalchemy.orm import Session

from ..database import KeyTable


def generate_master_keys(count: int = 2500) -> List[bytes]:
    """
    Generate cryptographically secure master keys.

    Args:
        count: Number of master keys to generate (default: 2500)

    Returns:
        List of 32-byte master keys

    Example:
        >>> keys = generate_master_keys(count=10)
        >>> len(keys)
        10
        >>> all(len(k) == 32 for k in keys)
        True
    """
    return [secrets.token_bytes(32) for _ in range(count)]


def populate_key_tables(db: Session, master_keys: List[bytes]) -> None:
    """
    Populate the key_tables database with master keys.

    This should only be run once during initial setup.

    Args:
        db: Database session
        master_keys: List of 32-byte master keys

    Raises:
        ValueError: If key count is not 2500
        RuntimeError: If tables already exist

    Example:
        >>> master_keys = generate_master_keys()
        >>> populate_key_tables(db, master_keys)
    """
    if len(master_keys) != 2500:
        raise ValueError(f"Expected 2500 master keys, got {len(master_keys)}")

    # Check if tables already exist
    existing_count = db.query(KeyTable).count()
    if existing_count > 0:
        raise RuntimeError(
            f"Key tables already exist ({existing_count} rows). "
            "Delete existing tables before regenerating."
        )

    # Insert all master keys
    key_table_objects = [
        KeyTable(table_id=i, master_key=key) for i, key in enumerate(master_keys)
    ]

    db.bulk_save_objects(key_table_objects)
    db.commit()


def get_master_key(db: Session, table_id: int) -> bytes:
    """
    Retrieve a master key by table ID.

    Args:
        db: Database session
        table_id: Key table ID (0-2499)

    Returns:
        32-byte master key

    Raises:
        ValueError: If table_id is out of range or not found

    Example:
        >>> master_key = get_master_key(db, table_id=42)
        >>> len(master_key)
        32
    """
    if not (0 <= table_id < 2500):
        raise ValueError(f"Table ID {table_id} out of range [0, 2499]")

    key_table = db.query(KeyTable).filter(KeyTable.table_id == table_id).first()

    if key_table is None:
        raise ValueError(f"Key table {table_id} not found in database")

    return key_table.master_key


def get_master_keys(db: Session, table_ids: List[int]) -> List[bytes]:
    """
    Retrieve multiple master keys by table IDs.

    Args:
        db: Database session
        table_ids: List of key table IDs (typically 3 for a device)

    Returns:
        List of 32-byte master keys in the same order as table_ids

    Raises:
        ValueError: If any table_id is out of range or not found

    Example:
        >>> master_keys = get_master_keys(db, [42, 1337, 2001])
        >>> len(master_keys)
        3
    """
    return [get_master_key(db, table_id) for table_id in table_ids]
