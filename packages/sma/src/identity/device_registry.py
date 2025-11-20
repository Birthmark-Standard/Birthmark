"""
Device identity and registration management.

Stores provisioned device information:
- Device serial number
- NUC hash (sensor fingerprint)
- Table assignments
- Device certificate
- Public key
- Device family

Phase 1: JSON file storage
Phase 2: PostgreSQL database storage
"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict
from datetime import datetime


@dataclass
class DeviceRegistration:
    """
    Complete device registration record.

    Phase 2 schema:
    CREATE TABLE registered_devices (
        device_serial VARCHAR(255) PRIMARY KEY,
        device_secret BYTEA NOT NULL,
        key_table_indices INTEGER[3] NOT NULL,
        table_assignments INTEGER[3] NOT NULL,
        device_certificate TEXT NOT NULL,
        device_public_key TEXT NOT NULL,
        device_family VARCHAR(50),
        provisioned_at TIMESTAMP,
        is_blacklisted BOOLEAN DEFAULT FALSE,
        blacklisted_at TIMESTAMP,
        blacklist_reason TEXT
    );

    Phase 1 compatibility: nuc_hash field supported for backward compatibility
    """
    device_serial: str
    device_secret: str  # Hex-encoded SHA-256 (32 bytes = 64 hex chars)
    key_table_indices: List[int]  # 3 global table IDs (e.g., [42, 157, 891])
    table_assignments: List[int]  # 3 local table references (for backward compat)
    device_certificate: str  # PEM-encoded X.509 certificate
    device_public_key: str  # PEM-encoded public key
    device_family: str  # "Raspberry Pi", "iOS", etc.
    provisioned_at: str  # ISO 8601 timestamp
    is_blacklisted: bool = False  # True if device is blacklisted
    blacklisted_at: Optional[str] = None  # When blacklisted (ISO 8601)
    blacklist_reason: Optional[str] = None  # Why blacklisted
    # Backward compatibility
    nuc_hash: Optional[str] = None  # Phase 1 compatibility

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DeviceRegistration":
        """Create from dictionary (JSON deserialization)."""
        return cls(**data)

    def validate(self) -> bool:
        """
        Validate registration data.

        Returns:
            True if valid, raises ValueError if invalid
        """
        # Validate device secret
        if len(self.device_secret) != 64:
            raise ValueError(f"Device secret must be 64 hex chars, got {len(self.device_secret)}")

        try:
            bytes.fromhex(self.device_secret)
        except ValueError:
            raise ValueError("Device secret must be valid hex string")

        # Validate key_table_indices (global indices)
        if len(self.key_table_indices) != 3:
            raise ValueError(f"Must have 3 key table indices, got {len(self.key_table_indices)}")

        for tid in self.key_table_indices:
            if not isinstance(tid, int) or tid < 0:
                raise ValueError(f"Invalid key table index: {tid}")

        # Validate table assignments (local, backward compat)
        if len(self.table_assignments) != 3:
            raise ValueError(f"Must have 3 table assignments, got {len(self.table_assignments)}")

        for tid in self.table_assignments:
            if not isinstance(tid, int) or tid < 0:
                raise ValueError(f"Invalid table ID: {tid}")

        # Validate device serial
        if not self.device_serial or len(self.device_serial) == 0:
            raise ValueError("Device serial cannot be empty")

        # Validate blacklist fields consistency
        if self.is_blacklisted and not self.blacklisted_at:
            raise ValueError("Blacklisted devices must have blacklisted_at timestamp")

        return True


class DeviceRegistry:
    """
    Device registration storage and retrieval.

    Phase 1: JSON file-based storage
    Phase 2: PostgreSQL database storage
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize device registry.

        Args:
            storage_path: Path to JSON file for device registrations (Phase 1)
        """
        self.storage_path = storage_path
        self._registrations: Dict[str, DeviceRegistration] = {}

        if storage_path and storage_path.exists():
            self.load_from_file(storage_path)

    def register_device(self, registration: DeviceRegistration) -> None:
        """
        Register a new device.

        Args:
            registration: Device registration data

        Raises:
            ValueError: If device already registered or invalid data
        """
        # Validate registration data
        registration.validate()

        # Check if device already exists
        if registration.device_serial in self._registrations:
            raise ValueError(f"Device {registration.device_serial} already registered")

        # Store registration
        self._registrations[registration.device_serial] = registration

    def get_device(self, device_serial: str) -> Optional[DeviceRegistration]:
        """
        Get device registration by serial number.

        Args:
            device_serial: Device serial number

        Returns:
            DeviceRegistration or None if not found
        """
        return self._registrations.get(device_serial)

    def get_device_by_nuc_hash(self, nuc_hash: str) -> Optional[DeviceRegistration]:
        """
        Find device by NUC hash (Phase 1 backward compatibility).

        Used during validation to identify which device made a request.

        Args:
            nuc_hash: Hex-encoded NUC hash (64 chars)

        Returns:
            DeviceRegistration or None if not found
        """
        for registration in self._registrations.values():
            if registration.nuc_hash and registration.nuc_hash == nuc_hash:
                return registration
        return None

    def get_device_by_secret(self, device_secret: str) -> Optional[DeviceRegistration]:
        """
        Find device by device secret (Phase 2).

        Used during validation to identify which device made a request.

        Args:
            device_secret: Hex-encoded device secret (64 chars)

        Returns:
            DeviceRegistration or None if not found
        """
        for registration in self._registrations.values():
            if registration.device_secret == device_secret:
                return registration
        return None

    def blacklist_device(
        self,
        device_serial: str,
        reason: str
    ) -> bool:
        """
        Blacklist a device (Phase 2 abuse detection).

        Args:
            device_serial: Device serial number
            reason: Reason for blacklisting

        Returns:
            True if device was blacklisted, False if not found
        """
        device = self.get_device(device_serial)
        if not device:
            return False

        device.is_blacklisted = True
        device.blacklisted_at = datetime.utcnow().isoformat()
        device.blacklist_reason = reason

        # Update registration in dict
        self._registrations[device_serial] = device

        return True

    def unblacklist_device(self, device_serial: str) -> bool:
        """
        Remove device from blacklist.

        Args:
            device_serial: Device serial number

        Returns:
            True if device was unblacklisted, False if not found
        """
        device = self.get_device(device_serial)
        if not device:
            return False

        device.is_blacklisted = False
        device.blacklisted_at = None
        device.blacklist_reason = None

        # Update registration in dict
        self._registrations[device_serial] = device

        return True

    def is_device_blacklisted(self, device_serial: str) -> bool:
        """
        Check if device is blacklisted.

        Args:
            device_serial: Device serial number

        Returns:
            True if blacklisted, False otherwise
        """
        device = self.get_device(device_serial)
        return device.is_blacklisted if device else False

    def list_devices(
        self,
        device_family: Optional[str] = None
    ) -> List[DeviceRegistration]:
        """
        List all registered devices, optionally filtered by family.

        Args:
            device_family: Optional filter by device family

        Returns:
            List of device registrations
        """
        devices = list(self._registrations.values())

        if device_family:
            devices = [d for d in devices if d.device_family == device_family]

        return devices

    def device_exists(self, device_serial: str) -> bool:
        """
        Check if device is registered.

        Args:
            device_serial: Device serial number

        Returns:
            True if device exists, False otherwise
        """
        return device_serial in self._registrations

    def get_table_assignments(self, device_serial: str) -> Optional[List[int]]:
        """
        Get table assignments for a device.

        Args:
            device_serial: Device serial number

        Returns:
            List of 3 table IDs or None if device not found
        """
        device = self.get_device(device_serial)
        return device.table_assignments if device else None

    def save_to_file(self, path: Optional[Path] = None) -> None:
        """
        Save device registrations to JSON file (Phase 1).

        Args:
            path: Output file path (uses self.storage_path if None)
        """
        if path is None:
            path = self.storage_path

        if path is None:
            raise ValueError("No storage path specified")

        # Convert to serializable format
        data = {
            "devices": [
                reg.to_dict()
                for reg in sorted(
                    self._registrations.values(),
                    key=lambda r: r.provisioned_at
                )
            ],
            "total_devices": len(self._registrations),
            "last_updated": datetime.utcnow().isoformat()
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
        Load device registrations from JSON file (Phase 1).

        Args:
            path: Input file path (uses self.storage_path if None)
        """
        if path is None:
            path = self.storage_path

        if path is None:
            raise ValueError("No storage path specified")

        if not path.exists():
            raise FileNotFoundError(f"Registry file not found: {path}")

        with open(path, "r") as f:
            data = json.load(f)

        # Load device registrations
        self._registrations = {
            reg_data["device_serial"]: DeviceRegistration.from_dict(reg_data)
            for reg_data in data["devices"]
        }

    def get_statistics(self) -> dict:
        """
        Get statistics about registered devices.

        Returns:
            Dictionary with statistics
        """
        devices = list(self._registrations.values())

        # Count devices by family
        family_counts: Dict[str, int] = {}
        for device in devices:
            family_counts[device.device_family] = family_counts.get(device.device_family, 0) + 1

        # Count table usage
        table_usage: Dict[int, int] = {}
        for device in devices:
            for tid in device.table_assignments:
                table_usage[tid] = table_usage.get(tid, 0) + 1

        return {
            "total_devices": len(devices),
            "devices_by_family": family_counts,
            "total_table_assignments": sum(table_usage.values()),
            "unique_tables_used": len(table_usage),
            "table_usage": table_usage,
        }


class Phase2DatabaseRegistry(DeviceRegistry):
    """
    Device registry for Phase 2 with PostgreSQL storage.

    NOTE: This is a placeholder for Phase 2 implementation.
    Actual implementation will use SQLAlchemy ORM.
    """

    def __init__(self, database_url: str):
        """
        Initialize with database connection.

        Args:
            database_url: PostgreSQL connection string
        """
        super().__init__(storage_path=None)
        self.database_url = database_url
        # TODO: Initialize SQLAlchemy session

    def register_device(self, registration: DeviceRegistration) -> None:
        """Register device in database."""
        # TODO: Phase 2 implementation with SQLAlchemy
        raise NotImplementedError("Phase 2: Database-backed device registration")

    def get_device(self, device_serial: str) -> Optional[DeviceRegistration]:
        """Get device from database."""
        # TODO: Phase 2 implementation
        raise NotImplementedError("Phase 2: Database-backed device lookup")

    def save_to_file(self, path: Optional[Path] = None) -> None:
        """Not used in Phase 2 (database storage)."""
        raise NotImplementedError("Phase 2 uses database storage, not files")

    def load_from_file(self, path: Optional[Path] = None) -> None:
        """Not used in Phase 2 (database storage)."""
        raise NotImplementedError("Phase 2 uses database storage, not files")
