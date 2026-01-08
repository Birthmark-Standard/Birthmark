# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Submission server client for submitting authentication bundles.

Handles HTTP communication with the Birthmark submission server.
"""

import json
import queue
import threading
import time
from dataclasses import dataclass
from typing import Optional
import requests


@dataclass
class AuthenticationBundle:
    """
    Complete authentication bundle sent to blockchain submission server.

    This format MUST match what blockchain submission server expects.
    Updated for merged blockchain+submission server architecture (Nov 2025).
    """
    image_hash: str  # SHA-256 of raw Bayer data (64 hex chars)
    camera_token: dict  # CameraToken.to_dict() - will be converted to blockchain format
    timestamp: int  # Unix timestamp (seconds since epoch)
    table_assignments: list[int]  # All 3 assigned tables (for privacy)
    gps_hash: Optional[str] = None  # SHA-256 of GPS coords (optional)
    owner_hash: Optional[str] = None  # SHA-256 of (owner_name + owner_salt)
    device_signature: Optional[str] = None  # ECDSA signature (hex)
    isp_validation: Optional[dict] = None  # ISP validation data (variance-from-expected)
    modification_level: int = 0  # 0=raw, 1=processed, 2+=further modifications
    parent_image_hash: Optional[str] = None  # Parent hash for provenance chain

    def to_json(self) -> dict:
        """
        Convert to JSON for blockchain API submission.

        Blockchain expects:
        - encrypted_nuc_token: bytes (base64-encoded ciphertext + nonce + auth_tag)
        - table_references: List[int] - all 3 assigned tables
        - key_indices: List[int] - 3 key indices (actual + 2 random for privacy)
        - device_signature: bytes (base64-encoded)
        """
        import secrets
        import base64

        # Pack encrypted token: ciphertext (32 bytes) + nonce (12 bytes) + auth_tag (16 bytes)
        ciphertext_bytes = bytes.fromhex(self.camera_token['ciphertext'])
        nonce_bytes = bytes.fromhex(self.camera_token['nonce'])
        auth_tag_bytes = bytes.fromhex(self.camera_token['auth_tag'])
        packed_token = ciphertext_bytes + nonce_bytes + auth_tag_bytes

        # Generate 3 key indices: actual one + 2 random (for privacy)
        actual_table_id = self.camera_token['table_id']
        actual_key_index = self.camera_token['key_index']

        # Map actual table position to generate indices in same order
        table_position = self.table_assignments.index(actual_table_id)
        key_indices = []
        for i in range(3):
            if i == table_position:
                key_indices.append(actual_key_index)
            else:
                # Random indices for unused tables (privacy)
                key_indices.append(secrets.randbelow(1000))

        # Prepare payload for blockchain
        payload = {
            "image_hash": self.image_hash,
            "encrypted_nuc_token": base64.b64encode(packed_token).decode('utf-8'),
            "table_references": self.table_assignments,  # All 3 assigned tables
            "key_indices": key_indices,  # Actual + 2 random
            "timestamp": self.timestamp,
            "modification_level": self.modification_level,
        }

        # Add optional fields
        if self.parent_image_hash:
            payload["parent_image_hash"] = self.parent_image_hash

        if self.gps_hash:
            payload["gps_hash"] = self.gps_hash

        if self.owner_hash:
            payload["owner_hash"] = self.owner_hash

        if self.device_signature:
            payload["device_signature"] = base64.b64encode(
                bytes.fromhex(self.device_signature)
            ).decode('utf-8')

        if self.isp_validation:
            payload["isp_validation"] = self.isp_validation

        return payload

    @classmethod
    def from_dict(cls, data: dict) -> 'AuthenticationBundle':
        """Create AuthenticationBundle from dictionary."""
        return cls(
            image_hash=data['image_hash'],
            camera_token=data['camera_token'],
            timestamp=data['timestamp'],
            table_assignments=data.get('table_assignments', []),
            gps_hash=data.get('gps_hash'),
            owner_hash=data.get('owner_hash'),
            device_signature=data.get('device_signature')
        )


@dataclass
class CertificateBundle:
    """
    Certificate-based authentication bundle (NEW format).

    Uses self-contained X.509 certificates with Birthmark extensions instead
    of separate authentication fields.
    """
    image_hash: str  # SHA-256 of raw Bayer data (64 hex chars)
    camera_cert_pem: str  # PEM-encoded device certificate
    timestamp: int  # Unix timestamp
    gps_hash: Optional[str] = None
    owner_hash: Optional[str] = None  # SHA-256 of (owner_name + owner_salt)
    bundle_signature: Optional[str] = None  # ECDSA signature (hex)
    isp_validation: Optional[dict] = None  # ISP validation data (variance-from-expected)

    def to_json(self, private_key) -> dict:
        """
        Convert to JSON for blockchain certificate API submission.

        Args:
            private_key: Device private key for signing bundle

        Returns:
            Dictionary ready for /api/v1/submit-cert endpoint
        """
        import base64
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization, hashes
        from cryptography.hazmat.primitives.asymmetric import ec

        # Convert PEM certificate to DER bytes
        cert_pem_bytes = self.camera_cert_pem.encode('utf-8')
        cert = x509.load_pem_x509_certificate(cert_pem_bytes, default_backend())
        cert_der = cert.public_bytes(serialization.Encoding.DER)

        # Sign the bundle (image_hash + timestamp)
        if self.bundle_signature is None:
            message = f"{self.image_hash}{self.timestamp}".encode('utf-8')
            signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
            bundle_signature_b64 = base64.b64encode(signature).decode('utf-8')
        else:
            bundle_signature_b64 = base64.b64encode(
                bytes.fromhex(self.bundle_signature)
            ).decode('utf-8')

        # Prepare payload
        payload = {
            "image_hash": self.image_hash,
            "camera_cert": base64.b64encode(cert_der).decode('utf-8'),
            "software_cert": None,  # Phase 2
            "timestamp": self.timestamp,
            "bundle_signature": bundle_signature_b64,
        }

        if self.gps_hash:
            payload["gps_hash"] = self.gps_hash

        if self.owner_hash:
            payload["owner_hash"] = self.owner_hash

        if self.isp_validation:
            payload["isp_validation"] = self.isp_validation

        return payload


@dataclass
class SubmissionReceipt:
    """Receipt from submission server."""
    receipt_id: str
    status: str  # "pending_validation", "accepted", "rejected"
    timestamp: Optional[str] = None
    message: Optional[str] = None


class SubmissionClient:
    """
    HTTP client for Birthmark submission server.

    Handles synchronous and asynchronous submission of authentication bundles.
    """

    def __init__(
        self,
        server_url: str = "https://api.birthmarkstandard.org",
        timeout: int = 10,
        max_retries: int = 3
    ):
        """
        Initialize submission client.

        Args:
            server_url: Base URL of submission server
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries

        # HTTP session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Birthmark-Camera-Pi/0.1.0'
        })

    def submit_bundle(
        self,
        bundle: AuthenticationBundle,
        retry: bool = True
    ) -> SubmissionReceipt:
        """
        Submit authentication bundle to submission server (synchronous).

        Args:
            bundle: AuthenticationBundle to submit
            retry: Whether to retry on failure

        Returns:
            SubmissionReceipt from server

        Raises:
            requests.exceptions.RequestException: If submission fails after retries
        """
        endpoint = f"{self.server_url}/api/v1/submit-legacy"
        payload = bundle.to_json()

        attempts = 0
        max_attempts = self.max_retries if retry else 1

        while attempts < max_attempts:
            try:
                response = self.session.post(
                    endpoint,
                    json=payload,
                    timeout=self.timeout
                )

                # Check response status
                if response.status_code in [200, 202]:
                    data = response.json()
                    return SubmissionReceipt(
                        receipt_id=data.get('receipt_id', 'unknown'),
                        status=data.get('status', 'pending_validation'),
                        timestamp=data.get('timestamp'),
                        message=data.get('message')
                    )
                else:
                    print(f"⚠ Submission failed: {response.status_code} {response.text}")

                    if response.status_code >= 500 and retry:
                        # Server error - retry
                        attempts += 1
                        if attempts < max_attempts:
                            time.sleep(2 ** attempts)  # Exponential backoff
                            continue
                    else:
                        # Client error - don't retry
                        raise requests.exceptions.HTTPError(
                            f"HTTP {response.status_code}: {response.text}"
                        )

            except requests.exceptions.Timeout:
                print(f"⚠ Request timeout (attempt {attempts + 1}/{max_attempts})")
                attempts += 1
                if attempts < max_attempts:
                    time.sleep(2 ** attempts)
                    continue
                raise

            except requests.exceptions.ConnectionError as e:
                print(f"⚠ Connection error: {e}")
                attempts += 1
                if attempts < max_attempts:
                    time.sleep(2 ** attempts)
                    continue
                raise

        # All retries failed
        raise requests.exceptions.RequestException(
            f"Submission failed after {max_attempts} attempts"
        )

    def submit_certificate(
        self,
        bundle: CertificateBundle,
        private_key,
        retry: bool = True
    ) -> SubmissionReceipt:
        """
        Submit certificate-based authentication bundle (NEW format).

        Args:
            bundle: CertificateBundle to submit
            private_key: Device private key for signing
            retry: Whether to retry on failure

        Returns:
            SubmissionReceipt from server

        Raises:
            requests.exceptions.RequestException: If submission fails after retries
        """
        endpoint = f"{self.server_url}/api/v1/submit-cert"
        payload = bundle.to_json(private_key)

        attempts = 0
        max_attempts = self.max_retries if retry else 1

        while attempts < max_attempts:
            try:
                response = self.session.post(
                    endpoint,
                    json=payload,
                    timeout=self.timeout
                )

                # Check response status
                if response.status_code in [200, 202]:
                    data = response.json()
                    return SubmissionReceipt(
                        receipt_id=data.get('receipt_id', 'unknown'),
                        status=data.get('status', 'pending_validation'),
                        timestamp=data.get('timestamp'),
                        message=data.get('message')
                    )
                else:
                    print(f"⚠ Certificate submission failed: {response.status_code} {response.text}")

                    if response.status_code >= 500 and retry:
                        # Server error - retry
                        attempts += 1
                        if attempts < max_attempts:
                            time.sleep(2 ** attempts)  # Exponential backoff
                            continue
                    else:
                        # Client error - don't retry
                        raise requests.exceptions.HTTPError(
                            f"HTTP {response.status_code}: {response.text}"
                        )

            except requests.exceptions.Timeout:
                print(f"⚠ Request timeout (attempt {attempts + 1}/{max_attempts})")
                attempts += 1
                if attempts < max_attempts:
                    time.sleep(2 ** attempts)
                    continue
                raise

            except requests.exceptions.ConnectionError as e:
                print(f"⚠ Connection error: {e}")
                attempts += 1
                if attempts < max_attempts:
                    time.sleep(2 ** attempts)
                    continue
                raise

        # All retries failed
        raise requests.exceptions.RequestException(
            f"Certificate submission failed after {max_attempts} attempts"
        )

    def test_connection(self) -> bool:
        """
        Test connection to submission server.

        Returns:
            True if server is reachable and healthy
        """
        try:
            endpoint = f"{self.server_url}/health"
            response = self.session.get(endpoint, timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False


class SubmissionQueue:
    """
    Background submission queue for asynchronous submissions.

    Allows camera to continue capturing while bundles are submitted in background.
    Persists bundles to disk to survive power loss or network outages.
    """

    def __init__(
        self,
        client: SubmissionClient,
        max_queue_size: int = 100,
        device_private_key=None,
        persistent_queue=None
    ):
        """
        Initialize submission queue.

        Args:
            client: SubmissionClient for submissions
            max_queue_size: Maximum queue size (blocks if full)
            device_private_key: Device private key for certificate signing (optional)
            persistent_queue: PersistentQueue for disk-based reliability (optional)
        """
        self.client = client
        self.queue = queue.Queue(maxsize=max_queue_size)
        self.worker_thread: Optional[threading.Thread] = None
        self.running = False
        self.device_private_key = device_private_key
        self.persistent_queue = persistent_queue

        # Statistics
        self.submitted = 0
        self.failed = 0

    def start_worker(self) -> None:
        """Start background submission worker thread."""
        if self.running:
            print("⚠ Worker already running")
            return

        # Retransmit any pending submissions from disk
        if self.persistent_queue:
            pending = self.persistent_queue.get_pending()
            if pending:
                print(f"📤 Retransmitting {len(pending)} pending submissions from disk...")
                for submission in pending:
                    # Re-enqueue for transmission
                    self.queue.put(('retransmit', submission.bundle_id, submission.bundle_data))

        self.running = True
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="SubmissionWorker"
        )
        self.worker_thread.start()
        print("✓ Submission worker started")

    def stop_worker(self, wait: bool = True) -> None:
        """
        Stop background worker.

        Args:
            wait: If True, wait for queue to empty before stopping
        """
        if not self.running:
            return

        if wait:
            print(f"Waiting for {self.queue.qsize()} pending submissions...")
            self.queue.join()

        self.running = False

        # Signal worker to stop
        self.queue.put(None)

        if self.worker_thread:
            self.worker_thread.join(timeout=5)

        print("✓ Submission worker stopped")

    def enqueue(self, bundle) -> None:
        """
        Enqueue bundle for background submission.

        Supports both AuthenticationBundle (legacy) and CertificateBundle (new).

        Args:
            bundle: AuthenticationBundle or CertificateBundle to submit

        Raises:
            queue.Full: If queue is full
        """
        if not self.running:
            raise RuntimeError("Worker not running. Call start_worker() first.")

        # Save to persistent queue before memory queue
        if self.persistent_queue and isinstance(bundle, CertificateBundle):
            bundle_id = f"{bundle.image_hash[:16]}_{bundle.timestamp}"
            bundle_data = bundle.to_json(self.device_private_key)
            self.persistent_queue.enqueue(bundle_id, bundle_data)

        self.queue.put(bundle)

    def _worker_loop(self) -> None:
        """Worker thread main loop."""
        while self.running:
            try:
                # Get bundle from queue (blocking with timeout)
                item = self.queue.get(timeout=1)

                # None signals shutdown
                if item is None:
                    self.queue.task_done()
                    break

                # Handle retransmit vs new submission
                if isinstance(item, tuple) and item[0] == 'retransmit':
                    # Retransmitting from persistent queue
                    _, bundle_id, bundle_data = item
                    bundle = None  # Will use raw data
                else:
                    # New submission
                    bundle = item
                    bundle_id = None
                    bundle_data = None

                # Submit bundle
                try:
                    if bundle_data:
                        # Retransmit using pre-serialized data
                        response = self.client.session.post(
                            f"{self.client.server_url}/api/v1/submit-cert",
                            json=bundle_data,
                            timeout=self.client.timeout
                        )
                        if response.status_code in [200, 202]:
                            receipt_id = response.json().get('receipt_id', 'unknown')
                            self.submitted += 1
                            print(f"✓ Retransmitted: {receipt_id} (total: {self.submitted})")

                            # Remove from persistent queue on success
                            if self.persistent_queue and bundle_id:
                                self.persistent_queue.dequeue(bundle_id)
                        else:
                            raise Exception(f"HTTP {response.status_code}")

                    else:
                        # New submission
                        bundle_id_new = None
                        if isinstance(bundle, CertificateBundle):
                            bundle_id_new = f"{bundle.image_hash[:16]}_{bundle.timestamp}"

                            if not self.device_private_key:
                                raise RuntimeError("device_private_key required for certificate submission")

                            receipt = self.client.submit_certificate(bundle, self.device_private_key, retry=True)

                            # Remove from persistent queue on success
                            if self.persistent_queue:
                                self.persistent_queue.dequeue(bundle_id_new)

                        elif isinstance(bundle, AuthenticationBundle):
                            receipt = self.client.submit_bundle(bundle, retry=True)
                        else:
                            raise ValueError(f"Unknown bundle type: {type(bundle)}")

                        self.submitted += 1
                        print(f"✓ Submitted: {receipt.receipt_id} (total: {self.submitted})")

                except Exception as e:
                    self.failed += 1
                    print(f"✗ Submission failed: {e} (total failed: {self.failed})")

                    # Record attempt in persistent queue
                    if self.persistent_queue and bundle_id:
                        self.persistent_queue.record_attempt(bundle_id)

                finally:
                    self.queue.task_done()

            except queue.Empty:
                # No bundles in queue, continue
                continue

        print("Worker loop exited")

    def get_statistics(self) -> dict:
        """
        Get submission statistics.

        Returns:
            Dictionary with submission stats
        """
        return {
            'queued': self.queue.qsize(),
            'submitted': self.submitted,
            'failed': self.failed,
            'running': self.running
        }


def create_submission_client(
    server_url: str = "https://api.birthmarkstandard.org"
) -> SubmissionClient:
    """
    Create submission client with default settings.

    Args:
        server_url: Submission server URL

    Returns:
        SubmissionClient instance
    """
    return SubmissionClient(server_url=server_url)


if __name__ == "__main__":
    # Example usage
    print("=== Submission Client Test ===\n")

    # Create client
    client = SubmissionClient(server_url="http://localhost:8000")

    # Test connection
    print("Testing connection...")
    if client.test_connection():
        print("✓ Server is reachable\n")
    else:
        print("✗ Server not reachable\n")

    # Create example bundle
    bundle = AuthenticationBundle(
        image_hash="a" * 64,
        camera_token={
            "ciphertext": "b" * 64,
            "nonce": "c" * 24,
            "auth_tag": "d" * 32,
            "table_id": 3,
            "key_index": 42
        },
        timestamp=int(time.time()),
        device_signature="e" * 128
    )

    print("Example bundle created")
    print(f"  Image hash: {bundle.image_hash[:16]}...")
    print(f"  Table: {bundle.camera_token['table_id']}")
    print(f"  Timestamp: {bundle.timestamp}")
