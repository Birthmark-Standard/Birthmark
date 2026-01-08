# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Validation result cache for idempotent MA responses.

Caches validation results to ensure same certificate/token returns same result.
Prevents replay attacks while allowing legitimate retries from Submission Server.
"""

import time
import hashlib
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from collections import OrderedDict


@dataclass
class CachedValidationResult:
    """Cached validation result with metadata."""

    valid: bool
    message: str
    device_serial: Optional[str]
    cached_at: float  # Unix timestamp
    request_count: int = 1  # How many times this request was made


class ValidationCache:
    """
    LRU cache for validation results with TTL.

    Features:
    - Idempotent: Same request returns same result
    - TTL: Results expire after 1 hour
    - LRU: Evicts least recently used when full
    - Thread-safe: Uses simple dict (FastAPI handles concurrency)
    """

    def __init__(self, max_size: int = 10000, ttl_seconds: int = 3600):
        """
        Initialize validation cache.

        Args:
            max_size: Maximum cached results (LRU eviction)
            ttl_seconds: Time-to-live for cached results (default 1 hour)
        """
        self.cache: OrderedDict[str, CachedValidationResult] = OrderedDict()
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds

        # Statistics
        self.hits = 0
        self.misses = 0

    def _make_key_token(
        self,
        ciphertext: str,
        auth_tag: str,
        nonce: str,
        table_id: int,
        key_index: int
    ) -> str:
        """
        Create cache key for token validation.

        Args:
            ciphertext: Hex-encoded ciphertext
            auth_tag: Hex-encoded auth tag
            nonce: Hex-encoded nonce
            table_id: Key table ID
            key_index: Key index within table

        Returns:
            SHA-256 hash of request parameters
        """
        # Hash all parameters to create unique key
        data = f"{ciphertext}:{auth_tag}:{nonce}:{table_id}:{key_index}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _make_key_cert(
        self,
        camera_cert: str,
        image_hash: str,
        timestamp: int,
        gps_hash: Optional[str],
        bundle_signature: str
    ) -> str:
        """
        Create cache key for certificate validation.

        Args:
            camera_cert: Base64-encoded certificate
            image_hash: SHA-256 image hash
            timestamp: Unix timestamp
            gps_hash: Optional GPS hash
            bundle_signature: Base64-encoded signature

        Returns:
            SHA-256 hash of request parameters
        """
        # Hash all parameters
        data = f"{camera_cert}:{image_hash}:{timestamp}:{gps_hash or ''}:{bundle_signature}"
        return hashlib.sha256(data.encode()).hexdigest()

    def get_token_result(
        self,
        ciphertext: str,
        auth_tag: str,
        nonce: str,
        table_id: int,
        key_index: int
    ) -> Optional[CachedValidationResult]:
        """
        Get cached result for token validation.

        Returns None if not in cache or expired.
        """
        key = self._make_key_token(ciphertext, auth_tag, nonce, table_id, key_index)
        return self._get(key)

    def get_cert_result(
        self,
        camera_cert: str,
        image_hash: str,
        timestamp: int,
        gps_hash: Optional[str],
        bundle_signature: str
    ) -> Optional[CachedValidationResult]:
        """
        Get cached result for certificate validation.

        Returns None if not in cache or expired.
        """
        key = self._make_key_cert(camera_cert, image_hash, timestamp, gps_hash, bundle_signature)
        return self._get(key)

    def _get(self, key: str) -> Optional[CachedValidationResult]:
        """Internal get with TTL check."""
        if key not in self.cache:
            self.misses += 1
            return None

        result = self.cache[key]

        # Check TTL
        age = time.time() - result.cached_at
        if age > self.ttl_seconds:
            # Expired - remove and return None
            del self.cache[key]
            self.misses += 1
            return None

        # Hit - move to end (LRU)
        self.cache.move_to_end(key)
        result.request_count += 1
        self.hits += 1
        return result

    def put_token_result(
        self,
        ciphertext: str,
        auth_tag: str,
        nonce: str,
        table_id: int,
        key_index: int,
        valid: bool,
        message: str,
        device_serial: Optional[str] = None
    ):
        """Cache result for token validation."""
        key = self._make_key_token(ciphertext, auth_tag, nonce, table_id, key_index)
        self._put(key, valid, message, device_serial)

    def put_cert_result(
        self,
        camera_cert: str,
        image_hash: str,
        timestamp: int,
        gps_hash: Optional[str],
        bundle_signature: str,
        valid: bool,
        message: str,
        device_serial: Optional[str] = None
    ):
        """Cache result for certificate validation."""
        key = self._make_key_cert(camera_cert, image_hash, timestamp, gps_hash, bundle_signature)
        self._put(key, valid, message, device_serial)

    def _put(self, key: str, valid: bool, message: str, device_serial: Optional[str]):
        """Internal put with LRU eviction."""
        # Evict oldest if at capacity
        if len(self.cache) >= self.max_size and key not in self.cache:
            self.cache.popitem(last=False)  # Remove oldest (FIFO)

        # Add/update result
        result = CachedValidationResult(
            valid=valid,
            message=message,
            device_serial=device_serial,
            cached_at=time.time()
        )

        self.cache[key] = result
        self.cache.move_to_end(key)  # Mark as most recently used

    def get_statistics(self) -> Dict:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "ttl_seconds": self.ttl_seconds
        }

    def clear(self):
        """Clear all cached results."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def cleanup_expired(self):
        """Remove expired entries (periodic maintenance)."""
        current_time = time.time()
        expired_keys = [
            key for key, result in self.cache.items()
            if (current_time - result.cached_at) > self.ttl_seconds
        ]

        for key in expired_keys:
            del self.cache[key]

        return len(expired_keys)


# Global cache instance
validation_cache = ValidationCache(max_size=10000, ttl_seconds=3600)
