"""
Device identity lookup for the SMA.

This module provides functions to query registered devices and verify
their NUC hashes.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from ..database import RegisteredDevice


def get_device_by_serial(db: Session, device_serial: str) -> Optional[RegisteredDevice]:
    """
    Look up a registered device by serial number.

    Args:
        db: Database session
        device_serial: Unique device serial number

    Returns:
        RegisteredDevice object or None if not found

    Example:
        >>> device = get_device_by_serial(db, "RPI-001")
        >>> device.device_family
        'Raspberry Pi'
    """
    return (
        db.query(RegisteredDevice)
        .filter(RegisteredDevice.device_serial == device_serial)
        .first()
    )


def get_device_by_nuc_hash(db: Session, nuc_hash: bytes) -> Optional[RegisteredDevice]:
    """
    Look up a registered device by its NUC hash.

    This is the primary lookup method used during validation. If a decrypted
    NUC hash matches a registered device, validation passes.

    Args:
        db: Database session
        nuc_hash: 32-byte SHA-256 hash of device's NUC map

    Returns:
        RegisteredDevice object or None if not found

    Example:
        >>> nuc_hash = hashlib.sha256(b"nuc_map").digest()
        >>> device = get_device_by_nuc_hash(db, nuc_hash)
        >>> device.device_serial
        'RPI-001'
    """
    if len(nuc_hash) != 32:
        raise ValueError(f"NUC hash must be 32 bytes, got {len(nuc_hash)}")

    return (
        db.query(RegisteredDevice)
        .filter(RegisteredDevice.nuc_hash == nuc_hash)
        .first()
    )


def register_device(
    db: Session,
    device_serial: str,
    nuc_hash: bytes,
    table_assignments: List[int],
    device_certificate: str,
    device_public_key: str,
    device_family: str,
) -> RegisteredDevice:
    """
    Register a new device with the SMA.

    This is called during device provisioning to store the device's
    NUC hash and key table assignments.

    Args:
        db: Database session
        device_serial: Unique device serial number
        nuc_hash: 32-byte SHA-256 hash of NUC map
        table_assignments: List of 3 key table IDs (0-2499)
        device_certificate: PEM-encoded X.509 certificate
        device_public_key: PEM-encoded public key
        device_family: Device type ('Raspberry Pi', 'iOS', etc.)

    Returns:
        Newly created RegisteredDevice object

    Raises:
        ValueError: If validation fails
        RuntimeError: If device already exists

    Example:
        >>> device = register_device(
        ...     db=db,
        ...     device_serial="RPI-001",
        ...     nuc_hash=hashlib.sha256(b"nuc").digest(),
        ...     table_assignments=[42, 1337, 2001],
        ...     device_certificate="-----BEGIN CERTIFICATE-----...",
        ...     device_public_key="-----BEGIN PUBLIC KEY-----...",
        ...     device_family="Raspberry Pi"
        ... )
    """
    # Validate inputs
    if len(nuc_hash) != 32:
        raise ValueError(f"NUC hash must be 32 bytes, got {len(nuc_hash)}")

    if len(table_assignments) != 3:
        raise ValueError(
            f"Expected 3 table assignments, got {len(table_assignments)}"
        )

    for table_id in table_assignments:
        if not (0 <= table_id < 2500):
            raise ValueError(f"Table ID {table_id} out of range [0, 2499]")

    # Check if device already exists
    existing = get_device_by_serial(db, device_serial)
    if existing is not None:
        raise RuntimeError(
            f"Device {device_serial} already registered. Use update instead."
        )

    # Create new device record
    device = RegisteredDevice(
        device_serial=device_serial,
        nuc_hash=nuc_hash,
        table_assignments=table_assignments,
        device_certificate=device_certificate,
        device_public_key=device_public_key,
        device_family=device_family,
    )

    db.add(device)
    db.commit()
    db.refresh(device)

    return device


def list_devices(db: Session, device_family: Optional[str] = None) -> List[RegisteredDevice]:
    """
    List all registered devices, optionally filtered by family.

    Args:
        db: Database session
        device_family: Optional filter by device family

    Returns:
        List of RegisteredDevice objects

    Example:
        >>> rpi_devices = list_devices(db, device_family="Raspberry Pi")
        >>> len(rpi_devices)
        5
    """
    query = db.query(RegisteredDevice)

    if device_family is not None:
        query = query.filter(RegisteredDevice.device_family == device_family)

    return query.all()


def get_device_count(db: Session) -> int:
    """
    Get the total number of registered devices.

    Args:
        db: Database session

    Returns:
        Count of registered devices

    Example:
        >>> get_device_count(db)
        127
    """
    return db.query(RegisteredDevice).count()
