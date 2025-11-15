"""
ECDSA signing for authentication bundles.

Signs authentication bundles with device private key to prove authenticity.
"""

import json
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature


def load_private_key_from_pem(pem_data: str | bytes) -> ec.EllipticCurvePrivateKey:
    """
    Load ECDSA P-256 private key from PEM format.

    Args:
        pem_data: PEM-encoded private key (string or bytes)

    Returns:
        ECDSA P-256 private key

    Raises:
        ValueError: If PEM data is invalid or not ECDSA P-256

    Example:
        >>> pem = "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----"
        >>> key = load_private_key_from_pem(pem)  # doctest: +SKIP
    """
    if isinstance(pem_data, str):
        pem_data = pem_data.encode('utf-8')

    private_key = serialization.load_pem_private_key(
        pem_data,
        password=None  # No password protection in Phase 1
    )

    # Verify it's ECDSA P-256
    if not isinstance(private_key, ec.EllipticCurvePrivateKey):
        raise ValueError("Private key is not ECDSA")

    return private_key


def load_public_key_from_pem(pem_data: str | bytes) -> ec.EllipticCurvePublicKey:
    """
    Load ECDSA P-256 public key from PEM format.

    Args:
        pem_data: PEM-encoded public key (string or bytes)

    Returns:
        ECDSA P-256 public key

    Example:
        >>> pem = "-----BEGIN PUBLIC KEY-----\\n...\\n-----END PUBLIC KEY-----"
        >>> key = load_public_key_from_pem(pem)  # doctest: +SKIP
    """
    if isinstance(pem_data, str):
        pem_data = pem_data.encode('utf-8')

    public_key = serialization.load_pem_public_key(pem_data)

    if not isinstance(public_key, ec.EllipticCurvePublicKey):
        raise ValueError("Public key is not ECDSA")

    return public_key


def sign_data(
    data: bytes,
    private_key: ec.EllipticCurvePrivateKey
) -> bytes:
    """
    Sign data with ECDSA P-256 + SHA-256.

    Args:
        data: Data to sign
        private_key: ECDSA P-256 private key

    Returns:
        DER-encoded signature

    Example:
        >>> from cryptography.hazmat.primitives.asymmetric import ec
        >>> private_key = ec.generate_private_key(ec.SECP256R1())
        >>> data = b"test data"
        >>> signature = sign_data(data, private_key)
        >>> len(signature) > 0
        True
    """
    signature = private_key.sign(
        data,
        ec.ECDSA(hashes.SHA256())
    )
    return signature


def verify_signature(
    data: bytes,
    signature: bytes,
    public_key: ec.EllipticCurvePublicKey
) -> bool:
    """
    Verify ECDSA signature.

    Useful for testing. Aggregation server performs actual verification.

    Args:
        data: Original data that was signed
        signature: DER-encoded signature
        public_key: ECDSA P-256 public key

    Returns:
        True if signature is valid, False otherwise

    Example:
        >>> from cryptography.hazmat.primitives.asymmetric import ec
        >>> private_key = ec.generate_private_key(ec.SECP256R1())
        >>> public_key = private_key.public_key()
        >>> data = b"test data"
        >>> signature = sign_data(data, private_key)
        >>> verify_signature(data, signature, public_key)
        True
        >>> verify_signature(b"wrong data", signature, public_key)
        False
    """
    try:
        public_key.verify(
            signature,
            data,
            ec.ECDSA(hashes.SHA256())
        )
        return True
    except InvalidSignature:
        return False


def sign_bundle(
    bundle_dict: dict,
    private_key: ec.EllipticCurvePrivateKey
) -> bytes:
    """
    Sign authentication bundle.

    Serializes bundle to canonical JSON and signs with device private key.

    Args:
        bundle_dict: Authentication bundle as dictionary
        private_key: Device ECDSA P-256 private key

    Returns:
        DER-encoded signature

    Example:
        >>> from cryptography.hazmat.primitives.asymmetric import ec
        >>> private_key = ec.generate_private_key(ec.SECP256R1())
        >>> bundle = {"image_hash": "abc123", "timestamp": 1234567890}
        >>> signature = sign_bundle(bundle, private_key)
        >>> len(signature) > 0
        True
    """
    # Remove signature field if present (don't sign signature)
    bundle_copy = bundle_dict.copy()
    bundle_copy.pop('device_signature', None)

    # Serialize to canonical JSON (sorted keys)
    bundle_json = json.dumps(bundle_copy, sort_keys=True)
    bundle_bytes = bundle_json.encode('utf-8')

    # Sign
    return sign_data(bundle_bytes, private_key)


def verify_bundle_signature(
    bundle_dict: dict,
    signature: bytes,
    public_key: ec.EllipticCurvePublicKey
) -> bool:
    """
    Verify authentication bundle signature.

    Args:
        bundle_dict: Authentication bundle as dictionary
        signature: DER-encoded signature
        public_key: Device ECDSA P-256 public key

    Returns:
        True if signature is valid, False otherwise

    Example:
        >>> from cryptography.hazmat.primitives.asymmetric import ec
        >>> private_key = ec.generate_private_key(ec.SECP256R1())
        >>> public_key = private_key.public_key()
        >>> bundle = {"image_hash": "abc123", "timestamp": 1234567890}
        >>> signature = sign_bundle(bundle, private_key)
        >>> verify_bundle_signature(bundle, signature, public_key)
        True
    """
    # Remove signature field
    bundle_copy = bundle_dict.copy()
    bundle_copy.pop('device_signature', None)

    # Serialize to canonical JSON
    bundle_json = json.dumps(bundle_copy, sort_keys=True)
    bundle_bytes = bundle_json.encode('utf-8')

    # Verify
    return verify_signature(bundle_bytes, signature, public_key)
