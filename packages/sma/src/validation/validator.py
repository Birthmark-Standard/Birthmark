"""
Validation logic for the SMA.

This module implements the core validation algorithm:
1. Receive encrypted token and table/key references
2. Derive correct keys using HKDF
3. Decrypt the token
4. Check if decrypted NUC hash matches a registered device
5. Return PASS or FAIL
"""

import logging
from typing import List

from cryptography.exceptions import InvalidTag
from sqlalchemy.orm import Session

from shared.crypto import decrypt_nuc_token, derive_key_from_master
from shared.types import ValidationRequest, ValidationResponse

from ..identity import get_device_by_nuc_hash
from ..key_tables import get_master_keys

logger = logging.getLogger(__name__)


def validate_authentication_token(
    db: Session, validation_request: ValidationRequest
) -> ValidationResponse:
    """
    Validate a camera's encrypted NUC token.

    This is the core validation function. It:
    1. Retrieves master keys for the referenced tables
    2. Derives encryption keys using HKDF
    3. Decrypts the token (triple AES-GCM)
    4. Looks up the device by decrypted NUC hash
    5. Returns PASS if device found, FAIL otherwise

    CRITICAL: This function never sees or processes image hashes.
    It only validates camera authenticity.

    Args:
        db: Database session
        validation_request: ValidationRequest containing encrypted token and key references

    Returns:
        ValidationResponse with valid=True if camera is legitimate, False otherwise

    Example:
        >>> request = ValidationRequest(
        ...     encrypted_token=b"...",
        ...     table_references=[42, 1337, 2001],
        ...     key_indices=[7, 99, 512]
        ... )
        >>> response = validate_authentication_token(db, request)
        >>> response.valid
        True
    """
    try:
        # Step 1: Get master keys for the referenced tables
        logger.debug(
            f"Retrieving master keys for tables: {validation_request.table_references}"
        )
        master_keys = get_master_keys(db, validation_request.table_references)

        # Step 2: Derive encryption keys using HKDF
        logger.debug(f"Deriving keys for indices: {validation_request.key_indices}")
        derived_keys = _derive_encryption_keys(
            master_keys,
            validation_request.table_references,
            validation_request.key_indices,
        )

        # Step 3: Decrypt the NUC token
        logger.debug("Decrypting NUC token")
        decrypted_nuc_hash = decrypt_nuc_token(
            validation_request.encrypted_token, derived_keys
        )

        # Step 4: Look up device by NUC hash
        logger.debug("Looking up device by NUC hash")
        device = get_device_by_nuc_hash(db, decrypted_nuc_hash)

        # Step 5: Return result
        if device is not None:
            logger.info(
                f"Validation PASSED for device {device.device_serial} "
                f"(family: {device.device_family})"
            )
            return ValidationResponse(valid=True)
        else:
            logger.warning("Validation FAILED: NUC hash not found in database")
            return ValidationResponse(valid=False)

    except InvalidTag:
        # Decryption failed - wrong keys or corrupted token
        logger.warning("Validation FAILED: Decryption failed (wrong keys or corrupted token)")
        return ValidationResponse(valid=False)

    except ValueError as e:
        # Invalid input (e.g., table_id out of range)
        logger.error(f"Validation FAILED: Invalid input - {e}")
        return ValidationResponse(valid=False)

    except Exception as e:
        # Unexpected error - log but still return FAIL
        logger.error(f"Validation FAILED: Unexpected error - {e}", exc_info=True)
        return ValidationResponse(valid=False)


def _derive_encryption_keys(
    master_keys: List[bytes], table_ids: List[int], key_indices: List[int]
) -> List[bytes]:
    """
    Derive encryption keys from master keys using HKDF.

    This is an internal helper function that applies HKDF to each
    (master_key, table_id, key_index) triple.

    Args:
        master_keys: List of 3 master keys (32 bytes each)
        table_ids: List of 3 table IDs (0-2499)
        key_indices: List of 3 key indices (0-999)

    Returns:
        List of 3 derived encryption keys (32 bytes each)

    Raises:
        ValueError: If input lengths don't match or values are out of range
    """
    if len(master_keys) != 3:
        raise ValueError(f"Expected 3 master keys, got {len(master_keys)}")

    if len(table_ids) != 3:
        raise ValueError(f"Expected 3 table IDs, got {len(table_ids)}")

    if len(key_indices) != 3:
        raise ValueError(f"Expected 3 key indices, got {len(key_indices)}")

    derived_keys = []
    for master_key, table_id, key_index in zip(master_keys, table_ids, key_indices):
        derived_key = derive_key_from_master(master_key, table_id, key_index)
        derived_keys.append(derived_key)

    return derived_keys


def validate_batch(
    db: Session, validation_requests: List[ValidationRequest]
) -> List[ValidationResponse]:
    """
    Validate multiple authentication tokens in batch.

    This is useful for the aggregation server to validate multiple
    submissions in a single call.

    Args:
        db: Database session
        validation_requests: List of ValidationRequest objects

    Returns:
        List of ValidationResponse objects (same order as requests)

    Example:
        >>> requests = [request1, request2, request3]
        >>> responses = validate_batch(db, requests)
        >>> all_valid = all(r.valid for r in responses)
    """
    return [validate_authentication_token(db, req) for req in validation_requests]
