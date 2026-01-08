# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Birthmark Certificate Utilities

X.509 certificate generation, parsing, and validation for the Birthmark Protocol.
"""

from .oids import (
    BIRTHMARK_OID_BASE,
    CameraCertOIDs,
    SoftwareCertOIDs,
)

from .builder import (
    CameraCertificateBuilder,
    SoftwareCertificateBuilder,
)

from .parser import (
    CertificateParser,
    CameraExtensions,
    SoftwareExtensions,
)

from .validator import (
    CertificateValidator,
    ValidationResult,
)

__all__ = [
    # OIDs
    "BIRTHMARK_OID_BASE",
    "CameraCertOIDs",
    "SoftwareCertOIDs",
    # Builders
    "CameraCertificateBuilder",
    "SoftwareCertificateBuilder",
    # Parsers
    "CertificateParser",
    "CameraExtensions",
    "SoftwareExtensions",
    # Validators
    "CertificateValidator",
    "ValidationResult",
]
