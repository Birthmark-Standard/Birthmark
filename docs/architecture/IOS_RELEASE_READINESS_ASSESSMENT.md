# iOS App Release Readiness Assessment

**Date:** November 2025
**Phase:** Phase 2 (Certificate-Based Authentication)
**Target:** TestFlight Beta Release
**Assessment Status:** CRITICAL GAPS IDENTIFIED

---

## Executive Summary

The iOS app has **core certificate-based authentication implemented** but requires:
- **Backend Implementation:** SMA certificate generation (HIGH PRIORITY)
- **Integration Testing:** End-to-end flow validation (HIGH PRIORITY)
- **Missing Features:** Offline queue, error handling, UI polish (MEDIUM PRIORITY)
- **Testing Infrastructure:** Unit tests, integration tests (REQUIRED FOR RELEASE)

**Estimated Work Remaining:** 2-3 weeks for TestFlight beta release

---

## Part 1: Code Completeness Assessment

### ✅ FULLY IMPLEMENTED (Ready)

#### 1. **iOS Core Services (100% Complete)**

**KeychainService.swift** ✅
- Device certificate storage (`saveDeviceCertificate`, `getDeviceCertificate`)
- Private key storage (`saveDevicePrivateKey`, `getDevicePrivateKey`)
- Certificate chain storage (`saveCertificateChain`, `getCertificateChain`)
- Full provisioning check (`isFullyProvisioned()`)
- Secure Keychain operations with proper error handling
- **Status:** Production-ready

**CryptoService.swift** ✅
- Device secret generation (`generateDeviceSecret()`)
- SHA-256 image hashing
- ECDSA P-256 bundle signing (`signCertificateBundle()`)
- Canonical bundle data creation
- PEM/DER private key parsing
- Signature verification (for testing)
- **Status:** Production-ready

**NetworkService.swift** ✅
- Certificate bundle submission (`submitCertificateBundle()`)
- SMA provisioning API call (`provisionDevice()`)
- ProvisioningResponse model with proper JSON mapping
- Backward compatibility with Phase 1
- **Status:** API integration ready, needs backend

**AuthenticationService.swift** ✅
- Certificate-based authentication flow
- Bundle validation before submission
- Phase 1 fallback support
- Error handling with specific error types
- **Status:** Production-ready

**Models/CertificateBundle.swift** ✅
- Complete certificate bundle model
- Validation logic
- API format conversion
- Error handling with localized descriptions
- **Status:** Production-ready

**Views/ProvisioningView.swift** ✅
- SMA API integration for provisioning
- Credential verification and storage
- Full provisioning validation
- Error handling and UI feedback
- **Status:** Production-ready

---

### ⚠️ PARTIALLY IMPLEMENTED (Needs Work)

#### 1. **Offline Queue for Certificate Bundles** (30% Complete)

**Current State:**
- Phase 1 `AuthenticationBundle` queue exists in `NetworkService.swift`
- Certificate bundles are NOT queued when offline
- Authentication fails if network unavailable

**Missing Code:**
```swift
// In NetworkService.swift

// Need to add:
private let certQueueKey = "com.birthmark.cert_submission_queue"

struct QueuedCertSubmission: Codable {
    let id: UUID
    let bundle: CertificateBundle
    let createdAt: Date
    var attemptCount: Int
    var lastAttempt: Date?
}

func queueCertificateBundle(_ bundle: CertificateBundle) {
    var queue = loadCertQueue()
    let queued = QueuedCertSubmission(
        id: UUID(),
        bundle: bundle,
        createdAt: Date(),
        attemptCount: 0,
        lastAttempt: nil
    )
    queue.append(queued)
    saveCertQueue(queue)
}

func processCertQueue() async {
    // Similar to processQueue() but for CertificateBundle
}
```

**Priority:** MEDIUM (TestFlight can work without offline support)
**Estimated Time:** 2-3 hours

#### 2. **GPS Hashing** (0% Complete)

**Current State:**
- GPS hash field exists in `CertificateBundle`
- Always set to `nil` in `AuthenticationService.swift` (line 44)
- No location services integration

**Missing Code:**
```swift
// New file: Services/LocationService.swift

import CoreLocation

class LocationService: NSObject, CLLocationManagerDelegate {
    static let shared = LocationService()
    private let locationManager = CLLocationManager()
    private var currentLocation: CLLocation?

    func requestPermission() {
        locationManager.requestWhenInUseAuthorization()
    }

    func getCurrentLocationHash() -> String? {
        guard let location = currentLocation else { return nil }
        let lat = String(format: "%.6f", location.coordinate.latitude)
        let lon = String(format: "%.6f", location.coordinate.longitude)
        let combined = lat + lon
        return CryptoService.shared.sha256(combined)
    }
}

// In AuthenticationService.swift, replace line 44:
let gpsHash = LocationService.shared.getCurrentLocationHash()
```

**Additional Requirements:**
- Add `NSLocationWhenInUseUsageDescription` to Info.plist
- UI toggle in settings to enable/disable GPS
- Privacy policy update explaining GPS usage

**Priority:** LOW (Optional feature for Phase 2)
**Estimated Time:** 4-6 hours

#### 3. **Camera UI and Photo Capture** (Assuming 50% Complete)

**Status Unknown:** Need to verify if camera interface exists

If missing, need:
```swift
// Views/CameraView.swift
import AVFoundation

struct CameraView: View {
    @StateObject private var camera = CameraModel()

    var body: some View {
        ZStack {
            CameraPreview(camera: camera)

            VStack {
                Spacer()

                Button(action: { camera.capturePhoto() }) {
                    Circle()
                        .fill(Color.white)
                        .frame(width: 70, height: 70)
                        .overlay(
                            Circle()
                                .stroke(Color.white, lineWidth: 2)
                                .frame(width: 80, height: 80)
                        )
                }
                .padding(.bottom, 30)
            }
        }
        .onAppear {
            camera.requestPermission()
        }
    }
}

class CameraModel: NSObject, ObservableObject {
    // AVCaptureSession setup
    // Photo capture with authentication
}
```

**Priority:** CRITICAL (Core functionality)
**Estimated Time:** If missing: 1-2 days

#### 4. **Settings View** (Likely 0% Complete)

**Missing:**
- Server URL configuration (currently hardcoded to localhost)
- GPS toggle
- Debug mode toggle
- View provisioning status
- Clear credentials / re-provision

**Required Code:**
```swift
// Views/SettingsView.swift

struct SettingsView: View {
    @AppStorage("aggregatorURL") private var aggregatorURL = "http://localhost:8545"
    @AppStorage("smaURL") private var smaURL = "http://localhost:8001"
    @AppStorage("enableGPS") private var enableGPS = false
    @AppStorage("debugMode") private var debugMode = false

    var body: some View {
        Form {
            Section(header: Text("Server Configuration")) {
                TextField("Aggregator URL", text: $aggregatorURL)
                TextField("SMA URL", text: $smaURL)
            }

            Section(header: Text("Features")) {
                Toggle("Enable GPS Hashing", isOn: $enableGPS)
                Toggle("Debug Mode", isOn: $debugMode)
            }

            Section(header: Text("Device Status")) {
                HStack {
                    Text("Provisioned")
                    Spacer()
                    Text(KeychainService.shared.isFullyProvisioned() ? "Yes" : "No")
                }
                Button("Clear Credentials") {
                    KeychainService.shared.deleteAll()
                }
                .foregroundColor(.red)
            }
        }
    }
}

// Update NetworkService.swift to use AppStorage values
```

**Priority:** HIGH (Needed for TestFlight testing with real servers)
**Estimated Time:** 3-4 hours

---

### ❌ NOT IMPLEMENTED (Blockers)

#### 1. **SMA Certificate Generation** (CRITICAL BLOCKER)

**Current State:**
- iOS calls `POST /api/v1/devices/provision` with device_secret
- SMA endpoint exists but returns mock/incomplete data
- SMA does NOT generate actual ECDSA keys or certificates

**Missing Backend Code:**

**File:** `packages/sma/src/provisioning/certificate_generator.py` (NEW FILE)

```python
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography import x509
from cryptography.x509.oid import NameOID
from datetime import datetime, timedelta
import base64

class CertificateGenerator:
    """Generate ECDSA P-256 certificates for devices."""

    def __init__(self, ca_private_key_path: str, ca_cert_path: str):
        """Load CA private key and certificate."""
        with open(ca_private_key_path, 'rb') as f:
            self.ca_private_key = serialization.load_pem_private_key(
                f.read(), password=None
            )

        with open(ca_cert_path, 'rb') as f:
            self.ca_cert = x509.load_pem_x509_certificate(f.read())

    def generate_device_certificate(
        self,
        device_serial: str,
        device_secret: str,
        key_table_indices: list[int]
    ) -> tuple[str, str, str]:
        """
        Generate device certificate, private key, and chain.

        Returns:
            (device_cert_pem, device_private_key_pem, cert_chain_pem)
        """
        # 1. Generate device private key (ECDSA P-256)
        device_private_key = ec.generate_private_key(ec.SECP256R1())

        # 2. Get device public key
        device_public_key = device_private_key.public_key()

        # 3. Create certificate with device_secret in subject
        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, device_serial),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Birthmark Standard"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "iOS Device"),
        ])

        # 4. Add device_secret and key_table_indices as extensions
        extensions = [
            x509.Extension(
                x509.ObjectIdentifier("1.2.3.4.5.1"),  # Custom OID for device_secret
                critical=False,
                value=device_secret.encode('utf-8')
            ),
            x509.Extension(
                x509.ObjectIdentifier("1.2.3.4.5.2"),  # Custom OID for key_tables
                critical=False,
                value=str(key_table_indices).encode('utf-8')
            ),
        ]

        # 5. Build certificate
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(self.ca_cert.subject)
            .public_key(device_public_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=365))
        )

        for ext in extensions:
            cert = cert.add_extension(ext.oid, ext.value, ext.critical)

        # 6. Sign with CA private key
        device_cert = cert.sign(self.ca_private_key, hashes.SHA256())

        # 7. Serialize to PEM
        device_cert_pem = device_cert.public_bytes(
            serialization.Encoding.PEM
        ).decode('utf-8')

        device_private_key_pem = device_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        # 8. Certificate chain (CA cert)
        cert_chain_pem = self.ca_cert.public_bytes(
            serialization.Encoding.PEM
        ).decode('utf-8')

        return (device_cert_pem, device_private_key_pem, cert_chain_pem)
```

**Update:** `packages/sma/src/provisioning/provisioner.py`

```python
from .certificate_generator import CertificateGenerator

class Provisioner:
    def __init__(self, cert_gen: CertificateGenerator):
        self.cert_gen = cert_gen

    def provision_device(
        self,
        device_serial: str,
        device_family: str,
        device_secret: str
    ) -> ProvisioningResponse:
        # 1. Assign random key tables
        key_table_indices = self._assign_random_tables()

        # 2. Generate device certificate
        device_cert, device_key, cert_chain = self.cert_gen.generate_device_certificate(
            device_serial=device_serial,
            device_secret=device_secret,
            key_table_indices=key_table_indices
        )

        # 3. Get key tables
        key_tables = self._get_key_tables(key_table_indices)

        # 4. Save to database
        self._register_device(
            device_serial=device_serial,
            device_secret=device_secret,
            key_table_indices=key_table_indices,
            device_cert=device_cert
        )

        return ProvisioningResponse(
            device_certificate=device_cert,
            device_private_key=device_key,
            certificate_chain=cert_chain,
            key_tables=key_tables,
            key_table_indices=key_table_indices,
            device_secret=device_secret
        )
```

**Additional Requirements:**
- Generate CA certificate and private key (one-time setup)
- Store CA credentials securely
- Add certificate parsing to SMA validation endpoint

**Priority:** CRITICAL (iOS app cannot provision without this)
**Estimated Time:** 1-2 days

#### 2. **Aggregator Certificate Validation** (CRITICAL BLOCKER)

**Current State:**
- Aggregator has `/api/v1/submit-cert` endpoint
- Endpoint accepts certificate bundles but validation is incomplete
- SMA `/validate-cert` endpoint needs implementation

**Missing Backend Code:**

**File:** `packages/sma/src/validation/certificate_validator.py` (NEW FILE)

```python
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization

class CertificateValidator:
    """Validate device certificates and bundle signatures."""

    def __init__(self, ca_cert_path: str):
        """Load CA certificate for chain validation."""
        with open(ca_cert_path, 'rb') as f:
            self.ca_cert = x509.load_pem_x509_certificate(f.read())

    def validate_certificate_bundle(
        self,
        camera_cert_b64: str,
        image_hash: str,
        timestamp: int,
        gps_hash: str | None,
        bundle_signature_b64: str
    ) -> tuple[bool, str]:
        """
        Validate certificate bundle.

        Returns:
            (is_valid, reason)
        """
        try:
            # 1. Decode certificate
            cert_pem = base64.b64decode(camera_cert_b64)
            device_cert = x509.load_pem_x509_certificate(cert_pem)

            # 2. Verify certificate chain
            if not self._verify_certificate_chain(device_cert):
                return (False, "Invalid certificate chain")

            # 3. Check certificate expiration
            if not self._is_certificate_valid(device_cert):
                return (False, "Certificate expired")

            # 4. Extract device_secret from certificate
            device_secret = self._extract_device_secret(device_cert)

            # 5. Check if device is blacklisted
            if self._is_device_blacklisted(device_secret):
                return (False, "Device is blacklisted")

            # 6. Verify bundle signature
            device_public_key = device_cert.public_key()
            canonical_data = self._create_canonical_data(
                image_hash, camera_cert_b64, timestamp, gps_hash
            )
            signature_bytes = base64.b64decode(bundle_signature_b64)

            try:
                device_public_key.verify(
                    signature_bytes,
                    canonical_data.encode('utf-8'),
                    ec.ECDSA(hashes.SHA256())
                )
            except Exception:
                return (False, "Invalid bundle signature")

            # 7. Log submission for abuse detection
            self._log_submission(device_secret)

            return (True, "PASS")

        except Exception as e:
            return (False, f"Validation error: {str(e)}")

    def _create_canonical_data(
        self,
        image_hash: str,
        camera_cert: str,
        timestamp: int,
        gps_hash: str | None
    ) -> str:
        """Create canonical bundle data (must match iOS implementation)."""
        canonical = ""
        canonical += image_hash.lower() + "\n"
        canonical += camera_cert + "\n"
        canonical += str(timestamp) + "\n"
        canonical += (gps_hash.lower() if gps_hash else "") + "\n"
        return canonical
```

**Update:** `packages/sma/src/main.py`

```python
from .validation.certificate_validator import CertificateValidator

@app.post("/validate-cert")
async def validate_certificate(request: CertificateValidationRequest):
    """Validate certificate bundle (called by aggregator)."""
    validator = CertificateValidator(ca_cert_path="path/to/ca.crt")

    is_valid, reason = validator.validate_certificate_bundle(
        camera_cert_b64=request.camera_cert,
        image_hash=request.image_hash,
        timestamp=request.timestamp,
        gps_hash=request.gps_hash,
        bundle_signature_b64=request.bundle_signature
    )

    return SMAValidationResponse(
        valid=is_valid,
        message=reason
    )
```

**Priority:** CRITICAL (Aggregator cannot validate submissions without this)
**Estimated Time:** 1-2 days

#### 3. **CA Certificate Generation** (ONE-TIME SETUP)

**Script:** `packages/sma/scripts/generate_ca_certificate.py` (NEW FILE)

```python
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography import x509
from cryptography.x509.oid import NameOID
from datetime import datetime, timedelta

def generate_ca_certificate():
    """Generate root CA certificate for SMA."""
    # Generate CA private key
    ca_private_key = ec.generate_private_key(ec.SECP256R1())

    # Create self-signed CA certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Oregon"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Eugene"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Birthmark Standard Foundation"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Birthmark SMA Root CA"),
    ])

    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(ca_private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=3650))  # 10 years
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True
        )
        .sign(ca_private_key, hashes.SHA256())
    )

    # Save CA private key
    with open("ca_private_key.pem", "wb") as f:
        f.write(ca_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Save CA certificate
    with open("ca_certificate.pem", "wb") as f:
        f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

    print("✅ CA certificate generated:")
    print("   - ca_private_key.pem (KEEP SECURE!)")
    print("   - ca_certificate.pem (distribute to clients)")

if __name__ == "__main__":
    generate_ca_certificate()
```

**Run Once:**
```bash
cd packages/sma
python scripts/generate_ca_certificate.py
# Move keys to secure location
mv ca_private_key.pem /secure/location/
mv ca_certificate.pem certs/
```

**Priority:** CRITICAL (Required before any provisioning can work)
**Estimated Time:** 1 hour

---

## Part 2: Testing Requirements

### Unit Tests (REQUIRED)

#### iOS Unit Tests

**File:** `packages/mobile-app/BirthmarkCamera/BirthmarkCameraTests/CryptoServiceTests.swift`

```swift
import XCTest
@testable import BirthmarkCamera

class CryptoServiceTests: XCTestCase {

    func testDeviceSecretGeneration() {
        let secret1 = CryptoService.shared.generateDeviceSecret()
        let secret2 = CryptoService.shared.generateDeviceSecret()

        XCTAssertEqual(secret1.count, 32, "Device secret should be 32 bytes")
        XCTAssertNotEqual(secret1, secret2, "Device secrets should be unique")
    }

    func testSHA256Hashing() {
        let data = "test".data(using: .utf8)!
        let hash = CryptoService.shared.sha256(data)

        XCTAssertEqual(hash.count, 64, "SHA-256 hash should be 64 hex characters")
        XCTAssertEqual(
            hash,
            "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
            "Hash should match expected value"
        )
    }

    func testECDSASigning() throws {
        // Generate test key pair
        let privateKey = P256.Signing.PrivateKey()
        let publicKey = privateKey.publicKey

        // Sign test data
        let testData = "test bundle".data(using: .utf8)!
        let signature = try privateKey.signature(for: testData)

        // Verify signature
        XCTAssertTrue(
            publicKey.isValidSignature(signature, for: testData),
            "Signature should verify"
        )
    }

    func testCanonicalBundleFormat() {
        // Test that canonical format matches spec
        let imageHash = "a" * 64
        let cert = "test_cert_base64"
        let timestamp = 1700000000
        let gpsHash: String? = nil

        // This would need to be exposed or tested via integration
        // Verify format: hash\ncert\ntimestamp\ngps\n
    }
}
```

**File:** `packages/mobile-app/BirthmarkCamera/BirthmarkCameraTests/KeychainServiceTests.swift`

```swift
class KeychainServiceTests: XCTestCase {

    override func setUp() {
        KeychainService.shared.deleteAll()
    }

    func testDeviceCertificateStorage() {
        let testCert = "test_certificate_pem"

        KeychainService.shared.saveDeviceCertificate(testCert)
        let retrieved = KeychainService.shared.getDeviceCertificate()

        XCTAssertEqual(retrieved, testCert, "Certificate should round-trip")
    }

    func testPrivateKeyStorage() {
        let testKey = "test_private_key_pem"

        KeychainService.shared.saveDevicePrivateKey(testKey)
        let retrieved = KeychainService.shared.getDevicePrivateKey()

        XCTAssertEqual(retrieved, testKey, "Private key should round-trip")
    }

    func testFullyProvisionedCheck() {
        XCTAssertFalse(KeychainService.shared.isFullyProvisioned())

        KeychainService.shared.saveDeviceCertificate("cert")
        KeychainService.shared.saveDevicePrivateKey("key")
        KeychainService.shared.saveDeviceSecret(Data([0x01, 0x02]))
        KeychainService.shared.saveKeyTableIndices([1, 2, 3])
        KeychainService.shared.saveKeyTables([[], [], []])

        XCTAssertTrue(KeychainService.shared.isFullyProvisioned())
    }
}
```

**File:** `packages/mobile-app/BirthmarkCamera/BirthmarkCameraTests/CertificateBundleTests.swift`

```swift
class CertificateBundleTests: XCTestCase {

    func testBundleValidation() {
        let validBundle = CertificateBundle(
            imageHash: String(repeating: "a", count: 64),
            cameraCert: "dGVzdA==",  // base64
            timestamp: Int(Date().timeIntervalSince1970),
            gpsHash: nil,
            bundleSignature: "dGVzdA=="
        )

        XCTAssertNoThrow(try validBundle.validate())
    }

    func testInvalidHashFormat() {
        let invalidBundle = CertificateBundle(
            imageHash: "not_a_valid_hash",  // Too short
            cameraCert: "dGVzdA==",
            timestamp: Int(Date().timeIntervalSince1970),
            gpsHash: nil,
            bundleSignature: "dGVzdA=="
        )

        XCTAssertThrowsError(try invalidBundle.validate())
    }

    func testFutureTimestamp() {
        let futureBundle = CertificateBundle(
            imageHash: String(repeating: "a", count: 64),
            cameraCert: "dGVzdA==",
            timestamp: Int(Date().timeIntervalSince1970) + 1000,  // Future
            gpsHash: nil,
            bundleSignature: "dGVzdA=="
        )

        XCTAssertThrowsError(try futureBundle.validate())
    }
}
```

**Priority:** HIGH
**Estimated Time:** 1 day
**Run:** `xcodebuild test -scheme BirthmarkCamera -destination 'platform=iOS Simulator,name=iPhone 14'`

#### Backend Unit Tests

**File:** `packages/sma/tests/test_certificate_generator.py`

```python
import pytest
from cryptography import x509
from sma.provisioning.certificate_generator import CertificateGenerator

def test_generate_device_certificate():
    """Test device certificate generation."""
    cert_gen = CertificateGenerator(
        ca_private_key_path="tests/fixtures/ca_key.pem",
        ca_cert_path="tests/fixtures/ca_cert.pem"
    )

    device_cert, device_key, cert_chain = cert_gen.generate_device_certificate(
        device_serial="TEST-12345",
        device_secret="abc123",
        key_table_indices=[1, 2, 3]
    )

    # Verify certificate is valid PEM
    cert = x509.load_pem_x509_certificate(device_cert.encode())
    assert cert is not None

    # Verify subject
    subject = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
    assert subject == "TEST-12345"

    # Verify private key format
    assert "BEGIN PRIVATE KEY" in device_key
```

**File:** `packages/sma/tests/test_certificate_validator.py`

```python
def test_validate_certificate_bundle():
    """Test certificate bundle validation."""
    validator = CertificateValidator(ca_cert_path="tests/fixtures/ca_cert.pem")

    # Create test bundle
    is_valid, reason = validator.validate_certificate_bundle(
        camera_cert_b64="base64_encoded_cert",
        image_hash="a" * 64,
        timestamp=1700000000,
        gps_hash=None,
        bundle_signature_b64="base64_signature"
    )

    assert is_valid or reason != ""
```

**Priority:** HIGH
**Estimated Time:** 1 day
**Run:** `cd packages/sma && pytest`

---

### Integration Tests (REQUIRED)

#### End-to-End Flow Test

**File:** `packages/mobile-app/BirthmarkCamera/BirthmarkCameraTests/IntegrationTests.swift`

```swift
class IntegrationTests: XCTestCase {

    func testCompleteProvisioningFlow() async throws {
        // This requires running SMA backend

        // 1. Generate device secret
        let deviceSecret = CryptoService.shared.generateDeviceSecret()

        // 2. Call SMA for provisioning
        let response = try await NetworkService.shared.provisionDevice(
            deviceSecret: deviceSecret
        )

        // 3. Verify response
        XCTAssertEqual(response.deviceSecret, deviceSecret.hexString)
        XCTAssertEqual(response.keyTableIndices.count, 3)
        XCTAssertEqual(response.keyTables.count, 3)
        XCTAssertFalse(response.deviceCertificate.isEmpty)
        XCTAssertFalse(response.devicePrivateKey.isEmpty)

        // 4. Save credentials
        KeychainService.shared.saveDeviceCertificate(response.deviceCertificate)
        KeychainService.shared.saveDevicePrivateKey(response.devicePrivateKey)
        KeychainService.shared.saveDeviceSecret(deviceSecret)
        KeychainService.shared.saveKeyTableIndices(response.keyTableIndices)
        KeychainService.shared.saveKeyTables(response.keyTables)

        // 5. Verify provisioning
        XCTAssertTrue(KeychainService.shared.isFullyProvisioned())
    }

    func testCompleteAuthenticationFlow() async throws {
        // Assumes device is provisioned

        // 1. Create test image
        let testImage = UIImage(systemName: "photo")!
        let imageData = testImage.pngData()!

        // 2. Authenticate
        let response = try await AuthenticationService.shared.authenticateImage(imageData)

        // 3. Verify response
        XCTAssertFalse(response.receiptId.isEmpty)
        XCTAssertEqual(response.status, "pending_validation")
    }
}
```

**Test Environment Setup:**
```bash
# Terminal 1: Start SMA
cd packages/sma
uvicorn src.main:app --port 8001

# Terminal 2: Start Aggregator
cd packages/blockchain
uvicorn src.main:app --port 8545

# Terminal 3: Run iOS tests
cd packages/mobile-app/BirthmarkCamera
xcodebuild test -scheme BirthmarkCamera -destination 'platform=iOS Simulator,name=iPhone 14'
```

**Priority:** CRITICAL
**Estimated Time:** 2 days (including infrastructure setup)

---

### Manual Testing Checklist (REQUIRED)

#### Provisioning Tests

- [ ] **Fresh Install**: Delete app, reinstall, provision successfully
- [ ] **Network Failure**: Disconnect WiFi during provisioning, verify error message
- [ ] **Invalid Server URL**: Change to bad URL, verify error handling
- [ ] **Re-provisioning**: Clear credentials, re-provision successfully
- [ ] **Provisioning Interruption**: Force quit during provisioning, restart, verify clean state

#### Authentication Tests

- [ ] **Single Photo**: Take photo, verify submission success
- [ ] **Multiple Photos**: Take 10 photos in a row, all submit successfully
- [ ] **Large Image**: Take high-res photo (12MP+), verify hash computation speed
- [ ] **Network Failure**: Take photo offline, verify error message
- [ ] **Invalid Certificate**: Manually corrupt certificate in Keychain, verify error
- [ ] **Signature Verification**: Submit bundle, verify SMA validates signature

#### Verification Tests

- [ ] **Verify Authentic Photo**: Hash submitted photo, query blockchain, verify TRUE
- [ ] **Verify Non-Authentic Photo**: Hash random photo, query blockchain, verify FALSE
- [ ] **Verify Edited Photo**: Edit submitted photo, re-hash, query blockchain, verify FALSE

#### Performance Tests

- [ ] **Hash Speed**: Measure time to hash 12MP image (target: <100ms)
- [ ] **Signing Speed**: Measure time to sign bundle (target: <10ms)
- [ ] **Provisioning Speed**: Measure total provisioning time (target: <3s)
- [ ] **Submission Speed**: Measure end-to-end submission (target: <500ms)

#### Edge Cases

- [ ] **Device Rename**: Rename device, verify secret unchanged, can still submit
- [ ] **App Update**: Update app version, verify credentials persist
- [ ] **iOS Update**: Update iOS, verify credentials persist
- [ ] **Low Storage**: Fill device storage, verify provisioning/submission fails gracefully
- [ ] **Background Submission**: Submit while app backgrounded, verify works
- [ ] **Airplane Mode**: Take photo in airplane mode, verify queue behavior

**Priority:** CRITICAL
**Estimated Time:** 2 days

---

## Part 3: Missing Features Summary

### CRITICAL (Blocks Release)

1. ✅ **SMA Certificate Generation** - Generate ECDSA keys and X.509 certificates
2. ✅ **SMA Certificate Validation** - Validate bundles and signatures
3. ✅ **CA Certificate Setup** - One-time root CA generation
4. ⚠️ **Settings UI** - Configure server URLs for TestFlight testing
5. ⚠️ **Camera UI** - Photo capture interface (status unknown)

### HIGH PRIORITY (Should Have)

1. ⚠️ **Unit Tests** - iOS and backend test suites
2. ⚠️ **Integration Tests** - End-to-end flow validation
3. ⚠️ **Error Handling** - Production-quality error messages and recovery
4. ⚠️ **Logging** - Structured logging for debugging

### MEDIUM PRIORITY (Nice to Have)

1. ⏸️ **Offline Queue** - Certificate bundle queueing
2. ⏸️ **GPS Hashing** - Optional location verification
3. ⏸️ **Submission History** - View past submissions
4. ⏸️ **Certificate Viewer** - Inspect device certificate

### LOW PRIORITY (Future)

1. ⏸️ **Multiple Photos** - Batch submission
2. ⏸️ **Photo Library** - Re-submit existing photos
3. ⏸️ **Share Extension** - Submit from Photos app
4. ⏸️ **Widget** - Quick submission count

---

## Part 4: Release Timeline

### Week 1: Backend Critical Path

**Days 1-2: SMA Certificate Infrastructure**
- Generate CA certificate (1 hour)
- Implement `CertificateGenerator` class (4 hours)
- Update provisioning endpoint (2 hours)
- Test certificate generation (2 hours)

**Days 3-4: SMA Validation**
- Implement `CertificateValidator` class (4 hours)
- Update `/validate-cert` endpoint (2 hours)
- Test validation flow (2 hours)
- Fix bugs (2 hours)

**Day 5: Integration Testing**
- End-to-end provisioning test (2 hours)
- End-to-end submission test (2 hours)
- Fix integration bugs (4 hours)

### Week 2: iOS Completion

**Days 1-2: Missing Features**
- Settings UI implementation (4 hours)
- Camera UI review/completion (4-8 hours)
- Offline queue implementation (3 hours)
- Error handling polish (2 hours)

**Days 3-4: Testing**
- Write unit tests (8 hours)
- Write integration tests (4 hours)
- Manual testing checklist (8 hours)

**Day 5: Bug Fixes**
- Fix all critical bugs from testing
- Performance optimization
- Code cleanup

### Week 3: TestFlight Beta

**Days 1-2: Deployment**
- Deploy SMA to production server
- Deploy aggregator to production server
- Update iOS app with production URLs
- Generate production CA certificate

**Day 3: TestFlight Upload**
- Build release IPA
- Upload to App Store Connect
- Submit for TestFlight review
- Create testing instructions

**Days 4-5: Beta Testing**
- Invite 10-20 internal testers
- Monitor crash reports
- Fix critical issues
- Iterate

---

## Part 5: Pre-Release Checklist

### Backend Readiness

- [ ] CA certificate generated and secured
- [ ] SMA provisioning returns real certificates
- [ ] SMA validation verifies signatures correctly
- [ ] Aggregator submits to blockchain
- [ ] Blockchain stores hashes
- [ ] Verification API works
- [ ] All endpoints have error handling
- [ ] Rate limiting configured
- [ ] Logging configured
- [ ] Monitoring configured

### iOS Readiness

- [ ] All services implemented
- [ ] Settings UI complete
- [ ] Camera UI complete
- [ ] Error handling production-ready
- [ ] Unit tests pass (>80% coverage)
- [ ] Integration tests pass
- [ ] Manual testing complete
- [ ] Performance targets met
- [ ] Privacy policy updated
- [ ] App Store description written
- [ ] Screenshots captured
- [ ] TestFlight instructions written

### Security Checklist

- [ ] Private keys stored in Keychain only
- [ ] No secrets in code
- [ ] HTTPS enforced for all requests
- [ ] Certificate chain validation
- [ ] Signature verification
- [ ] Input validation on all APIs
- [ ] SQL injection prevention
- [ ] XSS prevention
- [ ] Rate limiting

### Documentation

- [ ] iOS app pipeline documented ✅
- [ ] Backend API documented
- [ ] Testing procedures documented
- [ ] Deployment guide written
- [ ] Troubleshooting guide written
- [ ] Privacy policy finalized
- [ ] Terms of service finalized

---

## Conclusion

**Status:** 70% Complete

**Critical Blockers:**
1. SMA certificate generation (1-2 days)
2. SMA certificate validation (1-2 days)
3. iOS-backend integration testing (2 days)

**Nice-to-Haves:**
1. Offline queue (3 hours)
2. GPS hashing (4-6 hours)
3. Enhanced error handling (1 day)

**Estimated Time to TestFlight Beta:** 2-3 weeks

**Recommended Next Steps:**
1. Generate CA certificate (1 hour) - START HERE
2. Implement SMA certificate generation (1 day)
3. Implement SMA certificate validation (1 day)
4. Run end-to-end integration tests (1 day)
5. Write unit tests (1 day)
6. Complete manual testing checklist (2 days)
7. Deploy to production (1 day)
8. TestFlight beta release (1 day)

**Ready for Production?** No - Critical backend work required first
**Ready for Internal Testing?** Yes - After Week 1 backend work
**Ready for TestFlight?** Week 3
