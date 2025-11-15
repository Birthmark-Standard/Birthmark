"""
Raw Bayer data capture from Raspberry Pi HQ Camera.

Captures raw sensor data for authentication hashing.
Uses picamera2 library (libcamera backend).
"""

import hashlib
import time
from dataclasses import dataclass
from typing import Optional, Callable
import numpy as np

# Import picamera2 if available (only on Raspberry Pi)
try:
    from picamera2 import Picamera2
    PICAMERA_AVAILABLE = True
except ImportError:
    PICAMERA_AVAILABLE = False
    Picamera2 = None


@dataclass
class RawCaptureConfig:
    """Configuration for raw Bayer capture."""
    format: str = 'SRGGB10'  # 10-bit Bayer RGGB
    size: tuple[int, int] = (4056, 3040)  # 12.3MP (Sony IMX477)
    mode: int = 3  # Camera mode

    def validate(self) -> None:
        """Validate configuration."""
        if self.format not in ['SRGGB10', 'SRGGB12']:
            raise ValueError(f"Invalid format: {self.format}")

        width, height = self.size
        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid size: {self.size}")


@dataclass
class CaptureResult:
    """Result of raw capture operation."""
    raw_bayer: np.ndarray  # Raw Bayer array
    image_hash: str        # SHA-256 hash of raw data
    capture_time: float    # Time to capture (seconds)
    hash_time: float       # Time to hash (seconds)
    timestamp: int         # Unix timestamp


class RawCaptureManager:
    """
    Manages Raspberry Pi HQ Camera for raw Bayer capture.

    Phase 1: Real camera on Raspberry Pi
    Testing: Mock camera for development without hardware
    """

    def __init__(self, config: Optional[RawCaptureConfig] = None):
        """
        Initialize capture manager.

        Args:
            config: Optional capture configuration (uses defaults if None)
        """
        if config is None:
            config = RawCaptureConfig()

        config.validate()
        self.config = config
        self._camera: Optional[Picamera2] = None
        self._initialized = False

    def initialize(self) -> None:
        """
        Initialize camera hardware.

        Raises:
            RuntimeError: If picamera2 not available or camera not found
        """
        if not PICAMERA_AVAILABLE:
            raise RuntimeError(
                "picamera2 not available. "
                "This module requires Raspberry Pi with picamera2 installed."
            )

        print("Initializing Raspberry Pi HQ Camera...")

        # Create camera instance
        self._camera = Picamera2()

        # Configure for raw capture
        camera_config = self._camera.create_still_configuration(
            raw={'format': self.config.format, 'size': self.config.size}
        )

        self._camera.configure(camera_config)
        print(f"✓ Camera configured: {self.config.format} {self.config.size}")

        self._initialized = True

    def capture_raw_bayer(self) -> np.ndarray:
        """
        Capture raw Bayer data from camera sensor.

        Returns:
            Numpy array containing raw Bayer data

        Raises:
            RuntimeError: If camera not initialized
        """
        if not self._initialized:
            raise RuntimeError("Camera not initialized. Call initialize() first.")

        start_time = time.time()

        # Start camera if needed
        if not self._camera.started:
            self._camera.start()
            time.sleep(0.1)  # Brief warm-up

        # Capture raw frame
        raw_array = self._camera.capture_array("raw")

        capture_time = time.time() - start_time
        print(f"✓ Raw capture: {raw_array.shape} in {capture_time:.3f}s")

        return raw_array

    def capture_with_hash(self) -> CaptureResult:
        """
        Capture raw Bayer data and compute hash.

        Returns:
            CaptureResult with raw data, hash, and timing info
        """
        timestamp = int(time.time())

        # Capture raw
        capture_start = time.time()
        raw_bayer = self.capture_raw_bayer()
        capture_time = time.time() - capture_start

        # Hash raw data
        hash_start = time.time()
        image_hash = hash_raw_bayer(raw_bayer)
        hash_time = time.time() - hash_start

        print(f"✓ Hash computed: {image_hash[:16]}... in {hash_time:.3f}s")

        return CaptureResult(
            raw_bayer=raw_bayer,
            image_hash=image_hash,
            capture_time=capture_time,
            hash_time=hash_time,
            timestamp=timestamp
        )

    def start_camera(self) -> None:
        """Start camera for continuous capture."""
        if not self._initialized:
            raise RuntimeError("Camera not initialized")

        if not self._camera.started:
            self._camera.start()
            print("✓ Camera started")

    def stop_camera(self) -> None:
        """Stop camera."""
        if self._camera and self._camera.started:
            self._camera.stop()
            print("✓ Camera stopped")

    def close(self) -> None:
        """Close camera and cleanup resources."""
        if self._camera:
            if self._camera.started:
                self._camera.stop()
            self._camera.close()
            print("✓ Camera closed")

        self._initialized = False
        self._camera = None

    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class MockCaptureManager(RawCaptureManager):
    """
    Mock capture manager for testing without Raspberry Pi hardware.

    Generates synthetic Bayer data for development and testing.
    """

    def __init__(self, config: Optional[RawCaptureConfig] = None):
        """Initialize mock capture manager."""
        super().__init__(config)
        print("⚠ Using MockCaptureManager (synthetic data)")

    def initialize(self) -> None:
        """Initialize mock camera."""
        print("Initializing mock camera...")
        self._initialized = True
        print(f"✓ Mock camera configured: {self.config.format} {self.config.size}")

    def capture_raw_bayer(self) -> np.ndarray:
        """Generate synthetic Bayer data."""
        if not self._initialized:
            raise RuntimeError("Mock camera not initialized")

        start_time = time.time()

        width, height = self.config.size

        # Generate synthetic Bayer pattern
        # Real Bayer has values 0-1023 for 10-bit
        raw_array = np.random.randint(0, 1024, (height, width), dtype=np.uint16)

        # Add some structure (gradient) to make it look less random
        gradient = np.linspace(0, 512, width, dtype=np.uint16)
        raw_array = raw_array + gradient
        raw_array = np.clip(raw_array, 0, 1023)

        capture_time = time.time() - start_time
        print(f"✓ Mock capture: {raw_array.shape} in {capture_time:.3f}s")

        return raw_array

    def start_camera(self) -> None:
        """Start mock camera."""
        print("✓ Mock camera started")

    def stop_camera(self) -> None:
        """Stop mock camera."""
        print("✓ Mock camera stopped")

    def close(self) -> None:
        """Close mock camera."""
        print("✓ Mock camera closed")
        self._initialized = False


def hash_raw_bayer(bayer_array: np.ndarray) -> str:
    """
    Compute SHA-256 hash of raw Bayer data.

    Args:
        bayer_array: Numpy array containing raw Bayer data

    Returns:
        Hex string of SHA-256 hash (64 characters)

    Example:
        >>> data = np.random.randint(0, 1024, (100, 100), dtype=np.uint16)
        >>> hash_value = hash_raw_bayer(data)
        >>> len(hash_value)
        64
        >>> all(c in '0123456789abcdef' for c in hash_value)
        True
    """
    # Convert to bytes (ensuring consistent byte order)
    bayer_bytes = bayer_array.tobytes()

    # Compute SHA-256
    sha256_hash = hashlib.sha256(bayer_bytes).hexdigest()

    return sha256_hash


def create_capture_manager(
    use_mock: bool = False,
    config: Optional[RawCaptureConfig] = None
) -> RawCaptureManager:
    """
    Create appropriate capture manager.

    Args:
        use_mock: If True, use mock camera (default: auto-detect)
        config: Optional capture configuration

    Returns:
        RawCaptureManager or MockCaptureManager
    """
    if use_mock or not PICAMERA_AVAILABLE:
        return MockCaptureManager(config)
    else:
        return RawCaptureManager(config)


if __name__ == "__main__":
    # Example usage
    print("=== Raw Capture Test ===\n")

    # Use mock camera for testing
    with create_capture_manager(use_mock=True) as camera:
        # Single capture with hash
        result = camera.capture_with_hash()

        print(f"\nCapture Result:")
        print(f"  Shape: {result.raw_bayer.shape}")
        print(f"  Hash: {result.image_hash}")
        print(f"  Capture time: {result.capture_time:.3f}s")
        print(f"  Hash time: {result.hash_time:.3f}s")
        print(f"  Timestamp: {result.timestamp}")
