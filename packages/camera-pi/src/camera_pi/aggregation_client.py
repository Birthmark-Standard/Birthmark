"""
Aggregation server client for submitting authentication bundles.

Handles HTTP communication with the Birthmark aggregation server.
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
    Complete authentication bundle sent to blockchain aggregator.

    This format MUST match what blockchain aggregator expects.
    Updated for merged blockchain+aggregator architecture (Nov 2025).
    """
    image_hash: str  # SHA-256 of raw Bayer data (64 hex chars)
    camera_token: dict  # CameraToken.to_dict() - will be converted to blockchain format
    timestamp: int  # Unix timestamp (seconds since epoch)
    table_assignments: list[int]  # All 3 assigned tables (for privacy)
    gps_hash: Optional[str] = None  # SHA-256 of GPS coords (optional)
    device_signature: Optional[str] = None  # ECDSA signature (hex)

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
        }

        # Add optional fields
        if self.gps_hash:
            payload["gps_hash"] = self.gps_hash

        if self.device_signature:
            payload["device_signature"] = base64.b64encode(
                bytes.fromhex(self.device_signature)
            ).decode('utf-8')

        return payload

    @classmethod
    def from_dict(cls, data: dict) -> 'AuthenticationBundle':
        """Create AuthenticationBundle from dictionary."""
        return cls(
            image_hash=data['image_hash'],
            camera_token=data['camera_token'],
            timestamp=data['timestamp'],
            gps_hash=data.get('gps_hash'),
            device_signature=data.get('device_signature')
        )


@dataclass
class SubmissionReceipt:
    """Receipt from aggregation server."""
    receipt_id: str
    status: str  # "pending_validation", "accepted", "rejected"
    timestamp: Optional[str] = None
    message: Optional[str] = None


class AggregationClient:
    """
    HTTP client for Birthmark aggregation server.

    Handles synchronous and asynchronous submission of authentication bundles.
    """

    def __init__(
        self,
        server_url: str = "https://api.birthmarkstandard.org",
        timeout: int = 10,
        max_retries: int = 3
    ):
        """
        Initialize aggregation client.

        Args:
            server_url: Base URL of aggregation server
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
        Submit authentication bundle to aggregation server (synchronous).

        Args:
            bundle: AuthenticationBundle to submit
            retry: Whether to retry on failure

        Returns:
            SubmissionReceipt from server

        Raises:
            requests.exceptions.RequestException: If submission fails after retries
        """
        endpoint = f"{self.server_url}/api/v1/submit"
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

    def test_connection(self) -> bool:
        """
        Test connection to aggregation server.

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
    """

    def __init__(
        self,
        client: AggregationClient,
        max_queue_size: int = 100
    ):
        """
        Initialize submission queue.

        Args:
            client: AggregationClient for submissions
            max_queue_size: Maximum queue size (blocks if full)
        """
        self.client = client
        self.queue = queue.Queue(maxsize=max_queue_size)
        self.worker_thread: Optional[threading.Thread] = None
        self.running = False

        # Statistics
        self.submitted = 0
        self.failed = 0

    def start_worker(self) -> None:
        """Start background submission worker thread."""
        if self.running:
            print("⚠ Worker already running")
            return

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

    def enqueue(self, bundle: AuthenticationBundle) -> None:
        """
        Enqueue bundle for background submission.

        Args:
            bundle: AuthenticationBundle to submit

        Raises:
            queue.Full: If queue is full
        """
        if not self.running:
            raise RuntimeError("Worker not running. Call start_worker() first.")

        self.queue.put(bundle)

    def _worker_loop(self) -> None:
        """Worker thread main loop."""
        while self.running:
            try:
                # Get bundle from queue (blocking with timeout)
                bundle = self.queue.get(timeout=1)

                # None signals shutdown
                if bundle is None:
                    self.queue.task_done()
                    break

                # Submit bundle
                try:
                    receipt = self.client.submit_bundle(bundle, retry=True)
                    self.submitted += 1
                    print(f"✓ Submitted: {receipt.receipt_id} (total: {self.submitted})")

                except Exception as e:
                    self.failed += 1
                    print(f"✗ Submission failed: {e} (total failed: {self.failed})")

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


def create_aggregation_client(
    server_url: str = "https://api.birthmarkstandard.org"
) -> AggregationClient:
    """
    Create aggregation client with default settings.

    Args:
        server_url: Aggregation server URL

    Returns:
        AggregationClient instance
    """
    return AggregationClient(server_url=server_url)


if __name__ == "__main__":
    # Example usage
    print("=== Aggregation Client Test ===\n")

    # Create client
    client = AggregationClient(server_url="http://localhost:8000")

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
