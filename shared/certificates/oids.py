# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Object Identifier (OID) definitions for Birthmark certificate extensions.

OID Namespace: 1.3.6.1.4.1.60000 (Birthmark Standard - placeholder PEN)
├── 1.* - Camera Certificate Extensions
└── 2.* - Software Certificate Extensions

Note: 1.3.6.1.4.1.60000 is a placeholder. Production requires IANA PEN registration.
"""

from cryptography import x509


# Base OID for all Birthmark extensions (placeholder PEN)
BIRTHMARK_OID_BASE = x509.ObjectIdentifier("1.3.6.1.4.1.60000")


class CameraCertOIDs:
    """OIDs for camera certificate custom extensions."""

    # 1.3.6.1.4.1.60000.1.1 - Manufacturer ID
    MANUFACTURER_ID = x509.ObjectIdentifier("1.3.6.1.4.1.60000.1.1")

    # 1.3.6.1.4.1.60000.1.2 - MA validation endpoint URL
    MA_ENDPOINT = x509.ObjectIdentifier("1.3.6.1.4.1.60000.1.2")

    # 1.3.6.1.4.1.60000.1.3 - Encrypted NUC hash (60 bytes)
    ENCRYPTED_NUC = x509.ObjectIdentifier("1.3.6.1.4.1.60000.1.3")

    # 1.3.6.1.4.1.60000.1.4 - Key table ID (0-2499)
    KEY_TABLE_ID = x509.ObjectIdentifier("1.3.6.1.4.1.60000.1.4")

    # 1.3.6.1.4.1.60000.1.5 - Key index within table (0-999)
    KEY_INDEX = x509.ObjectIdentifier("1.3.6.1.4.1.60000.1.5")

    # 1.3.6.1.4.1.60000.1.6 - Device family string
    DEVICE_FAMILY = x509.ObjectIdentifier("1.3.6.1.4.1.60000.1.6")

    @classmethod
    def all_oids(cls) -> list[x509.ObjectIdentifier]:
        """Return all camera certificate OIDs."""
        return [
            cls.MANUFACTURER_ID,
            cls.MA_ENDPOINT,
            cls.ENCRYPTED_NUC,
            cls.KEY_TABLE_ID,
            cls.KEY_INDEX,
            cls.DEVICE_FAMILY,
        ]


class SoftwareCertOIDs:
    """OIDs for software certificate custom extensions (Phase 2)."""

    # 1.3.6.1.4.1.60000.2.1 - Developer ID
    DEVELOPER_ID = x509.ObjectIdentifier("1.3.6.1.4.1.60000.2.1")

    # 1.3.6.1.4.1.60000.2.2 - SA validation endpoint URL
    SA_ENDPOINT = x509.ObjectIdentifier("1.3.6.1.4.1.60000.2.2")

    # 1.3.6.1.4.1.60000.2.3 - App bundle identifier
    APP_IDENTIFIER = x509.ObjectIdentifier("1.3.6.1.4.1.60000.2.3")

    # 1.3.6.1.4.1.60000.2.4 - Version string
    VERSION_STRING = x509.ObjectIdentifier("1.3.6.1.4.1.60000.2.4")

    # 1.3.6.1.4.1.60000.2.5 - Allowed versions (for validation)
    ALLOWED_VERSIONS = x509.ObjectIdentifier("1.3.6.1.4.1.60000.2.5")

    @classmethod
    def all_oids(cls) -> list[x509.ObjectIdentifier]:
        """Return all software certificate OIDs."""
        return [
            cls.DEVELOPER_ID,
            cls.SA_ENDPOINT,
            cls.APP_IDENTIFIER,
            cls.VERSION_STRING,
            cls.ALLOWED_VERSIONS,
        ]


def get_oid_name(oid: x509.ObjectIdentifier) -> str:
    """
    Get human-readable name for OID.

    Args:
        oid: The OID to look up

    Returns:
        Human-readable name or the OID string if unknown
    """
    oid_names = {
        # Camera OIDs
        CameraCertOIDs.MANUFACTURER_ID: "manufacturerID",
        CameraCertOIDs.MA_ENDPOINT: "maEndpoint",
        CameraCertOIDs.ENCRYPTED_NUC: "encryptedNUC",
        CameraCertOIDs.KEY_TABLE_ID: "keyTableID",
        CameraCertOIDs.KEY_INDEX: "keyIndex",
        CameraCertOIDs.DEVICE_FAMILY: "deviceFamily",
        # Software OIDs
        SoftwareCertOIDs.DEVELOPER_ID: "developerID",
        SoftwareCertOIDs.SA_ENDPOINT: "saEndpoint",
        SoftwareCertOIDs.APP_IDENTIFIER: "appIdentifier",
        SoftwareCertOIDs.VERSION_STRING: "versionString",
        SoftwareCertOIDs.ALLOWED_VERSIONS: "allowedVersions",
    }

    return oid_names.get(oid, oid.dotted_string)
