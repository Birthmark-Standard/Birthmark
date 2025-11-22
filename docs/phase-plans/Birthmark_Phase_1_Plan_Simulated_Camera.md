# Birthmark Phase 1 Plan - Simulated Camera

**Version:** 1.0  
**Date:** November 2025  
**Phase:** Phase 1 (Hardware Prototype)  
**Timeline:** 4-6 weeks

---

## Purpose

This document specifies the hardware prototype camera system for Phase 1 development. The simulated camera demonstrates the complete Birthmark Protocol authentication workflow using off-the-shelf components to prove the parallel raw sensor hashing architecture.

**Phase 1 Goal:** Build a functional Raspberry Pi-based camera that captures raw Bayer data, hashes it in parallel with ISP processing using a hardware secure element, and submits authentication bundles to the Aggregation Server. This proves manufacturers can implement the architecture without user-facing latency.

**Why This Matters:**
- Demonstrates raw sensor data can be tapped in parallel with ISP processing
- Proves secure element integration is feasible at hardware level
- Validates zero user-facing latency claim
- Provides tangible demonstration unit for manufacturer discussions
- Enables real-world user testing with photography clubs

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  RASPBERRY PI 4 MODEL B                     │
│                                                             │
│  ┌──────────────────────┐                                  │
│  │  Camera Module HQ    │                                  │
│  │  (Sony IMX477)       │                                  │
│  │  Raw Bayer Output    │                                  │
│  └──────────┬───────────┘                                  │
│             │ CSI-2 Interface                              │
│             ▼                                              │
│  ┌──────────────────────────────────────────────────────┐ │
│  │             Unicam CSI-2 Receiver                    │ │
│  │         (Raw Bayer Data Capture)                     │ │
│  └──────────┬───────────────────────────────────────────┘ │
│             │                                              │
│             │ Split DMA Transfer                           │
│             │                                              │
│      ┌──────┴──────┐                                      │
│      │             │                                      │
│      ▼             ▼                                      │
│  ┌────────┐   ┌─────────────────┐                        │
│  │  DMA   │   │      DMA        │                        │
│  │Buffer 1│   │   Buffer 2      │                        │
│  └───┬────┘   └────┬────────────┘                        │
│      │             │                                      │
│      │             ▼                                      │
│      │      ┌──────────────────┐                         │
│      │      │  libcamera ISP   │                         │
│      │      │  - Demosaic      │                         │
│      │      │  - White Balance │                         │
│      │      │  - Denoise       │                         │
│      │      │  - JPEG Encode   │                         │
│      │      └────┬─────────────┘                         │
│      │           │                                        │
│      │           ▼                                        │
│      │      [Processed Image]                            │
│      │      Saved to Storage                             │
│      │                                                    │
│      │                                                    │
│      │      ┌────────────────────────────────────┐       │
│      └─────►│  LetsTrust TPM Module              │       │
│             │  (Infineon SLB 9670)               │       │
│             │                                    │       │
│             │  1. Compute SHA-256(Raw Bayer)     │       │
│             │  2. Get NUC hash from storage      │       │
│             │  3. Encrypt NUC with rotating key  │       │
│             │  4. Sign complete bundle           │       │
│             └────┬───────────────────────────────┘       │
│                  │                                        │
│                  ▼                                        │
│         [Authentication Bundle]                           │
│         {image_hash, camera_token,                        │
│          timestamp, gps_hash}                             │
│                  │                                        │
│                  │ HTTPS POST                             │
└──────────────────┼───────────────────────────────────────┘
                   │
                   ▼
        [Aggregation Server]
        api.birthmarkstandard.org
```

**Key Innovation:** Raw Bayer data flows to BOTH the ISP pipeline (for user images) AND the TPM (for authentication) simultaneously via DMA. The user never waits for authentication.

---

## Hardware Bill of Materials

### Core Components

| Component | Model/Spec | Quantity | Unit Cost | Total | Source |
|-----------|------------|----------|-----------|-------|--------|
| Single Board Computer | Raspberry Pi 4 Model B (4GB) | 1 | $55 | $55 | raspberrypi.com |
| Camera Module | Raspberry Pi HQ Camera | 1 | $50 | $50 | raspberrypi.com |
| Camera Lens | 6mm Wide Angle or 16mm Telephoto | 1 | $25-50 | $35 | raspberrypi.com |
| Secure Element | LetsTrust TPM (SLB 9670) | 1 | $25 | $25 | pi3g.com |
| Storage | SanDisk Extreme 64GB microSD (A2) | 1 | $12 | $12 | Amazon |
| Power Supply | Official Pi 4 USB-C 5V/3A | 1 | $8 | $8 | raspberrypi.com |
| Case | Raspberry Pi 4 Case with Fan | 1 | $10 | $10 | Amazon |
| Cables | GPIO Header + Camera Cable | 1 | $5 | $5 | Included |
| **TOTAL** | | | | **$200** | |

**Optional Additions:**
- GPS Module: Neo-6M GPS (~$15) for GPS hashing
- RTC Module: DS3231 RTC (~$8) for accurate timestamps offline
- Battery Pack: Anker PowerCore 20000mAh (~$40) for field testing

**Recommended Budget:** $250 with GPS and RTC

---

## Component 1: Raw Sensor Data Capture

### Hardware: Raspberry Pi HQ Camera

**Specifications:**
- Sensor: Sony IMX477
- Resolution: 12.3 megapixels (4056 × 3040)
- Sensor Size: 7.9mm diagonal (1/2.3")
- Pixel Size: 1.55 × 1.55 µm
- Output Format: RAW10 Bayer (SRGGB10)
- Interface: 2-lane CSI-2

**Why This Camera:**
- Provides true raw Bayer data access (not all cameras do)
- Well-documented in Raspberry Pi ecosystem
- Professional image quality for photography club testing
- Interchangeable C/CS-mount lenses

### Software: libcamera + raspiraw

**Primary Tool: libcamera**
```bash
# Capture raw DNG file
libcamera-still -r -o image.dng --raw

# Capture raw + JPEG simultaneously
libcamera-still -r -o image.jpg --raw
```

**Low-Level Tool: raspiraw (for development)**
```bash
git clone https://github.com/raspberrypi/raspiraw
cd raspiraw
make

# Capture raw Bayer frames
./raspiraw -md 3 -t 1000 -hd0 -sr 1 -o /dev/shm/out.%04d.raw
```

### Implementation: Raw Data Access

**Method 1: Using libcamera (Recommended)**
```python
#!/usr/bin/env python3
"""
Raw Bayer capture with libcamera
"""
from picamera2 import Picamera2
import numpy as np
import hashlib

def capture_raw_bayer():
    """Capture raw Bayer data and return as numpy array"""
    picam2 = Picamera2()
    
    # Configure for raw capture
    config = picam2.create_still_configuration(
        raw={'format': 'SRGGB10', 'size': (4056, 3040)}
    )
    picam2.configure(config)
    picam2.start()
    
    # Capture raw frame
    raw_array = picam2.capture_array("raw")
    
    picam2.stop()
    
    return raw_array

def hash_raw_bayer(bayer_array):
    """Compute SHA-256 hash of raw Bayer data"""
    # Convert to bytes (ensuring consistent byte order)
    bayer_bytes = bayer_array.tobytes()
    
    # Compute hash
    sha256_hash = hashlib.sha256(bayer_bytes).hexdigest()
    
    return sha256_hash

if __name__ == "__main__":
    print("Capturing raw Bayer data...")
    raw_data = capture_raw_bayer()
    
    print(f"Captured: {raw_data.shape} array")
    print(f"Data type: {raw_data.dtype}")
    
    image_hash = hash_raw_bayer(raw_data)
    print(f"SHA-256: {image_hash}")
```

**Method 2: Direct V4L2 Access (Advanced)**
```python
import v4l2
import fcntl
import mmap

def capture_via_v4l2():
    """Direct access to raw Bayer via V4L2"""
    device = '/dev/video0'
    
    with open(device, 'rb+', buffering=0) as vd:
        # Configure format
        fmt = v4l2.v4l2_format()
        fmt.type = v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE
        fmt.fmt.pix.width = 4056
        fmt.fmt.pix.height = 3040
        fmt.fmt.pix.pixelformat = v4l2.V4L2_PIX_FMT_SRGGB10
        fcntl.ioctl(vd, v4l2.VIDIOC_S_FMT, fmt)
        
        # Request buffers, map memory, capture...
        # (Full implementation in final code)
```

### Parallel Processing Architecture

**Key Design:** Both processing paths run simultaneously

```python
import threading
import time

class ParallelCapture:
    """Manages parallel raw hashing and ISP processing"""
    
    def __init__(self):
        self.raw_hash = None
        self.processed_image = None
        self.tpm = TPMInterface()  # See Component 2
        
    def capture_and_process(self):
        """Capture with parallel processing"""
        start_time = time.time()
        
        # Capture raw Bayer
        raw_data = capture_raw_bayer()
        
        # Start parallel threads
        hash_thread = threading.Thread(
            target=self._hash_and_sign,
            args=(raw_data,)
        )
        isp_thread = threading.Thread(
            target=self._process_image,
            args=(raw_data,)
        )
        
        hash_thread.start()
        isp_thread.start()
        
        # Wait for both to complete
        hash_thread.join()
        isp_thread.join()
        
        elapsed = time.time() - start_time
        print(f"Total time: {elapsed:.3f}s")
        
        return self.raw_hash, self.processed_image
    
    def _hash_and_sign(self, raw_data):
        """Hash raw data and create authentication bundle"""
        # 1. Hash raw Bayer
        self.raw_hash = hash_raw_bayer(raw_data)
        
        # 2. Create camera token via TPM
        camera_token = self.tpm.create_token(self.raw_hash)
        
        # 3. Create authentication bundle
        bundle = {
            'image_hash': self.raw_hash,
            'camera_token': camera_token,
            'timestamp': int(time.time())
        }
        
        # 4. Queue for submission (non-blocking)
        queue_submission(bundle)
    
    def _process_image(self, raw_data):
        """Process image through ISP"""
        # Use libcamera ISP or manual processing
        self.processed_image = process_through_isp(raw_data)
        
        # Save to disk
        save_image(self.processed_image, 'output.jpg')
```

**Performance Target:**
- Raw capture: ~500ms
- SHA-256 hash: ~100ms (TPM)
- TPM signing: ~50ms
- ISP processing: ~600ms
- **Total user wait:** ~600ms (ISP only, hash runs in parallel)
- **Overhead:** 0ms (imperceptible to user)

---

## Component 2: Secure Element Integration

### Hardware: LetsTrust TPM Module

**Specifications:**
- Chip: Infineon Optiga SLB 9670 TPM 2.0
- Security: EAL4+ certified, FIPS 140-2
- Interface: SPI (GPIO pins 17-26)
- Features: SHA-256, HMAC, RSA-2048, ECC P-256, RNG
- Power: 3.3V, ~25mA active, 110µA idle

**Physical Installation:**
```
Raspberry Pi GPIO Header (looking at pins):
 1  2    Pin 1: 3.3V
 3  4    Pin 6: GND
 5  6    Pin 19: SPI0_MOSI
 7  8    Pin 21: SPI0_MISO
 9 10    Pin 23: SPI0_SCLK
11 12    Pin 24: SPI0_CE0
13 14
15 16
17 18  ← TPM plugs in here (pins 17-26)
19 20
21 22
23 24
25 26
```

**Connection:**
- Module spans GPIO pins 17-26 (2x5 block)
- Communicates via SPI0 interface
- Reset button on board for testing

### Software: TPM 2.0 Tools

**Installation:**
```bash
# Enable SPI interface
sudo raspi-config
# Interface Options → SPI → Enable

# Add device tree overlay
sudo nano /boot/config.txt
# Add line:
dtoverlay=tpm-slb9670

# Reboot
sudo reboot

# Install TPM tools
sudo apt-get update
sudo apt-get install tpm2-tools

# Verify TPM is detected
ls -l /dev/tpm0
sudo tpm2_getrandom 16 --hex
```

**Expected Output:**
```
crw-rw---- 1 tss tss 10, 224 Nov 10 10:00 /dev/tpm0
a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

### Implementation: TPM Interface

**Phase 1: Python TPM Interface**
```python
#!/usr/bin/env python3
"""
TPM interface for Birthmark Protocol
"""
import subprocess
import json
import hashlib
from typing import Dict, Tuple

class TPMInterface:
    """Interface to LetsTrust TPM module"""
    
    def __init__(self):
        self.tpm_device = '/dev/tpm0'
        self._verify_tpm()
        self._initialize_keys()
        
    def _verify_tpm(self):
        """Verify TPM is accessible"""
        try:
            result = subprocess.run(
                ['tpm2_getrandom', '16', '--hex'],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"TPM verified: {result.stdout.strip()}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"TPM not accessible: {e}")
    
    def _initialize_keys(self):
        """Initialize or load TPM keys"""
        # Check if primary key exists
        result = subprocess.run(
            ['tpm2_readpublic', '-c', '0x81010001'],
            capture_output=True
        )
        
        if result.returncode != 0:
            print("Creating primary key...")
            self._create_primary_key()
        else:
            print("Primary key exists")
    
    def _create_primary_key(self):
        """Create primary endorsement key"""
        subprocess.run([
            'tpm2_createprimary',
            '-C', 'e',  # Endorsement hierarchy
            '-g', 'sha256',
            '-G', 'ecc256',
            '-c', 'primary.ctx'
        ], check=True)
        
        # Persist to TPM
        subprocess.run([
            'tpm2_evictcontrol',
            '-C', 'o',  # Owner hierarchy
            '-c', 'primary.ctx',
            '0x81010001'
        ], check=True)
        
        print("Primary key created and persisted")
    
    def compute_hash(self, data: bytes) -> str:
        """
        Compute SHA-256 hash using TPM hardware
        
        Args:
            data: Raw bytes to hash
            
        Returns:
            Hex string of hash
        """
        # Write data to temp file
        with open('/tmp/tpm_input.bin', 'wb') as f:
            f.write(data)
        
        # Hash with TPM
        result = subprocess.run([
            'tpm2_hash',
            '-g', 'sha256',
            '-o', '/tmp/tpm_hash.bin',
            '/tmp/tpm_input.bin'
        ], capture_output=True, check=True)
        
        # Read hash
        with open('/tmp/tpm_hash.bin', 'rb') as f:
            hash_bytes = f.read()
        
        return hash_bytes.hex()
    
    def create_token(self, image_hash: str) -> Dict:
        """
        Create encrypted camera token
        
        Args:
            image_hash: SHA-256 hash of raw Bayer data
            
        Returns:
            Camera token dict with encrypted NUC hash
        """
        # 1. Load NUC hash from secure storage
        nuc_hash = self._load_nuc_hash()
        
        # 2. Get current key table and index
        table_id, key_index = self._get_current_key()
        
        # 3. Load encryption key
        encryption_key = self._load_key(table_id, key_index)
        
        # 4. Encrypt NUC hash with AES-GCM
        ciphertext, auth_tag, nonce = self._encrypt_aes_gcm(
            nuc_hash,
            encryption_key
        )
        
        # 5. Return camera token
        return {
            'ciphertext': ciphertext.hex(),
            'auth_tag': auth_tag.hex(),
            'nonce': nonce.hex(),
            'table_id': table_id,
            'key_index': key_index
        }
    
    def _load_nuc_hash(self) -> bytes:
        """Load camera's NUC hash from secure storage"""
        # Phase 1: Read from file
        # Phase 2: Store in TPM NVRAM
        with open('/etc/birthmark/nuc_hash.bin', 'rb') as f:
            return f.read()
    
    def _get_current_key(self) -> Tuple[int, int]:
        """
        Determine current key table and index
        
        Returns:
            (table_id, key_index) tuple
        """
        # Phase 1: Simple rotation based on day
        import datetime
        now = datetime.datetime.now()
        
        # Change key every 6 hours
        hours_since_epoch = int(now.timestamp() / 3600)
        table_id = (hours_since_epoch // 1000) % 250
        key_index = hours_since_epoch % 1000
        
        return table_id, key_index
    
    def _load_key(self, table_id: int, key_index: int) -> bytes:
        """
        Load encryption key from key table
        
        Args:
            table_id: Which key table (0-249)
            key_index: Which key in table (0-999)
            
        Returns:
            32-byte AES-256 key
        """
        # Phase 1: Load from local file
        # Phase 2: Load from manufacturer's HSM
        key_file = f'/etc/birthmark/keys/table_{table_id:03d}.bin'
        
        with open(key_file, 'rb') as f:
            # Each key is 32 bytes
            f.seek(key_index * 32)
            return f.read(32)
    
    def _encrypt_aes_gcm(self, data: bytes, key: bytes) -> Tuple[bytes, bytes, bytes]:
        """
        Encrypt data with AES-256-GCM
        
        Args:
            data: Plaintext to encrypt
            key: 32-byte AES key
            
        Returns:
            (ciphertext, auth_tag, nonce) tuple
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import os
        
        # Generate random nonce
        nonce = os.urandom(12)
        
        # Encrypt
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        
        # Split ciphertext and auth tag
        # AES-GCM appends 16-byte auth tag
        auth_tag = ciphertext[-16:]
        ciphertext = ciphertext[:-16]
        
        return ciphertext, auth_tag, nonce
    
    def sign_bundle(self, bundle: Dict) -> str:
        """
        Sign complete authentication bundle
        
        Args:
            bundle: Complete bundle dict
            
        Returns:
            Hex signature string
        """
        # Serialize bundle to JSON
        bundle_json = json.dumps(bundle, sort_keys=True)
        bundle_bytes = bundle_json.encode('utf-8')
        
        # Write to temp file
        with open('/tmp/bundle.json', 'wb') as f:
            f.write(bundle_bytes)
        
        # Sign with TPM
        subprocess.run([
            'tpm2_sign',
            '-c', '0x81010001',  # Primary key
            '-g', 'sha256',
            '-f', 'plain',
            '-o', '/tmp/bundle.sig',
            '/tmp/bundle.json'
        ], check=True)
        
        # Read signature
        with open('/tmp/bundle.sig', 'rb') as f:
            signature = f.read()
        
        return signature.hex()
```

**Key Generation Script:**
```python
#!/usr/bin/env python3
"""
Generate manufacturer key tables
"""
import os
import secrets

def generate_key_tables(output_dir: str):
    """Generate 250 key tables with 1000 keys each"""
    os.makedirs(output_dir, exist_ok=True)
    
    for table_id in range(250):
        table_file = f'{output_dir}/table_{table_id:03d}.bin'
        
        with open(table_file, 'wb') as f:
            for key_index in range(1000):
                # Generate random 32-byte AES key
                key = secrets.token_bytes(32)
                f.write(key)
        
        print(f"Generated table {table_id:03d}")
    
    print(f"\nTotal keys: {250 * 1000:,}")
    print(f"Total size: {250 * 1000 * 32 / 1024 / 1024:.1f} MB")

if __name__ == "__main__":
    generate_key_tables('/etc/birthmark/keys')
```

---

## Component 3: Network Communication

### Aggregation Server API Client

**Purpose:** Submit authentication bundles to aggregation server

```python
#!/usr/bin/env python3
"""
Aggregation server API client
"""
import requests
import json
import queue
import threading
import time
from typing import Dict

class AggregationClient:
    """Client for submitting to aggregation server"""
    
    def __init__(self, server_url: str = "https://api.birthmarkstandard.org"):
        self.server_url = server_url
        self.submission_queue = queue.Queue()
        self.worker_thread = threading.Thread(
            target=self._submission_worker,
            daemon=True
        )
        self.worker_thread.start()
    
    def submit_async(self, bundle: Dict):
        """Queue bundle for async submission"""
        self.submission_queue.put(bundle)
    
    def submit_sync(self, bundle: Dict) -> Dict:
        """Submit bundle synchronously"""
        endpoint = f"{self.server_url}/api/v1/submit"
        
        try:
            response = requests.post(
                endpoint,
                json=bundle,
                headers={
                    'Content-Type': 'application/json',
                    'X-API-Version': '1.0'
                },
                timeout=5
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Submission failed: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _submission_worker(self):
        """Background worker for async submissions"""
        while True:
            try:
                bundle = self.submission_queue.get(timeout=1)
                
                result = self.submit_sync(bundle)
                
                if result.get('status') == 'accepted':
                    print(f"Submitted: {result['submission_id']}")
                else:
                    print(f"Failed: {result.get('message')}")
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Worker error: {e}")

# Global client instance
aggregation_client = AggregationClient()

def queue_submission(bundle: Dict):
    """Queue authentication bundle for submission"""
    aggregation_client.submit_async(bundle)
```

### GPS Integration (Optional)

**Hardware:** Neo-6M GPS Module (~$15)

**Wiring:**
```
GPS Module  →  Raspberry Pi
VCC         →  Pin 1 (3.3V)
GND         →  Pin 6 (GND)
TX          →  Pin 10 (GPIO 15, RXD)
RX          →  Pin 8 (GPIO 14, TXD)
```

**Software:**
```python
import serial
import pynmea2

def read_gps_position() -> tuple:
    """Read current GPS position"""
    ser = serial.Serial('/dev/ttyS0', 9600, timeout=1)
    
    while True:
        line = ser.readline().decode('ascii', errors='replace')
        
        if line.startswith('$GPGGA'):
            msg = pynmea2.parse(line)
            if msg.latitude and msg.longitude:
                return (msg.latitude, msg.longitude)
    
    ser.close()

def hash_gps_position() -> str:
    """Get hashed GPS coordinates"""
    lat, lon = read_gps_position()
    
    # Truncate to ~10m precision
    lat_trunc = round(lat, 4)
    lon_trunc = round(lon, 4)
    
    gps_string = f"{lat_trunc},{lon_trunc}"
    gps_hash = hashlib.sha256(gps_string.encode()).hexdigest()
    
    return gps_hash
```

---

## Component 4: Complete Capture System

### Main Application

```python
#!/usr/bin/env python3
"""
Birthmark Camera - Main Application
Raspberry Pi 4 + HQ Camera + LetsTrust TPM
"""
import sys
import time
import argparse
from pathlib import Path

# Import our modules
from raw_capture import ParallelCapture
from tpm_interface import TPMInterface
from aggregation_client import queue_submission

class BirthmarkCamera:
    """Complete Birthmark camera system"""
    
    def __init__(self, output_dir: str = "./captures"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.parallel_capture = ParallelCapture()
        self.capture_count = 0
        
        print("Birthmark Camera initialized")
    
    def capture_photo(self) -> Dict:
        """
        Capture authenticated photo
        
        Returns:
            Result dict with paths and hashes
        """
        print(f"\n=== Capture #{self.capture_count + 1} ===")
        
        start_time = time.time()
        
        # 1. Parallel capture and process
        image_hash, processed_image = self.parallel_capture.capture_and_process()
        
        # 2. Save processed image
        timestamp = int(time.time())
        filename = f"IMG_{timestamp}.jpg"
        filepath = self.output_dir / filename
        
        with open(filepath, 'wb') as f:
            f.write(processed_image)
        
        # 3. Results
        elapsed = time.time() - start_time
        
        result = {
            'capture_number': self.capture_count + 1,
            'image_hash': image_hash,
            'filename': str(filepath),
            'timestamp': timestamp,
            'elapsed_time': elapsed,
            'status': 'success'
        }
        
        self.capture_count += 1
        
        print(f"Saved: {filename}")
        print(f"Hash: {image_hash[:16]}...")
        print(f"Time: {elapsed:.3f}s")
        print(f"Authentication queued for submission")
        
        return result
    
    def timelapse(self, interval: int, count: int):
        """
        Capture timelapse sequence
        
        Args:
            interval: Seconds between captures
            count: Number of captures (0 = infinite)
        """
        print(f"\nStarting timelapse:")
        print(f"  Interval: {interval}s")
        print(f"  Count: {count if count > 0 else 'infinite'}")
        
        capture_num = 0
        
        try:
            while True:
                if count > 0 and capture_num >= count:
                    break
                
                self.capture_photo()
                capture_num += 1
                
                if count > 0 and capture_num < count:
                    print(f"\nWaiting {interval}s...")
                    time.sleep(interval)
                elif count == 0:
                    time.sleep(interval)
                    
        except KeyboardInterrupt:
            print(f"\n\nTimelapse stopped")
            print(f"Captured {capture_num} photos")

def main():
    parser = argparse.ArgumentParser(
        description='Birthmark Protocol Camera'
    )
    parser.add_argument(
        '--output',
        default='./captures',
        help='Output directory for captures'
    )
    parser.add_argument(
        '--timelapse',
        type=int,
        metavar='INTERVAL',
        help='Timelapse mode with interval in seconds'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=0,
        metavar='N',
        help='Number of captures (0 = infinite)'
    )
    
    args = parser.parse_args()
    
    # Initialize camera
    camera = BirthmarkCamera(output_dir=args.output)
    
    if args.timelapse:
        # Timelapse mode
        camera.timelapse(interval=args.timelapse, count=args.count)
    else:
        # Single capture
        camera.capture_photo()

if __name__ == "__main__":
    main()
```

### Usage Examples

```bash
# Single capture
python3 birthmark_camera.py

# Timelapse: 1 photo every 5 seconds, 100 captures
python3 birthmark_camera.py --timelapse 5 --count 100

# Continuous timelapse
python3 birthmark_camera.py --timelapse 10

# Custom output directory
python3 birthmark_camera.py --output /media/usb/captures
```

---

## Testing & Validation

### Unit Tests

```python
#!/usr/bin/env python3
"""
Unit tests for Birthmark camera components
"""
import unittest
import hashlib
import numpy as np
from raw_capture import hash_raw_bayer
from tpm_interface import TPMInterface

class TestRawCapture(unittest.TestCase):
    """Test raw Bayer capture and hashing"""
    
    def test_hash_deterministic(self):
        """Same data should produce same hash"""
        # Create fake Bayer data
        data = np.random.randint(0, 1024, (3040, 4056), dtype=np.uint16)
        
        hash1 = hash_raw_bayer(data)
        hash2 = hash_raw_bayer(data)
        
        self.assertEqual(hash1, hash2)
    
    def test_hash_different(self):
        """Different data should produce different hash"""
        data1 = np.random.randint(0, 1024, (3040, 4056), dtype=np.uint16)
        data2 = np.random.randint(0, 1024, (3040, 4056), dtype=np.uint16)
        
        hash1 = hash_raw_bayer(data1)
        hash2 = hash_raw_bayer(data2)
        
        self.assertNotEqual(hash1, hash2)
    
    def test_hash_format(self):
        """Hash should be valid SHA-256"""
        data = np.random.randint(0, 1024, (100, 100), dtype=np.uint16)
        hash_value = hash_raw_bayer(data)
        
        # Should be 64 hex characters
        self.assertEqual(len(hash_value), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in hash_value))

class TestTPMInterface(unittest.TestCase):
    """Test TPM interface"""
    
    def setUp(self):
        """Initialize TPM for tests"""
        try:
            self.tpm = TPMInterface()
        except RuntimeError:
            self.skipTest("TPM not available")
    
    def test_tpm_available(self):
        """TPM should be accessible"""
        # If we got here, TPM is working
        self.assertTrue(True)
    
    def test_hash_computation(self):
        """TPM should compute correct hash"""
        data = b"Test data for hashing"
        
        # Compute with TPM
        tpm_hash = self.tpm.compute_hash(data)
        
        # Compute with hashlib
        expected_hash = hashlib.sha256(data).hexdigest()
        
        self.assertEqual(tpm_hash, expected_hash)
    
    def test_token_creation(self):
        """Token should have required fields"""
        image_hash = "a" * 64
        token = self.tpm.create_token(image_hash)
        
        self.assertIn('ciphertext', token)
        self.assertIn('auth_tag', token)
        self.assertIn('nonce', token)
        self.assertIn('table_id', token)
        self.assertIn('key_index', token)
        
        # Validate field formats
        self.assertEqual(len(token['auth_tag']), 32)
        self.assertEqual(len(token['nonce']), 24)
        self.assertIn(token['table_id'], range(250))
        self.assertIn(token['key_index'], range(1000))

if __name__ == '__main__':
    unittest.main()
```

### Integration Tests

```bash
#!/bin/bash
# Integration test script

echo "=== Birthmark Camera Integration Test ==="
echo

# 1. Check hardware
echo "1. Checking hardware..."
if [ ! -e /dev/video0 ]; then
    echo "ERROR: Camera not detected"
    exit 1
fi
if [ ! -e /dev/tpm0 ]; then
    echo "ERROR: TPM not detected"
    exit 1
fi
echo "✓ Hardware detected"
echo

# 2. Test TPM
echo "2. Testing TPM..."
tpm2_getrandom 16 --hex > /dev/null
if [ $? -eq 0 ]; then
    echo "✓ TPM working"
else
    echo "ERROR: TPM test failed"
    exit 1
fi
echo

# 3. Test raw capture
echo "3. Testing raw capture..."
python3 -c "from raw_capture import capture_raw_bayer; capture_raw_bayer()" > /dev/null
if [ $? -eq 0 ]; then
    echo "✓ Raw capture working"
else
    echo "ERROR: Raw capture failed"
    exit 1
fi
echo

# 4. Test full capture
echo "4. Testing full capture..."
python3 birthmark_camera.py --output /tmp/test_captures
if [ $? -eq 0 ]; then
    echo "✓ Full capture working"
else
    echo "ERROR: Full capture failed"
    exit 1
fi
echo

# 5. Verify output
echo "5. Verifying output..."
if [ -f /tmp/test_captures/IMG_*.jpg ]; then
    echo "✓ Image file created"
else
    echo "ERROR: No image file created"
    exit 1
fi
echo

echo "=== All tests passed ==="
```

### Performance Benchmarking

```python
#!/usr/bin/env python3
"""
Performance benchmark for Birthmark camera
"""
import time
import statistics
from raw_capture import ParallelCapture

def benchmark_capture(iterations: int = 10):
    """Benchmark capture performance"""
    camera = ParallelCapture()
    
    timings = {
        'total': [],
        'hash': [],
        'isp': []
    }
    
    print(f"Running {iterations} capture cycles...")
    
    for i in range(iterations):
        start = time.time()
        
        # Capture with timing
        camera.capture_and_process()
        
        total_time = time.time() - start
        timings['total'].append(total_time)
        
        print(f"  Capture {i+1}: {total_time:.3f}s")
    
    # Statistics
    print(f"\nResults ({iterations} iterations):")
    print(f"  Mean: {statistics.mean(timings['total']):.3f}s")
    print(f"  Median: {statistics.median(timings['total']):.3f}s")
    print(f"  Std Dev: {statistics.stdev(timings['total']):.3f}s")
    print(f"  Min: {min(timings['total']):.3f}s")
    print(f"  Max: {max(timings['total']):.3f}s")

if __name__ == "__main__":
    benchmark_capture(iterations=10)
```

---

## Phase 1 Implementation Timeline

### Week 1: Hardware Setup & Basic Capture
**Goal:** Camera capturing raw Bayer data

**Tasks:**
1. Order and receive all hardware components
2. Assemble Raspberry Pi + HQ Camera + TPM
3. Install Raspberry Pi OS (64-bit)
4. Configure camera interface (libcamera)
5. Install TPM tools and verify functionality
6. Test raw Bayer capture with raspiraw
7. Implement `raw_capture.py` module
8. Write unit tests for capture

**Deliverables:**
- [ ] Assembled hardware
- [ ] Raw Bayer data captured successfully
- [ ] TPM responding to commands
- [ ] Basic Python modules working

### Week 2: TPM Integration & Encryption
**Goal:** TPM creating signed authentication tokens

**Tasks:**
1. Implement `tpm_interface.py` module
2. Generate manufacturer key tables (250 × 1000 keys)
3. Create mock NUC hash for testing
4. Test SHA-256 hashing via TPM
5. Implement AES-GCM encryption
6. Test camera token creation
7. Write unit tests for TPM interface
8. Document key rotation mechanism

**Deliverables:**
- [ ] TPM hashing working
- [ ] Camera tokens being created correctly
- [ ] Key table generation script
- [ ] TPM interface tests passing

### Week 3: Parallel Processing & Integration
**Goal:** Complete capture system with parallel processing

**Tasks:**
1. Implement parallel capture architecture
2. Test simultaneous hash + ISP processing
3. Benchmark performance (target: <650ms total)
4. Implement `aggregation_client.py`
5. Test API communication with aggregation server
6. Create main `birthmark_camera.py` application
7. Add GPS integration (optional)
8. Write integration tests

**Deliverables:**
- [ ] Parallel processing working
- [ ] Performance targets met
- [ ] API communication functional
- [ ] Complete application working

### Week 4: Testing & Documentation
**Goal:** Production-ready prototype

**Tasks:**
1. Run comprehensive test suite
2. Performance benchmarking
3. Create user documentation
4. Create demo video
5. Photography club testing session
6. Bug fixes and polish
7. Prepare for manufacturer demos

**Deliverables:**
- [ ] All tests passing
- [ ] User documentation complete
- [ ] Demo video recorded
- [ ] Photography club feedback gathered
- [ ] Bug-free prototype

---

## Deployment & Usage

### Initial Setup

```bash
# 1. Flash Raspberry Pi OS (64-bit)
# Use Raspberry Pi Imager: https://www.raspberrypi.com/software/

# 2. Boot and configure
sudo raspi-config
# - Enable SSH
# - Enable SPI
# - Enable Camera
# - Set hostname to "birthmark-camera"

# 3. Update system
sudo apt-get update
sudo apt-get upgrade -y

# 4. Install dependencies
sudo apt-get install -y \
    python3-pip \
    python3-picamera2 \
    python3-numpy \
    tpm2-tools \
    git

# 5. Install Python packages
pip3 install \
    cryptography \
    requests \
    pynmea2 \
    pyserial

# 6. Clone Birthmark repository
git clone https://github.com/Birthmark-Protocol/camera-prototype
cd camera-prototype

# 7. Configure TPM
sudo nano /boot/config.txt
# Add: dtoverlay=tpm-slb9670
sudo reboot

# 8. Verify installation
./scripts/verify_setup.sh

# 9. Generate keys (one-time)
sudo python3 scripts/generate_keys.py

# 10. Ready to use!
python3 birthmark_camera.py
```

### Daily Usage

```bash
# Single photo
python3 birthmark_camera.py

# Timelapse (1 photo every 30 seconds)
python3 birthmark_camera.py --timelapse 30

# High-frequency burst (1 photo/second for 60 seconds)
python3 birthmark_camera.py --timelapse 1 --count 60
```

### Photography Club Testing

**Test Scenarios:**
1. **Single Capture Test** (5 min)
   - Take 5 photos of different subjects
   - Verify images saved correctly
   - Check authentication bundles submitted
   
2. **Timelapse Test** (30 min)
   - Set up 10-minute timelapse (1 photo/30s = 20 photos)
   - Let system run unattended
   - Verify all photos authenticated
   
3. **Verification Test** (10 min)
   - Query aggregation server for image hashes
   - Verify Merkle proofs validate
   - Demonstrate tamper detection

**Feedback Survey:**
```
1. Was the capture process easy to use? (1-5)
2. Did you notice any delay compared to normal cameras? (Yes/No)
3. Would you use this for competition submissions? (Yes/No)
4. What concerns do you have about the technology?
5. What improvements would you suggest?
```

---

## Success Criteria

### Technical Criteria

**Hardware:**
- [ ] Camera captures 12MP raw Bayer images
- [ ] TPM computes SHA-256 hashes correctly
- [ ] Secure element encrypts tokens properly
- [ ] All components communicate reliably

**Performance:**
- [ ] Total capture time <650ms
- [ ] Parallel overhead <5% CPU
- [ ] Zero user-perceivable latency
- [ ] Can capture 1 photo/second sustained
- [ ] Handles 100+ captures without failure

**Integration:**
- [ ] Authentication bundles submit successfully
- [ ] Aggregation server accepts all submissions
- [ ] Verification queries return correct proofs
- [ ] End-to-end workflow completes in <30s

### User Validation

**Photography Club:**
- [ ] 80%+ find it "easy to use" (4-5 rating)
- [ ] 90%+ notice no delay vs normal cameras
- [ ] 70%+ would use for competition submissions
- [ ] No critical usability issues reported

**Demonstration:**
- [ ] 5-minute demo video shows complete workflow
- [ ] Non-technical viewers understand concept
- [ ] Addresses manufacturer concerns (cost, complexity)
- [ ] Demonstrates clear advantage over C2PA

### Manufacturer Demo

**Proof Points:**
- [ ] Raw sensor hashing is feasible
- [ ] Parallel processing eliminates latency
- [ ] Secure element integration is practical
- [ ] Architecture scales to production
- [ ] Cost impact is reasonable (<$5/camera)

---

## Cost Analysis

### Per-Unit Prototype Cost

| Component | Cost | Notes |
|-----------|------|-------|
| Raspberry Pi 4 | $55 | SBC equivalent |
| Camera Module | $50 | Sensor + interface |
| TPM/Secure Element | $25 | Production: $2-5 |
| Storage | $12 | Included in camera |
| Power Supply | $8 | Included in camera |
| Case/Mounting | $10 | Production: integrated |
| **Prototype Total** | **$160** | |
| **Production Estimate** | **$2-7** | Just secure element |

**Production Cost Breakdown:**
- Secure Element Chip: $2-5 (high volume)
- PCB Integration: ~$1
- Firmware Development: Amortized
- Testing/Certification: Amortized

**Cost Impact:** <1% of camera retail price

### Development Cost

| Phase | Hours | Rate | Cost |
|-------|-------|------|------|
| Hardware Assembly | 8 | $0 | $0 |
| Software Development | 80 | $150 | $12,000 |
| Testing & Validation | 40 | $150 | $6,000 |
| Photography Club | 16 | $150 | $2,400 |
| **Total** | **144** | | **$20,400** |

**Assumptions:**
- Hardware costs paid ($200)
- Sam's time valued at $150/hr (market rate)
- Photography club testing: 2 sessions × 8 hours

---

## Phase 2 Transition

**Ready for Phase 2 (Android App) when:**
- [ ] All Phase 1 hardware working reliably
- [ ] Photography club validates concept
- [ ] Performance targets met
- [ ] No critical bugs
- [ ] Manufacturer demo successful
- [ ] Clear path to production identified

**Phase 2 Changes:**
- Port to Android (Android Keystore)
- Use phone's existing camera ISP
- Integrate with Android Camera2/CameraX API
- Add live preview
- Improve user interface
- Test with 100+ photographers

**Lessons to Carry Forward:**
- Parallel processing architecture
- TPM integration patterns
- API communication protocols
- Authentication bundle format
- Testing methodologies

---

## Appendices

### A. GPIO Pinout Reference

```
Raspberry Pi 4 GPIO Header (40 pins)
====================================

 3.3V  (1)  (2)  5V
GPIO2 (3)  (4)  5V
GPIO3 (5)  (6)  GND
GPIO4 (7)  (8)  GPIO14 (UART TX)
  GND  (9) (10)  GPIO15 (UART RX)
...
     (17) (18)
SPI0_MOSI (19) (20) GND
SPI0_MISO (21) (22)
SPI0_SCLK (23) (24) SPI0_CE0
      GND (25) (26)

TPM Module plugs into pins 17-26
GPS Module uses pins 8 & 10 (UART)
```

### B. Troubleshooting Guide

**Camera Not Detected:**
```bash
# Check camera cable connection
vcgencmd get_camera

# Should show: supported=1 detected=1

# Enable camera interface
sudo raspi-config
# Interface Options → Camera → Enable
```

**TPM Not Responding:**
```bash
# Check device exists
ls -l /dev/tpm0

# Check SPI enabled
lsmod | grep spi

# Check device tree overlay
dtoverlay -l | grep tpm

# Reinstall TPM tools
sudo apt-get install --reinstall tpm2-tools
```

**Slow Performance:**
```bash
# Check CPU frequency
vcgencmd measure_clock arm

# Check temperature
vcgencmd measure_temp

# Check throttling
vcgencmd get_throttled

# Add cooling if overheating
```

### C. References

**Hardware Documentation:**
- Raspberry Pi 4: https://www.raspberrypi.com/products/raspberry-pi-4-model-b/
- HQ Camera: https://www.raspberrypi.com/products/raspberry-pi-high-quality-camera/
- LetsTrust TPM: https://pi3g.com/products/letstrust-tpm/
- SLB 9670 Datasheet: https://www.infineon.com/cms/en/product/security-smart-card-solutions/optiga-embedded-security-solutions/optiga-tpm/

**Software Documentation:**
- libcamera: https://libcamera.org/
- TPM2 Software Stack: https://tpm2-software.github.io/
- picamera2: https://github.com/raspberrypi/picamera2

**Standards:**
- TPM 2.0 Specification: https://trustedcomputinggroup.org/resource/tpm-library-specification/
- CSI-2 Specification: (MIPI Alliance members only)
- AES-GCM: NIST SP 800-38D

---

**Document Status:** Ready for Implementation  
**Owner:** Samuel C. Ryan, The Birthmark Standard Foundation  
**Hardware Lead:** Samuel C. Ryan  
**Next Review:** After Week 1 completion  
**Related Documents:** 
- Birthmark_Phase_1_Plan_Aggregation_Server.md
- Birthmark_Phase_1-2_Plan_SMA.md
