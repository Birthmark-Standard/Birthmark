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


class Phase2DatabaseTableManager(KeyTableManager):
    """
    Key table manager for Phase 2 with PostgreSQL storage.

    NOTE: This is a placeholder for Phase 2 implementation.
    Actual implementation will use SQLAlchemy ORM.
    """

    def __init__(self, database_url: str):
        """
        Initialize with database connection.

        Args:
            database_url: PostgreSQL connection string
        """
        super().__init__(total_tables=2500, tables_per_device=3)
        self.database_url = database_url
        # TODO: Initialize SQLAlchemy session

    def generate_all_tables(self) -> None:
        """Generate and insert 2,500 key tables into database."""
        # TODO: Phase 2 implementation
        raise NotImplementedError("Phase 2: Database-backed table generation")

    def assign_random_tables(
        self,
        device_serial: str,
        exclude_tables: Optional[Set[int]] = None
    ) -> List[int]:
        """Assign tables and store in database."""
        # TODO: Phase 2 implementation
        raise NotImplementedError("Phase 2: Database-backed table assignment")

    def save_to_file(self, path: Optional[Path] = None) -> None:
        """Not used in Phase 2 (database storage)."""
        raise NotImplementedError("Phase 2 uses database storage, not files")

    def load_from_file(self, path: Optional[Path] = None) -> None:
        """Not used in Phase 2 (database storage)."""
        raise NotImplementedError("Phase 2 uses database storage, not files")
