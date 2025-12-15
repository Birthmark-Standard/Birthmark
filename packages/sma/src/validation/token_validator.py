"""
Token validation for camera authentication.

This module implements the cryptographic validation of encrypted NUC tokens
from cameras. It decrypts the token using key derivation and compares the
NUC hash against registered devices.

Privacy: The SMA never sees image hashes, only encrypted NUC tokens.
"""

from typing import Tuple, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

from ..key_tables.key_derivation import derive_encryption_key
from ..key_tables.table_manager import KeyTableManager
from ..identity.device_registry import DeviceRegistry, DeviceRegistration


class TokenValidationResult:
    """
    Result of token validation.

    Attributes:
        valid: True if token is valid (camera authenticated)
        message: Human-readable validation result message
        device: DeviceRegistration if found, None otherwise (for logging only)
    """

    def __init__(self, valid: bool, message: str, device: Optional[DeviceRegistration] = None):
        self.valid = valid
        self.message = message
        self.device = device


class TokenValidator:
    """
    Validates encrypted camera tokens.

    This class implements the SMA's side of the camera authentication protocol:
    1. Derive encryption key from (table_id, key_index)
    2. Decrypt the token using AES-256-GCM
    3. Compare decrypted NUC hash with registered devices
    4. Return PASS/FAIL
    """

    def __init__(self, table_manager: KeyTableManager, device_registry: DeviceRegistry):
        """
        Initialize token validator.

        Args:
            table_manager: Key table manager with master keys
            device_registry: Device registry with NUC hashes
        """
        self.table_manager = table_manager
        self.device_registry = device_registry

    def validate_token(
        self,
        ciphertext: str,
        auth_tag: str,
        nonce: str,
        table_id: int,
        key_index: int
    ) -> TokenValidationResult:
        """
        Validate an encrypted camera token.

        This function implements Phase 1 cryptographic validation:
        1. Derive encryption key from master key table
        2. Decrypt token with AES-256-GCM
        3. Look up device by NUC hash
        4. Verify device has access to this table
        5. Return PASS/FAIL

        Args:
            ciphertext: Hex-encoded encrypted NUC hash
            auth_tag: Hex-encoded 16-byte authentication tag
            nonce: Hex-encoded 12-byte nonce
            table_id: Key table ID (0-9 in Phase 1)
            key_index: Key index within table (0-999)

        Returns:
            TokenValidationResult with validation outcome

        Privacy Note:
            The SMA cannot tell which specific camera made the request,
            only that it was one of ~3,333 cameras assigned to this table.
        """
        # Step 1: Convert hex strings to bytes
        try:
            ciphertext_bytes = bytes.fromhex(ciphertext)
            auth_tag_bytes = bytes.fromhex(auth_tag)
            nonce_bytes = bytes.fromhex(nonce)
        except ValueError as e:
            return TokenValidationResult(
                valid=False,
                message=f"Invalid hex encoding: {str(e)}"
            )

        # Step 2: Validate table_id exists
        if table_id not in self.table_manager.key_tables:
            return TokenValidationResult(
                valid=False,
                message=f"Unknown table_id: {table_id}"
            )

        # Step 3: Derive encryption key from master key
        try:
            master_key = self.table_manager.key_tables[table_id]
            encryption_key = derive_encryption_key(master_key, key_index)
        except Exception as e:
            return TokenValidationResult(
                valid=False,
                message=f"Key derivation failed: {str(e)}"
            )

        # Step 4: Decrypt token using AES-256-GCM
        try:
            # Combine ciphertext and auth tag (AESGCM expects them together)
            ciphertext_with_tag = ciphertext_bytes + auth_tag_bytes

            # Decrypt and authenticate
            aesgcm = AESGCM(encryption_key)
            decrypted_nuc_hash = aesgcm.decrypt(
                nonce_bytes,
                ciphertext_with_tag,
                None  # No associated data
            )
        except InvalidTag:
            # Authentication failed - either wrong key or tampered data
            return TokenValidationResult(
                valid=False,
                message="Token authentication failed (wrong key or tampered data)"
            )
        except Exception as e:
            return TokenValidationResult(
                valid=False,
                message=f"Decryption failed: {str(e)}"
            )

        # Step 5: Look up device by NUC hash
        decrypted_nuc_hash_hex = decrypted_nuc_hash.hex()
        device = self.device_registry.get_device_by_nuc_hash(decrypted_nuc_hash_hex)

        if not device:
            # Also try device_secret for Phase 2 compatibility
            device = self.device_registry.get_device_by_secret(decrypted_nuc_hash_hex)

        if not device:
            return TokenValidationResult(
                valid=False,
                message="Unknown device (NUC hash not registered)"
            )

        # Step 6: Verify device has access to this table
        # Device must have this table_id in their table_assignments
        if table_id not in device.table_assignments:
            return TokenValidationResult(
                valid=False,
                message=f"Device {device.device_serial} not assigned to table {table_id}"
            )

        # Step 7: Check if device is blacklisted
        if device.is_blacklisted:
            return TokenValidationResult(
                valid=False,
                message=f"Device {device.device_serial} is blacklisted: {device.blacklist_reason}",
                device=device
            )

        # Success! Token is valid
        return TokenValidationResult(
            valid=True,
            message=f"Token validated successfully (table={table_id}, index={key_index})",
            device=device
        )


def validate_camera_token(
    table_manager: KeyTableManager,
    device_registry: DeviceRegistry,
    ciphertext: str,
    auth_tag: str,
    nonce: str,
    table_id: int,
    key_index: int
) -> Tuple[bool, str, Optional[DeviceRegistration]]:
    """
    Convenience function for validating camera tokens.

    Args:
        table_manager: Key table manager
        device_registry: Device registry
        ciphertext: Hex-encoded encrypted NUC hash
        auth_tag: Hex-encoded authentication tag
        nonce: Hex-encoded nonce
        table_id: Key table ID
        key_index: Key index

    Returns:
        Tuple of (valid, message, device)

    Example:
        >>> valid, msg, device = validate_camera_token(
        ...     table_manager,
        ...     device_registry,
        ...     "a1b2c3...",
        ...     "d4e5f6...",
        ...     "789012...",
        ...     3,
        ...     42
        ... )
        >>> if valid:
        ...     print(f"Camera authenticated: {device.device_serial}")
    """
    validator = TokenValidator(table_manager, device_registry)
    result = validator.validate_token(ciphertext, auth_tag, nonce, table_id, key_index)
    return (result.valid, result.message, result.device)
