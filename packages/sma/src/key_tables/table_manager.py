# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Key table management and assignment.

Handles:
- Generation of master keys for key tables
- Storage and retrieval of key tables
- Random assignment of tables to devices
- Table availability tracking

Phase 1: 10 tables, JSON storage
Phase 2: 2,500 tables, PostgreSQL storage
"""

import json
import secrets
from pathlib import Path
from typing import List, Set, Optional
from dataclasses import dataclass, asdict


@dataclass
class KeyTable:
    """Represents a single key table with its master key."""
    table_id: int
    master_key: bytes  # 256-bit master key

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "table_id": self.table_id,
            "master_key": self.master_key.hex()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KeyTable":
        """Create from dictionary (JSON deserialization)."""
        return cls(
            table_id=data["table_id"],
            master_key=bytes.fromhex(data["master_key"])
        )


class KeyTableManager:
    """
    Manages key tables and device assignments.

    In Phase 1: Manages 10 tables with JSON storage
    In Phase 2: Manages 2,500 tables with database storage
    """

    def __init__(
        self,
        total_tables: int = 10,
        tables_per_device: int = 3,
        storage_path: Optional[Path] = None
    ):
        """
        Initialize key table manager.

        Args:
            total_tables: Total number of key tables (Phase 1: 10, Phase 2: 2500)
            tables_per_device: Number of tables assigned per device (always 3)
            storage_path: Path to JSON file for key table storage (Phase 1 only)
        """
        self.total_tables = total_tables
        self.tables_per_device = tables_per_device
        self.storage_path = storage_path
        self.key_tables: dict[int, bytes] = {}
        self._assigned_tables: dict[str, List[int]] = {}  # device_serial -> table_ids

        if storage_path and storage_path.exists():
            self.load_from_file(storage_path)

    def generate_master_key(self) -> bytes:
        """
        Generate a cryptographically secure 256-bit master key.

        Returns:
            32 bytes of random data
        """
        return secrets.token_bytes(32)

    def generate_all_tables(self) -> None:
        """
        Generate master keys for all key tables.

        Creates self.total_tables key tables with random master keys.
        """
        self.key_tables = {
            table_id: self.generate_master_key()
            for table_id in range(self.total_tables)
        }

    def assign_random_tables(
        self,
        device_serial: str,
        exclude_tables: Optional[Set[int]] = None
    ) -> List[int]:
        """
        Assign random key tables to a device.

        Selects tables_per_device random tables from available pool.
        Ensures no duplicate assignments within the same device.

        Args:
            device_serial: Unique device identifier
            exclude_tables: Optional set of table IDs to exclude from assignment

        Returns:
            List of assigned table IDs (e.g., [42, 1337, 2001])

        Raises:
            ValueError: If not enough tables available for assignment
        """
        if exclude_tables is None:
            exclude_tables = set()

        # Available tables = all tables minus excluded ones
        available_tables = set(range(self.total_tables)) - exclude_tables

        if len(available_tables) < self.tables_per_device:
            raise ValueError(
                f"Not enough tables available. Need {self.tables_per_device}, "
                f"have {len(available_tables)}"
            )

        # Use secrets.choice for cryptographically secure random selection
        assigned = []
        available_list = list(available_tables)

        for _ in range(self.tables_per_device):
            # Pick random table
            idx = secrets.randbelow(len(available_list))
            table_id = available_list.pop(idx)
            assigned.append(table_id)

        # Sort for consistency (optional, makes debugging easier)
        assigned.sort()

        # Track assignment
        self._assigned_tables[device_serial] = assigned

        return assigned

    def get_table_assignments(self, device_serial: str) -> Optional[List[int]]:
        """
        Get table assignments for a device.

        Args:
            device_serial: Device identifier

        Returns:
            List of table IDs or None if device not found
        """
        return self._assigned_tables.get(device_serial)

    def get_master_key(self, table_id: int) -> bytes:
        """
        Get master key for a specific table.

        Args:
            table_id: Table identifier

        Returns:
            256-bit master key

        Raises:
            KeyError: If table_id not found
        """
        if table_id not in self.key_tables:
            raise KeyError(f"Key table {table_id} not found")
        return self.key_tables[table_id]

    def get_master_keys(self, table_ids: List[int]) -> List[bytes]:
        """
        Get master keys for multiple tables.

        Args:
            table_ids: List of table identifiers

        Returns:
            List of master keys in same order

        Raises:
            KeyError: If any table_id not found
        """
        return [self.get_master_key(tid) for tid in table_ids]

    def save_to_file(self, path: Optional[Path] = None) -> None:
        """
        Save key tables to JSON file (Phase 1 only).

        Args:
            path: Output file path (uses self.storage_path if None)
        """
        if path is None:
            path = self.storage_path

        if path is None:
            raise ValueError("No storage path specified")

        # Convert to serializable format
        data = {
            "total_tables": self.total_tables,
            "tables_per_device": self.tables_per_device,
            "key_tables": [
                {
                    "table_id": tid,
                    "master_key": key.hex()
                }
                for tid, key in sorted(self.key_tables.items())
            ],
            "assigned_tables": self._assigned_tables
        }

        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write to file with restricted permissions
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        # Set restrictive permissions (owner read/write only)
        path.chmod(0o600)

    def load_from_file(self, path: Optional[Path] = None) -> None:
        """
        Load key tables from JSON file (Phase 1 only).

        Args:
            path: Input file path (uses self.storage_path if None)
        """
        if path is None:
            path = self.storage_path

        if path is None:
            raise ValueError("No storage path specified")

        if not path.exists():
            raise FileNotFoundError(f"Key table file not found: {path}")

        with open(path, "r") as f:
            data = json.load(f)

        self.total_tables = data["total_tables"]
        self.tables_per_device = data["tables_per_device"]

        # Load key tables
        self.key_tables = {
            item["table_id"]: bytes.fromhex(item["master_key"])
            for item in data["key_tables"]
        }

        # Load assignments
        self._assigned_tables = data.get("assigned_tables", {})

    def get_statistics(self) -> dict:
        """
        Get statistics about key table usage.

        Returns:
            Dictionary with statistics
        """
        # Count how many times each table is assigned
        table_usage = {tid: 0 for tid in range(self.total_tables)}
        for tables in self._assigned_tables.values():
            for tid in tables:
                table_usage[tid] += 1

        return {
            "total_tables": self.total_tables,
            "tables_per_device": self.tables_per_device,
            "total_devices": len(self._assigned_tables),
            "total_assignments": sum(table_usage.values()),
            "table_usage": table_usage,
            "min_usage": min(table_usage.values()),
            "max_usage": max(table_usage.values()),
            "avg_usage": sum(table_usage.values()) / len(table_usage) if table_usage else 0
        }


class Phase2KeyTableManager(KeyTableManager):
    """
    Key table manager for Phase 2 with full key storage.

    Manages 2,500 global key tables with 1,000 keys each.
    Each device receives actual key data (not just master keys) during provisioning.
    """

    def __init__(
        self,
        total_tables: int = 2500,
        keys_per_table: int = 1000,
        storage_path: Optional[Path] = None
    ):
        """
        Initialize Phase 2 key table manager.

        Args:
            total_tables: Total number of key tables (default: 2,500)
            keys_per_table: Keys per table (default: 1,000)
            storage_path: Path to JSON file for key storage
        """
        super().__init__(total_tables=total_tables, tables_per_device=3, storage_path=storage_path)
        self.keys_per_table = keys_per_table
        # Storage: {table_id: {key_index: derived_key}}
        self.derived_keys: dict[int, dict[int, bytes]] = {}

    def generate_all_tables_with_keys(self) -> None:
        """
        Generate 2,500 key tables with 1,000 derived keys each.

        Uses HKDF to derive all keys from master keys.
        Total: 2.5 million keys.
        """
        from .key_derivation import derive_encryption_key

        # First generate master keys
        self.generate_all_tables()

        print(f"Deriving {self.keys_per_table} keys for each of {self.total_tables} tables...")

        # Derive all keys for each table
        for table_id in range(self.total_tables):
            if table_id % 100 == 0:
                print(f"  Deriving keys for table {table_id}/{self.total_tables}")

            master_key = self.key_tables[table_id]
            self.derived_keys[table_id] = {}

            for key_index in range(self.keys_per_table):
                derived_key = derive_encryption_key(master_key, key_index)
                self.derived_keys[table_id][key_index] = derived_key

        print(f"✓ Generated {len(self.derived_keys)} tables with {self.keys_per_table} keys each")

    def get_table_keys(self, table_id: int) -> List[bytes]:
        """
        Get all derived keys for a specific table.

        Args:
            table_id: Global table identifier

        Returns:
            List of 1,000 derived keys (32 bytes each)

        Raises:
            KeyError: If table_id not found
        """
        if table_id not in self.derived_keys:
            raise KeyError(f"Key table {table_id} not found")

        # Return keys in order (0-999)
        return [
            self.derived_keys[table_id][i]
            for i in range(self.keys_per_table)
        ]

    def get_specific_key(self, table_id: int, key_index: int) -> bytes:
        """
        Get a specific derived key.

        Args:
            table_id: Global table identifier
            key_index: Key index (0-999)

        Returns:
            Derived encryption key (32 bytes)

        Raises:
            KeyError: If table or key not found
        """
        if table_id not in self.derived_keys:
            raise KeyError(f"Key table {table_id} not found")
        if key_index not in self.derived_keys[table_id]:
            raise KeyError(f"Key index {key_index} not found in table {table_id}")

        return self.derived_keys[table_id][key_index]

    def get_multiple_table_keys(self, table_ids: List[int]) -> List[List[bytes]]:
        """
        Get all keys for multiple tables (for provisioning).

        Args:
            table_ids: List of global table identifiers

        Returns:
            List of key arrays, one per table

        Raises:
            KeyError: If any table_id not found
        """
        return [self.get_table_keys(tid) for tid in table_ids]

    def save_to_file_with_keys(self, path: Optional[Path] = None) -> None:
        """
        Save key tables with all derived keys to JSON file.

        WARNING: This creates a large file (~80MB for 2,500 tables × 1,000 keys).
        Only use for Phase 2 development/testing.
        """
        if path is None:
            path = self.storage_path

        if path is None:
            raise ValueError("No storage path specified")

        # Convert to serializable format
        derived_keys_serializable = {
            str(table_id): {
                str(key_idx): key.hex()
                for key_idx, key in keys.items()
            }
            for table_id, keys in self.derived_keys.items()
        }

        data = {
            "total_tables": self.total_tables,
            "keys_per_table": self.keys_per_table,
            "tables_per_device": self.tables_per_device,
            "key_tables": [
                {
                    "table_id": tid,
                    "master_key": key.hex()
                }
                for tid, key in sorted(self.key_tables.items())
            ],
            "derived_keys": derived_keys_serializable,
            "assigned_tables": self._assigned_tables
        }

        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Saving {len(self.derived_keys)} tables with derived keys to {path}")
        print(f"  (This may take a moment...)")

        # Write to file
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        # Set restrictive permissions
        path.chmod(0o600)

        file_size_mb = path.stat().st_size / (1024 * 1024)
        print(f"✓ Saved key tables ({file_size_mb:.1f} MB)")

    def load_from_file_with_keys(self, path: Optional[Path] = None) -> None:
        """
        Load key tables with all derived keys from JSON file.
        """
        if path is None:
            path = self.storage_path

        if path is None:
            raise ValueError("No storage path specified")

        if not path.exists():
            raise FileNotFoundError(f"Key table file not found: {path}")

        print(f"Loading key tables from {path}")
        print(f"  (This may take a moment...)")

        with open(path, "r") as f:
            data = json.load(f)

        self.total_tables = data["total_tables"]
        self.keys_per_table = data.get("keys_per_table", 1000)
        self.tables_per_device = data["tables_per_device"]

        # Load master keys
        self.key_tables = {
            item["table_id"]: bytes.fromhex(item["master_key"])
            for item in data["key_tables"]
        }

        # Load derived keys
        derived_keys_data = data.get("derived_keys", {})
        self.derived_keys = {
            int(table_id): {
                int(key_idx): bytes.fromhex(key_hex)
                for key_idx, key_hex in keys.items()
            }
            for table_id, keys in derived_keys_data.items()
        }

        # Load assignments
        self._assigned_tables = data.get("assigned_tables", {})

        print(f"✓ Loaded {len(self.key_tables)} master keys")
        print(f"✓ Loaded {len(self.derived_keys)} tables with derived keys")
