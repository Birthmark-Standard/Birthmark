# Raspberry Pi Camera Package - Implementation Plan

**Package:** `packages/camera-pi`
**Phase:** Phase 1 (Hardware Prototype)
**Target Hardware:** Raspberry Pi 4 + HQ Camera + LetsTrust TPM
**Status:** Design Complete, Ready for Implementation

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Module Design](#module-design)
3. [Data Flow](#data-flow)
4. [Authentication Bundle Format](#authentication-bundle-format)
5. [Key Derivation](#key-derivation)
6. [Project Structure](#project-structure)
7. [Implementation Order](#implementation-order)
8. [Testing Strategy](#testing-strategy)
9. [Integration Points](#integration-points)

---

## Architecture Overview

### Design Philosophy

The camera-pi package demonstrates **zero-latency photo authentication** through parallel processing:

1. **Raw Bayer data** flows from sensor to BOTH:
   - ISP (Image Signal Processor) → User's processed image
   - TPM (Trusted Platform Module) → Authentication hash

2. **Background submission** queues authentication bundles without blocking user

3. **Hardware-backed security** using TPM for signing and key storage

### Core Innovation

```
         Camera Sensor (Sony IMX477)
                  │
                  │ Raw Bayer Data (12MP)
                  ├──────────────┬──────────────┐
                  │              │              │
                  ▼              ▼              ▼
         ISP Processing    TPM Hashing    DMA Buffer
         (600ms)          (100ms)         (Background)
                  │              │              │
                  ▼              ▼              │
         User's JPEG    Authentication     Queue for
         Image          Bundle             Submission
                                               │
                                               ▼
                                        Aggregation Server
                                        (Async, non-blocking)
```

**User sees:** Normal camera experience (~600ms shutter)
**Behind the scenes:** Parallel hashing + async network submission

---

## Module Design

### 1. `raw_capture.py` - Raw Sensor Data Capture

**Purpose:** Capture raw Bayer data from Raspberry Pi HQ Camera

**Key Classes:**

```python
class RawCaptureConfig:
    """Configuration for raw capture"""
    format: str = 'SRGGB10'  # 10-bit Bayer RGGB
    size: tuple[int, int] = (4056, 3040)  # 12.3MP
    mode: int = 3  # Camera mode

class RawCaptureManager:
    """Manages camera capture and raw data access"""

    def __init__(self, config: RawCaptureConfig)
    def capture_raw_bayer(self) -> np.ndarray
    def capture_with_processed(self) -> tuple[np.ndarray, bytes]
    def start_continuous_capture(self, callback: Callable)
```

**Implementation Details:**
- Use `picamera2` library (libcamera backend)
- Access raw Bayer array via `capture_array("raw")`
- Support both single capture and continuous modes
- Handle camera initialization and cleanup gracefully

**Performance Target:** <500ms raw capture

---

### 2. `tpm_interface.py` - TPM Integration

**Purpose:** Interface with LetsTrust TPM for hashing, signing, and encryption

**Key Classes:**

```python
class TPMConfig:
    """TPM configuration"""
    device_path: str = '/dev/tpm0'
    primary_key_handle: int = 0x81010001

class TPMInterface:
    """Main TPM interface"""

    def __init__(self, config: TPMConfig)
    def verify_tpm_available(self) -> bool
    def hash_data(self, data: bytes) -> bytes
    def sign_data(self, data: bytes) -> bytes
    def encrypt_aes_gcm(self, plaintext: bytes, key: bytes) -> EncryptedData
    def derive_key_hkdf(self, master_key: bytes, key_index: int) -> bytes
```

**Key Derivation (CRITICAL - Must match SMA exactly):**

```python
def derive_encryption_key(
    master_key: bytes,  # 32 bytes from provisioning
    key_index: int,     # 0-999
    context: bytes = b"Birthmark"
) -> bytes:
    """
    HKDF-SHA256 key derivation.

    MUST produce identical output to SMA implementation:
    packages/sma/src/key_tables/key_derivation.py::derive_encryption_key
    """
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives import hashes

    info = key_index.to_bytes(4, 'big') + context

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=info
    )

    return hkdf.derive(master_key)
```

**Implementation Notes:**
- Phase 1: Use Python `cryptography` library (software crypto)
- Phase 2 (optional): Investigate TPM2-TSS Python bindings for hardware crypto
- Store device private key securely (file-based in Phase 1)
- Load NUC hash and master keys from provisioning data

**Performance Target:** <100ms for hash + sign

---

### 3. `camera_token.py` - Camera Token Generation

**Purpose:** Create encrypted NUC tokens for SMA validation

**Key Classes:**

```python
@dataclass
class CameraToken:
    """Encrypted NUC token"""
    ciphertext: str  # hex-encoded
    nonce: str       # hex-encoded (12 bytes)
    auth_tag: str    # hex-encoded (16 bytes)
    table_id: int    # Which table (from assigned 3)
    key_index: int   # Which key in table (0-999)

class TokenGenerator:
    """Generates camera tokens"""

    def __init__(
        self,
        nuc_hash: bytes,           # From provisioning
        table_assignments: list[int],  # 3 table IDs
        master_keys: dict[int, bytes]  # table_id -> master_key
    )

    def generate_token(self) -> CameraToken:
        """
        Generate encrypted NUC token.

        Steps:
        1. Select random table from assigned 3
        2. Select random key index (0-999)
        3. Derive encryption key using HKDF
        4. Encrypt NUC hash with AES-256-GCM
        5. Return CameraToken
        """
```

**Encryption Details:**
- Algorithm: AES-256-GCM
- Key: 32 bytes derived via HKDF
- Nonce: 12 bytes random (unique per encryption)
- Auth tag: 16 bytes (GCM authentication)
- Plaintext: 32-byte NUC hash

---

### 4. `aggregation_client.py` - Aggregation Server Client

**Purpose:** Submit authentication bundles to aggregation server

**Key Classes:**

```python
@dataclass
class AuthenticationBundle:
    """Complete authentication bundle"""
    image_hash: str              # SHA-256 of raw Bayer (64 hex chars)
    camera_token: CameraToken    # Encrypted NUC token
    timestamp: int               # Unix timestamp
    gps_hash: Optional[str]      # SHA-256 of GPS coords (optional)
    device_signature: str        # ECDSA signature over bundle

class AggregationClient:
    """HTTP client for aggregation server"""

    def __init__(self, server_url: str, timeout: int = 10)

    def submit_bundle(self, bundle: AuthenticationBundle) -> SubmissionReceipt

    def submit_bundle_async(self, bundle: AuthenticationBundle) -> None
        """Queue for background submission"""

class SubmissionQueue:
    """Background submission queue"""

    def __init__(self, client: AggregationClient)

    def enqueue(self, bundle: AuthenticationBundle)

    def start_worker(self)

    def stop_worker(self)
```

**API Endpoint:**
```
POST /api/v1/submit
Content-Type: application/json

{
    "image_hash": "a1b2c3d4...",  # 64 hex chars
    "camera_token": {
        "ciphertext": "...",
        "nonce": "...",
        "auth_tag": "...",
        "table_id": 42,
        "key_index": 137
    },
    "timestamp": 1732000000,
    "gps_hash": "optional...",
    "device_signature": "..."
}

Response: 202 Accepted
{
    "receipt_id": "uuid",
    "status": "pending_validation"
}
```

---

### 5. `provisioning_client.py` - Device Provisioning

**Purpose:** Load provisioning data from SMA

**Key Classes:**

```python
@dataclass
class ProvisioningData:
    """Data from SMA provisioning"""
    device_serial: str
    device_certificate: str      # PEM-encoded
    certificate_chain: str       # PEM-encoded
    device_private_key: str      # PEM-encoded
    device_public_key: str       # PEM-encoded
    table_assignments: list[int] # 3 table IDs
    nuc_hash: str               # Hex-encoded
    device_family: str

class ProvisioningClient:
    """Loads provisioning data"""

    def load_from_file(self, path: Path) -> ProvisioningData

    def save_to_file(self, data: ProvisioningData, path: Path)

    def get_master_keys(self) -> dict[int, bytes]:
        """
        Get master keys for assigned tables.

        Phase 1: Loaded from local key_tables.json
        Phase 2+: Retrieved from manufacturer during provisioning
        """
```

**Provisioning File Format (JSON):**
```json
{
    "device_serial": "RaspberryPi-Prototype-001",
    "device_certificate": "-----BEGIN CERTIFICATE-----\n...",
    "certificate_chain": "-----BEGIN CERTIFICATE-----\n...",
    "device_private_key": "-----BEGIN PRIVATE KEY-----\n...",
    "device_public_key": "-----BEGIN PUBLIC KEY-----\n...",
    "table_assignments": [3, 7, 9],
    "nuc_hash": "a1b2c3d4...",
    "device_family": "Raspberry Pi",
    "master_keys": {
        "3": "0123456789abcdef...",
        "7": "fedcba9876543210...",
        "9": "abcdef0123456789..."
    }
}
```

---

### 6. `main.py` - CLI Application

**Purpose:** Main application orchestrating capture and submission

**Key Classes:**

```python
class BirthmarkCamera:
    """Main camera application"""

    def __init__(
        self,
        provisioning_path: Path,
        aggregation_url: str,
        output_dir: Path
    )

    def capture_photo(self) -> CaptureResult:
        """
        Capture single photo with authentication.

        Workflow:
        1. Capture raw Bayer data
        2. Hash raw data (background)
        3. Generate camera token (background)
        4. Sign bundle (background)
        5. Queue submission (background)
        6. Process ISP image (foreground)
        7. Save JPEG to disk
        8. Return to user

        User waits only for step 6-7 (~600ms)
        Steps 2-5 run in parallel (~150ms total)
        """

    def capture_timelapse(
        self,
        interval: int,
        count: int = 0
    ):
        """Timelapse mode"""

    def test_submission(self) -> bool:
        """Test aggregation server connectivity"""
```

**CLI Interface:**

```bash
# Single capture
python -m camera_pi capture

# Timelapse (30 second interval, 100 photos)
python -m camera_pi timelapse --interval 30 --count 100

# Continuous (infinite)
python -m camera_pi timelapse --interval 10

# Test connectivity
python -m camera_pi test

# Show provisioning info
python -m camera_pi info
```

---

## Data Flow

### Complete Capture Workflow

```
[User presses shutter button]
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│ 1. CAPTURE RAW BAYER DATA                               │
│    raw_capture.capture_raw_bayer()                      │
│    Time: ~500ms                                         │
└─────────────────┬───────────────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
        ▼                   ▼
┌──────────────────┐  ┌──────────────────────────────┐
│ 2a. PARALLEL:    │  │ 2b. PARALLEL:                │
│ Process ISP      │  │ Hash & Authenticate          │
│ (FOREGROUND)     │  │ (BACKGROUND)                 │
│                  │  │                              │
│ - Demosaic       │  │ - TPM hash (100ms)          │
│ - White balance  │  │ - Generate token (20ms)     │
│ - JPEG encode    │  │ - Sign bundle (30ms)        │
│                  │  │ - Queue submission (1ms)    │
│ Time: ~600ms     │  │ Total: ~151ms               │
└────────┬─────────┘  └──────────────┬───────────────┘
         │                           │
         │ [User gets image]         │ [Network happens later]
         ▼                           ▼
┌─────────────────┐         ┌──────────────────┐
│ 3. SAVE JPEG    │         │ 3. SUBMIT BUNDLE │
│ output/IMG.jpg  │         │ (Async worker)   │
│ Time: ~100ms    │         │ Time: variable   │
└─────────────────┘         └──────────────────┘

TOTAL USER WAIT: ~700ms (steps 1 + 2a + 3)
BACKGROUND WORK: ~151ms (step 2b, overlapped)
```

### Parallel Processing Implementation

```python
import threading
import time

def capture_and_process(self):
    """Parallel capture workflow"""

    # Step 1: Capture raw data
    start = time.time()
    raw_bayer = self.capture_manager.capture_raw_bayer()
    capture_time = time.time() - start

    # Step 2: Start parallel threads
    results = {}

    def background_authenticate():
        # Hash raw Bayer
        image_hash = self.tpm.hash_data(raw_bayer.tobytes())

        # Generate camera token
        token = self.token_generator.generate_token()

        # Create bundle
        bundle = AuthenticationBundle(
            image_hash=image_hash.hex(),
            camera_token=token,
            timestamp=int(time.time()),
            gps_hash=None,
            device_signature=None  # Sign below
        )

        # Sign bundle
        bundle_json = json.dumps(bundle.__dict__, sort_keys=True)
        signature = self.tpm.sign_data(bundle_json.encode())
        bundle.device_signature = signature.hex()

        # Queue for submission
        self.submission_queue.enqueue(bundle)

        results['bundle'] = bundle

    def foreground_process():
        # Process through ISP
        processed_image = process_isp(raw_bayer)
        results['image'] = processed_image

    # Start both threads
    bg_thread = threading.Thread(target=background_authenticate)
    fg_thread = threading.Thread(target=foreground_process)

    bg_thread.start()
    fg_thread.start()

    # Wait only for foreground (user image)
    fg_thread.join()

    # Background continues (or finishes faster)
    # Don't wait for bg_thread - let it complete async

    return results['image']
```

---

## Authentication Bundle Format

### Bundle Structure

```python
@dataclass
class AuthenticationBundle:
    """
    Complete authentication bundle sent to aggregation server.

    This format MUST match what aggregation server expects.
    """

    # Image identification
    image_hash: str  # SHA-256 of raw Bayer data (64 hex chars)

    # Camera authentication
    camera_token: CameraToken  # Encrypted NUC hash

    # Metadata
    timestamp: int  # Unix timestamp (seconds since epoch)
    gps_hash: Optional[str]  # SHA-256 of GPS coords (optional)

    # Signature
    device_signature: str  # ECDSA signature over entire bundle

    def to_json(self) -> dict:
        """Convert to JSON for API submission"""
        return {
            "image_hash": self.image_hash,
            "camera_token": {
                "ciphertext": self.camera_token.ciphertext,
                "nonce": self.camera_token.nonce,
                "auth_tag": self.camera_token.auth_tag,
                "table_id": self.camera_token.table_id,
                "key_index": self.camera_token.key_index
            },
            "timestamp": self.timestamp,
            "gps_hash": self.gps_hash,
            "device_signature": self.device_signature
        }
```

### Signing Process

```python
def sign_bundle(bundle: AuthenticationBundle, private_key: ec.EllipticCurvePrivateKey) -> bytes:
    """
    Sign authentication bundle with device private key.

    Signature covers all fields to prevent tampering.
    """
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec

    # Serialize bundle to canonical JSON
    bundle_dict = bundle.to_json()
    bundle_dict.pop('device_signature', None)  # Don't sign signature field
    bundle_json = json.dumps(bundle_dict, sort_keys=True)

    # Sign with ECDSA P-256 + SHA-256
    signature = private_key.sign(
        bundle_json.encode('utf-8'),
        ec.ECDSA(hashes.SHA256())
    )

    return signature
```

---

## Key Derivation

### HKDF-SHA256 Implementation

**CRITICAL:** This must match SMA exactly. Any discrepancy causes validation failure.

```python
def derive_encryption_key(
    master_key: bytes,
    key_index: int,
    context: bytes = b"Birthmark",
    key_length: int = 32
) -> bytes:
    """
    Derive encryption key from master key using HKDF-SHA256.

    Reference implementation: packages/sma/src/key_tables/key_derivation.py

    Args:
        master_key: 32-byte master key from provisioning
        key_index: Integer 0-999 identifying derived key
        context: Domain separation string (default: b"Birthmark")
        key_length: Output length in bytes (default: 32 for AES-256)

    Returns:
        32-byte derived encryption key
    """
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives import hashes

    # Validation
    if len(master_key) != 32:
        raise ValueError(f"Master key must be 32 bytes, got {len(master_key)}")
    if not 0 <= key_index <= 999:
        raise ValueError(f"Key index must be 0-999, got {key_index}")

    # Encode key index as 4-byte big-endian + context
    info = key_index.to_bytes(4, 'big') + context

    # HKDF-SHA256
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=key_length,
        salt=None,  # No salt (uses zeros)
        info=info
    )

    derived_key = hkdf.derive(master_key)
    return derived_key
```

### Test Vectors

```python
# Test vectors to validate against SMA implementation
TEST_VECTORS = [
    {
        "master_key": bytes.fromhex(
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        ),
        "key_index": 0,
        "expected_key": None,  # Run SMA test to get expected value
    },
    {
        "master_key": bytes.fromhex(
            "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        ),
        "key_index": 999,
        "expected_key": None,
    },
]

def validate_key_derivation():
    """Validate key derivation against test vectors"""
    for vector in TEST_VECTORS:
        derived = derive_encryption_key(
            vector["master_key"],
            vector["key_index"]
        )
        print(f"Key index {vector['key_index']}: {derived.hex()}")
        # Compare against SMA output
```

---

## Project Structure

```
packages/camera-pi/
├── pyproject.toml              # Project metadata and dependencies
├── README.md                   # Package documentation
├── PLAN.md                     # This file
├── setup.py                    # Optional setuptools config
│
├── src/
│   └── camera_pi/
│       ├── __init__.py
│       │
│       ├── raw_capture.py      # Raw Bayer capture
│       ├── tpm_interface.py    # TPM integration
│       ├── camera_token.py     # Token generation
│       ├── aggregation_client.py  # Server communication
│       ├── provisioning_client.py # Provisioning data
│       ├── main.py             # CLI application
│       │
│       ├── crypto/
│       │   ├── __init__.py
│       │   ├── key_derivation.py   # HKDF implementation
│       │   ├── signing.py          # ECDSA signing
│       │   └── encryption.py       # AES-GCM encryption
│       │
│       └── utils/
│           ├── __init__.py
│           ├── config.py       # Configuration management
│           ├── logging.py      # Logging setup
│           └── exceptions.py   # Custom exceptions
│
├── tests/
│   ├── __init__.py
│   ├── test_raw_capture.py
│   ├── test_tpm_interface.py
│   ├── test_camera_token.py
│   ├── test_aggregation_client.py
│   ├── test_key_derivation.py
│   ├── test_integration.py
│   │
│   ├── fixtures/
│   │   ├── test_vectors.json   # Key derivation test vectors
│   │   └── sample_provision.json
│   │
│   └── mocks/
│       ├── mock_tpm.py         # Mock TPM for testing without hardware
│       ├── mock_camera.py      # Mock camera for unit tests
│       └── mock_aggregator.py  # Mock server for network tests
│
├── scripts/
│   ├── setup_device.sh         # Initial hardware setup
│   ├── provision_device.py     # Load provisioning data
│   ├── test_camera.py          # Test camera functionality
│   ├── benchmark.py            # Performance benchmarking
│   └── validate_sma_compat.py  # Validate SMA compatibility
│
├── configs/
│   ├── camera_config.yaml      # Camera settings
│   ├── default_provision.json  # Example provisioning data
│   └── logging_config.yaml     # Logging configuration
│
└── data/                       # Runtime data (gitignored)
    ├── provisioning.json       # Device provisioning data
    ├── device_private_key.pem  # Device private key
    └── captures/               # Captured images
```

---

## Implementation Order

### Phase 1: Core Functionality (Week 1)

**Goal:** Basic capture and hashing working

1. **Project setup**
   - [x] Create directory structure
   - [x] Set up pyproject.toml
   - [ ] Configure testing framework
   - [ ] Set up logging

2. **`raw_capture.py`**
   - [ ] Implement `RawCaptureConfig`
   - [ ] Implement `RawCaptureManager`
   - [ ] Test on actual Raspberry Pi HQ Camera
   - [ ] Validate raw Bayer data format
   - [ ] Benchmark capture time

3. **`crypto/key_derivation.py`**
   - [ ] Implement HKDF-SHA256
   - [ ] Generate test vectors
   - [ ] Validate against SMA implementation
   - [ ] Write unit tests

4. **`provisioning_client.py`**
   - [ ] Implement `ProvisioningData` dataclass
   - [ ] Implement file loading
   - [ ] Validate provisioning data format
   - [ ] Write unit tests

### Phase 2: TPM Integration (Week 2)

**Goal:** Hardware-backed authentication working

5. **`tpm_interface.py`**
   - [ ] Implement TPM availability check
   - [ ] Implement software-based hashing (fallback)
   - [ ] Implement signing with device private key
   - [ ] Test on Raspberry Pi with LetsTrust TPM
   - [ ] Benchmark TPM operations

6. **`camera_token.py`**
   - [ ] Implement `CameraToken` dataclass
   - [ ] Implement `TokenGenerator`
   - [ ] Implement AES-GCM encryption
   - [ ] Test token generation
   - [ ] Validate token format

7. **`crypto/signing.py`**
   - [ ] Implement ECDSA signing
   - [ ] Implement signature verification (for testing)
   - [ ] Write unit tests

### Phase 3: Network Communication (Week 3)

**Goal:** Submission to aggregation server working

8. **`aggregation_client.py`**
   - [ ] Implement `AuthenticationBundle` dataclass
   - [ ] Implement synchronous submission
   - [ ] Implement asynchronous queue
   - [ ] Add retry logic
   - [ ] Test with mock aggregation server
   - [ ] Test with real aggregation server

9. **Integration testing**
   - [ ] End-to-end capture → submit flow
   - [ ] Validate with aggregation server
   - [ ] Test error handling
   - [ ] Test network failures

### Phase 4: CLI & Polish (Week 4)

**Goal:** Complete user-facing application

10. **`main.py`**
    - [ ] Implement CLI argument parsing
    - [ ] Implement single capture mode
    - [ ] Implement timelapse mode
    - [ ] Implement info/status commands
    - [ ] Add progress indicators
    - [ ] Add error messages

11. **Testing & Documentation**
    - [ ] Write integration tests
    - [ ] Performance benchmarking
    - [ ] Update README
    - [ ] Write user guide
    - [ ] Create demo video

12. **Optimization**
    - [ ] Profile code
    - [ ] Optimize hot paths
    - [ ] Validate <5 second target
    - [ ] Test sustained capture rate

---

## Testing Strategy

### Unit Tests

Each module has comprehensive unit tests:

```python
# tests/test_key_derivation.py
def test_derive_key_matches_sma():
    """Validate key derivation matches SMA implementation"""
    # Use test vectors from SMA
    # Compare outputs byte-for-byte

def test_derive_key_deterministic():
    """Same inputs produce same outputs"""

def test_derive_key_different_indices():
    """Different indices produce different keys"""

# tests/test_camera_token.py
def test_token_generation():
    """Token generation produces valid format"""

def test_token_encryption_decryption():
    """Encrypted tokens can be decrypted"""

def test_token_random_selection():
    """Tokens use random table/key selection"""

# tests/test_aggregation_client.py
def test_bundle_format():
    """Bundle matches aggregation server expectations"""

def test_async_submission():
    """Async submission doesn't block"""
```

### Integration Tests

```python
# tests/test_integration.py
def test_end_to_end_capture():
    """Complete capture → submit workflow"""
    # 1. Capture raw
    # 2. Hash
    # 3. Generate token
    # 4. Sign bundle
    # 5. Submit to mock server
    # 6. Verify format

def test_sma_validation():
    """SMA can validate our tokens"""
    # Generate token
    # Submit to real SMA validation endpoint
    # Verify PASS response
```

### Mock Objects

```python
# tests/mocks/mock_tpm.py
class MockTPM:
    """Mock TPM for testing without hardware"""

    def hash_data(self, data: bytes) -> bytes:
        return hashlib.sha256(data).digest()

    def sign_data(self, data: bytes) -> bytes:
        # Use test private key
        return fake_sign(data)

# tests/mocks/mock_camera.py
class MockCamera:
    """Mock camera for unit tests"""

    def capture_raw_bayer(self) -> np.ndarray:
        # Return synthetic Bayer data
        return np.random.randint(0, 1024, (3040, 4056), dtype=np.uint16)
```

### Performance Tests

```python
# tests/test_performance.py
def test_capture_time():
    """Capture completes in <500ms"""

def test_hash_time():
    """Hashing completes in <100ms"""

def test_total_user_latency():
    """Total user wait <700ms"""

def test_parallel_overhead():
    """Background work <5% CPU"""
```

---

## Integration Points

### 1. SMA Integration

**Provisioning:**
- Load provisioning data from SMA output
- Extract table assignments and master keys
- Store device certificate and private key

**Validation:**
- Generate camera tokens matching SMA expectations
- Ensure key derivation matches exactly
- Test against SMA validation endpoint

**Key Files:**
- `packages/sma/src/key_tables/key_derivation.py` - MUST MATCH
- `packages/sma/src/provisioning/provisioner.py` - Provisioning format
- `packages/sma/scripts/provision_device.py` - Provisioning script

### 2. Aggregation Server Integration

**Submission API:**
- POST /api/v1/submit
- Bundle format must match server expectations
- Handle 202 Accepted responses
- Retry on failures

**Testing:**
- Mock aggregation server for unit tests
- Real aggregation server for integration tests
- Validate receipt IDs

### 3. Hardware Integration

**Raspberry Pi Camera:**
- picamera2 library
- libcamera backend
- Raw Bayer access via `capture_array("raw")`

**LetsTrust TPM:**
- Device: `/dev/tpm0`
- Commands: `tpm2_hash`, `tpm2_sign`
- Python: `python-tpm2-pytss` (optional)

**GPS Module (Optional):**
- Serial interface `/dev/ttyS0`
- NMEA sentence parsing
- Coordinate hashing

---

## Configuration Management

### Camera Configuration

```yaml
# configs/camera_config.yaml
camera:
  format: SRGGB10
  size: [4056, 3040]
  mode: 3

capture:
  output_dir: ./data/captures
  jpeg_quality: 95

performance:
  parallel_processing: true
  async_submission: true
  submission_queue_size: 100

aggregation:
  server_url: https://api.birthmarkstandard.org
  timeout: 10
  retry_attempts: 3
  retry_delay: 5
```

### Logging Configuration

```yaml
# configs/logging_config.yaml
version: 1
formatters:
  detailed:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

handlers:
  console:
    class: logging.StreamHandler
    formatter: detailed
    level: INFO

  file:
    class: logging.FileHandler
    filename: camera.log
    formatter: detailed
    level: DEBUG

root:
  level: DEBUG
  handlers: [console, file]
```

---

## Security Considerations

### Secure Storage

**Device private key:**
- Store in PEM format
- File permissions: 0600 (owner read/write only)
- Phase 2: Consider TPM NVRAM storage

**Provisioning data:**
- Contains sensitive material (NUC hash, master keys)
- File permissions: 0600
- Never commit to git

**Master keys:**
- Loaded from provisioning data
- Kept in memory only during operation
- Cleared on shutdown

### Signature Validation

**Device certificate:**
- Validate against SMA root CA
- Check expiration
- Verify certificate chain

**Bundle signatures:**
- Sign entire bundle to prevent tampering
- Use ECDSA P-256 + SHA-256
- Aggregation server verifies signatures

---

## Performance Targets

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Raw capture | <500ms | `time.time()` around capture |
| SHA-256 hash | <100ms | TPM or software hash |
| Token generation | <20ms | HKDF + AES-GCM |
| Bundle signing | <30ms | ECDSA signature |
| **Total background** | **<150ms** | **Steps 2-5 parallel** |
| ISP processing | <600ms | libcamera ISP |
| **Total user wait** | **<700ms** | **Capture + ISP** |
| Sustained rate | 1 photo/sec | Timelapse test |

---

## Deliverables

### Code
- [x] Project structure
- [ ] All modules implemented
- [ ] Unit tests (>80% coverage)
- [ ] Integration tests
- [ ] Performance benchmarks

### Documentation
- [x] PLAN.md (this file)
- [ ] Updated README.md
- [ ] API documentation
- [ ] User guide
- [ ] Troubleshooting guide

### Testing
- [ ] Hardware validation on Raspberry Pi
- [ ] SMA compatibility validation
- [ ] Aggregation server integration
- [ ] Performance benchmarks
- [ ] Photography club demo

---

## Success Criteria

- [ ] Camera captures 12MP raw Bayer data reliably
- [ ] SHA-256 hashing completes in <100ms
- [ ] Key derivation matches SMA exactly (test vectors pass)
- [ ] Camera tokens validated by SMA (PASS response)
- [ ] Authentication bundles accepted by aggregation server
- [ ] Total user latency <700ms
- [ ] Parallel processing overhead <5% CPU
- [ ] Sustained capture rate >1 photo/second
- [ ] 100+ consecutive captures without failure
- [ ] All tests passing
- [ ] Code coverage >80%

---

## Next Steps

1. **Implement Phase 1** (Core functionality)
   - Set up project structure
   - Implement raw capture
   - Implement key derivation
   - Validate against SMA

2. **Implement Phase 2** (TPM integration)
   - Integrate with LetsTrust TPM
   - Test on actual hardware
   - Benchmark performance

3. **Implement Phase 3** (Network)
   - Build aggregation client
   - Test with aggregation server
   - Implement async submission

4. **Implement Phase 4** (Polish)
   - Complete CLI
   - Write documentation
   - Create demo

---

**Document Status:** Complete
**Owner:** Samuel C. Ryan
**Last Updated:** 2025-11-15
**Ready for Implementation:** ✓
