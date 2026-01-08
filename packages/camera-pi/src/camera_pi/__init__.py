# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Birthmark Camera Pi Package

Raspberry Pi camera prototype for the Birthmark Protocol.
Hardware-backed photo authentication with zero user latency.
"""

__version__ = "0.1.0"

# Export main classes and functions
from .raw_capture import (
    RawCaptureManager,
    MockCaptureManager,
    RawCaptureConfig,
    CaptureResult,
    create_capture_manager,
    hash_raw_bayer
)

from .provisioning_client import (
    ProvisioningClient,
    ProvisioningData
)

from .camera_token import (
    CameraToken,
    TokenGenerator,
    create_token_generator_from_provisioning
)

from .tpm_interface import (
    TPMInterface,
    TPMConfig,
    create_tpm_interface_from_provisioning
)

from .submission_client import (
    SubmissionClient,
    AuthenticationBundle,
    SubmissionQueue,
    SubmissionReceipt,
    create_submission_client
)

from .main import BirthmarkCamera

# Crypto exports
from .crypto.key_derivation import (
    derive_encryption_key,
    verify_key_derivation,
    generate_test_vectors,
    validate_implementation
)

from .crypto.encryption import (
    encrypt_aes_gcm,
    decrypt_aes_gcm,
    EncryptedData
)

from .crypto.signing import (
    sign_data,
    verify_signature,
    sign_bundle,
    verify_bundle_signature,
    load_private_key_from_pem,
    load_public_key_from_pem
)

__all__ = [
    # Version
    '__version__',

    # Raw capture
    'RawCaptureManager',
    'MockCaptureManager',
    'RawCaptureConfig',
    'CaptureResult',
    'create_capture_manager',
    'hash_raw_bayer',

    # Provisioning
    'ProvisioningClient',
    'ProvisioningData',

    # Camera token
    'CameraToken',
    'TokenGenerator',
    'create_token_generator_from_provisioning',

    # TPM
    'TPMInterface',
    'TPMConfig',
    'create_tpm_interface_from_provisioning',

    # Submission
    'SubmissionClient',
    'AuthenticationBundle',
    'SubmissionQueue',
    'SubmissionReceipt',
    'create_submission_client',

    # Main application
    'BirthmarkCamera',

    # Crypto
    'derive_encryption_key',
    'verify_key_derivation',
    'generate_test_vectors',
    'validate_implementation',
    'encrypt_aes_gcm',
    'decrypt_aes_gcm',
    'EncryptedData',
    'sign_data',
    'verify_signature',
    'sign_bundle',
    'verify_bundle_signature',
    'load_private_key_from_pem',
    'load_public_key_from_pem',
]
