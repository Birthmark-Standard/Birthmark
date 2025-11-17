# Birthmark Camera - iOS Architecture

Technical architecture documentation for the iOS authentication app.

## System Overview

```
┌─────────────────────────────────────────────────┐
│              iOS Application                     │
│                                                  │
│  ┌────────────┐        ┌──────────────┐        │
│  │  Camera    │───────▶│ Crypto       │        │
│  │  Service   │        │ Service      │        │
│  └────────────┘        └──────────────┘        │
│         │                      │                │
│         ▼                      ▼                │
│  ┌────────────┐        ┌──────────────┐        │
│  │   Image    │───────▶│ Auth         │        │
│  │   Data     │        │ Service      │        │
│  └────────────┘        └──────────────┘        │
│                               │                 │
│                               ▼                 │
│                        ┌──────────────┐        │
│                        │ Network      │        │
│                        │ Service      │        │
│                        └──────────────┘        │
│                               │                 │
└───────────────────────────────┼─────────────────┘
                                │
                                ▼
                    ┌─────────────────────┐
                    │ Aggregation Server   │
                    │ (Phase 1 Backend)    │
                    └─────────────────────┘
```

## Service Layer Details

### CameraService

**Responsibility:** Camera capture using AVFoundation

**Key Methods:**
- `setupCaptureSession()` - Configure camera input/output
- `capturePhoto(completion:)` - Capture single photo
- `saveToPhotoLibrary(_:completion:)` - Save to Camera Roll

**Dependencies:**
- AVFoundation
- Photos framework

**State:**
- `captureSession: AVCaptureSession?`
- `photoOutput: AVCapturePhotoOutput?`
- `isAuthorized: Bool`

### CryptoService

**Responsibility:** All cryptographic operations

**Key Methods:**
- `generateDeviceFingerprint() -> String` - First launch only
- `sha256(_ data: Data) -> String` - Image hashing (~10ms)
- `deriveKey(masterKey:keyIndex:tableId:) -> SymmetricKey` - HKDF (~1ms)
- `encryptFingerprint(_:key:) -> CameraToken` - AES-GCM (~1ms)
- `selectRandomTable(from:) -> Int` - Random table selection
- `generateRandomKeyIndex() -> Int` - Random key (0-999)

**Algorithms:**
- SHA-256 for hashing
- HKDF-SHA256 for key derivation
- AES-256-GCM for encryption

**No State:** Singleton with no mutable state

### KeychainService

**Responsibility:** Secure storage in iOS Keychain

**Key Methods:**
- `saveDeviceFingerprint(_ fingerprint: String)`
- `getDeviceFingerprint() -> String?`
- `saveTableAssignments(_ assignments: [Int])`
- `getTableAssignments() -> [Int]?`
- `saveMasterKey(_ key: Data, forTable: Int)`
- `getMasterKey(forTable: Int) -> Data?`

**Storage Keys:**
- `com.birthmark.device_fingerprint` - Device fingerprint hash
- `com.birthmark.table_assignments` - JSON array of 3 table IDs
- `com.birthmark.master_key_X` - Master key for table X (3 total)

**Security:**
- `kSecAttrAccessibleAfterFirstUnlock` - Available after device unlock
- Could upgrade to Secure Enclave for production

### NetworkService

**Responsibility:** HTTP client + offline queue

**Key Methods:**
- `submitBundle(_ bundle: AuthenticationBundle) async throws -> SubmissionResponse`
- `queueBundle(_ bundle: AuthenticationBundle)` - Add to offline queue
- `processQueue() async` - Retry queued submissions
- `getQueueCount() -> Int`

**Queue Management:**
- Stored in UserDefaults (JSON)
- Max 5 attempts per submission
- Exponential backoff: 1s between retries
- FIFO processing order

**API Format:**
```json
{
  "image_hash": "64 hex chars",
  "encrypted_nuc_token": "base64",
  "table_references": [int, int, int],
  "key_indices": [int, int, int],
  "timestamp": unix_timestamp,
  "device_signature": "base64"
}
```

### AuthenticationService

**Responsibility:** Orchestrate complete auth flow

**Key Method:**
```swift
func authenticateImage(_ imageData: Data) async throws -> SubmissionResponse {
    // 1. Hash image (~10ms)
    let hash = CryptoService.shared.sha256(imageData)

    // 2. Get device credentials
    let fingerprint = KeychainService.shared.getDeviceFingerprint()
    let assignments = KeychainService.shared.getTableAssignments()

    // 3. Select random table and key
    let tableId = CryptoService.shared.selectRandomTable(from: assignments)
    let keyIndex = CryptoService.shared.generateRandomKeyIndex()

    // 4. Get master key
    let masterKey = KeychainService.shared.getMasterKey(forTable: tableId)

    // 5. Derive encryption key (~1ms)
    let key = CryptoService.shared.deriveKey(masterKey, keyIndex, tableId)

    // 6. Encrypt fingerprint (~1ms)
    let token = CryptoService.shared.encryptFingerprint(fingerprint, key: key)

    // 7. Create bundle
    let bundle = AuthenticationBundle(...)

    // 8. Submit (or queue if offline)
    return try await NetworkService.shared.submitBundle(bundle)
}
```

**Total time: ~15ms**

## Data Models

### AuthenticationBundle

```swift
struct AuthenticationBundle: Codable {
    let imageHash: String           // SHA-256 (64 hex chars)
    let cameraToken: CameraToken    // Encrypted fingerprint
    let tableId: Int                // Selected table (0-2499)
    let keyIndex: Int               // Selected key (0-999)
    let timestamp: Int              // Unix timestamp
    let gpsHash: String?            // Optional GPS hash
}
```

### CameraToken

```swift
struct CameraToken: Codable {
    let ciphertext: Data    // AES-GCM encrypted fingerprint
    let authTag: Data       // GCM authentication tag (16 bytes)
    let nonce: Data         // Random nonce (12 bytes)
}
```

### QueuedSubmission

```swift
struct QueuedSubmission: Codable {
    let id: UUID
    let bundle: AuthenticationBundle
    let createdAt: Date
    var attemptCount: Int
    var lastAttempt: Date?
}
```

## View Layer

### App State Management

```swift
class AppState: ObservableObject {
    @Published var isProvisioned: Bool
    @Published var deviceInfo: DeviceInfo?
    @Published var queueCount: Int

    func completeProvisioning(fingerprint: String, assignments: [Int])
}
```

**State Flow:**
1. App launch → Check Keychain for fingerprint
2. If exists → `isProvisioned = true` → Show MainTabView
3. If not exists → `isProvisioned = false` → Show ProvisioningView
4. After provisioning → Update state → Show MainTabView

### View Hierarchy

```
ContentView
├─ If not provisioned:
│  └─ ProvisioningView
│     └─ Generate fingerprint
│     └─ Request table assignments
│     └─ Transition to main app
│
└─ If provisioned:
   └─ MainTabView
      ├─ CameraView (Tab 1)
      │  └─ Camera preview
      │  └─ Capture button
      │  └─ Status messages
      │
      └─ SettingsView (Tab 2)
         └─ Device info
         └─ Queue management
         └─ Reset device
```

## Cryptographic Flow

### Key Derivation (HKDF-SHA256)

```
Input:
- master_key: 256-bit key from SMA (stored in Keychain)
- key_index: 0-999 (selected randomly each capture)
- salt: empty (matching SMA behavior)
- info: "Birthmark" + key_index

Process:
1. HKDF-Extract: PRK = HMAC-SHA256(salt, master_key)
2. HKDF-Expand: OKM = HMAC-SHA256(PRK, info + 0x01)
3. Take first 32 bytes = derived_key

Output:
- derived_key: 256-bit symmetric key (unique per capture)
```

**Why HKDF?**
- Allows 1,000 unique keys per table without storing them all
- SMA can independently derive same key for validation
- Cryptographically secure key derivation from master

### AES-GCM Encryption

```
Input:
- plaintext: device fingerprint (64 hex chars = 64 bytes)
- key: derived 256-bit key
- nonce: 96-bit random (generated per encryption)

Process:
1. Generate random 96-bit nonce
2. AES-256-GCM encrypt: (ciphertext, tag) = AES-GCM(plaintext, key, nonce)
3. Return (ciphertext, tag, nonce)

Output:
- ciphertext: Encrypted fingerprint
- auth_tag: 128-bit authentication tag
- nonce: 96-bit nonce (sent in clear)
```

**Why AES-GCM?**
- Authenticated encryption (confidentiality + integrity)
- Fast on modern hardware (~0.3ms)
- Standard in cryptographic APIs (CryptoKit)

## Performance Optimization

### Critical Path Analysis

**Target: <20ms total authentication overhead**

Breakdown:
1. Image already captured (not counted)
2. SHA-256 hash: ~8ms (12MP JPEG)
3. Keychain reads: ~1ms (3 reads)
4. HKDF derivation: ~0.5ms
5. AES-GCM encryption: ~0.3ms
6. Bundle creation: ~0.1ms
7. Network call: async (not blocking)

**Total: ~10ms (well under target)**

### Background Processing

```swift
// Camera capture callback
func handleCapturedImage(_ imageData: Data) {
    // Start async authentication
    Task {
        do {
            // This runs in background
            let response = try await AuthenticationService.shared.authenticateImage(imageData)

            // UI update on main thread
            DispatchQueue.main.async {
                self.lastStatus = "✓ Authenticated"
            }
        } catch {
            // Handle error
        }
    }

    // User sees photo immediately, auth happens in background
}
```

**Key insight:** Network submission is async, so user never waits for server response.

### Memory Management

**Image data:**
- Captured: ~2-5MB per JPEG
- Hashed in-place (no extra copy)
- Released after hash computed
- Not stored by app (only saved to Photo Library)

**Queue storage:**
- ~200 bytes per queued submission
- JSON encoded in UserDefaults
- Max realistic queue: 10,000 items = 2MB
- Negligible vs typical app storage

## Security Considerations

### Threat Model

**What iOS app protects against:**
- ✅ Casual image manipulation after capture
- ✅ Device fingerprint theft (Keychain protected)
- ✅ Network eavesdropping (HTTPS to aggregator)

**What iOS app does NOT protect against:**
- ❌ Modified app that changes hash before submission
- ❌ Rooted/jailbroken devices
- ❌ Manipulation before camera API capture
- ❌ Complete image synthesis (no hardware proof)

### Why This Is OK for Phase 2

**Phase 2 goals:**
1. ✅ Validate architecture on mobile
2. ✅ Measure performance (battery, latency)
3. ✅ Prove user demand
4. ✅ Generate evidence for manufacturers

**Not goals:**
1. ❌ Production-grade security
2. ❌ Prevent determined adversaries
3. ❌ Replace Phase 3 hardware integration

**For manufacturers:** This app demonstrates what's *possible* at app-level and proves why hardware integration is necessary for production security.

### Keychain Security

**Current: `kSecAttrAccessibleAfterFirstUnlock`**
- Available after first device unlock
- Persists across reboots
- Protected by device passcode
- Adequate for proof-of-concept

**Production: Secure Enclave**
- Hardware-backed key storage
- Keys never leave secure processor
- Requires additional implementation:
  ```swift
  let access = SecAccessControlCreateWithFlags(
      nil,
      kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
      .privateKeyUsage,
      nil
  )
  ```

## Error Handling

### Error Types

```swift
enum AuthError: Error {
    case notProvisioned        // No fingerprint in Keychain
    case missingKey            // Master key not found
    case encryptionFailed      // Crypto error
    case submissionFailed      // Network error
}

enum CameraError: Error {
    case outputNotAvailable
    case noImageData
    case photoLibraryUnauthorized
    case saveFailed
}

enum NetworkError: Error {
    case invalidResponse
    case serverError(Int)
    case encodingFailed
}
```

### Recovery Strategy

| Error | Recovery |
|-------|----------|
| Network failure | Queue for later, show "Queued" status |
| Camera permission denied | Show prompt, link to Settings |
| Photo library denied | Skip save, auth still succeeds |
| Not provisioned | Show ProvisioningView |
| Missing key | Show error, offer re-provision |

## Testing Strategy

### Unit Tests (Recommended)

```swift
class CryptoServiceTests: XCTestCase {
    func testSHA256() {
        let data = "test".data(using: .utf8)!
        let hash = CryptoService.shared.sha256(data)
        XCTAssertEqual(hash, "9f86d081884c7d659a2feaa0c55ad015...")
    }

    func testHKDF() { /* ... */ }
    func testAESGCM() { /* ... */ }
}

class KeychainServiceTests: XCTestCase {
    func testSaveAndRetrieve() { /* ... */ }
}
```

### Integration Tests

1. **Provisioning flow**
   - Generate fingerprint
   - Save to Keychain
   - Verify persists across app restarts

2. **Capture + Auth flow**
   - Take photo
   - Verify hash computed
   - Verify bundle created
   - Verify submission attempted

3. **Offline queue**
   - Disable network
   - Take photos
   - Verify queued
   - Enable network
   - Verify processed

### Performance Benchmarks

```swift
func measureAuthenticationPerformance() {
    let imageData = /* load test image */

    measure {
        let expectation = expectation(description: "auth")
        Task {
            _ = try await AuthenticationService.shared.authenticateImage(imageData)
            expectation.fulfill()
        }
        wait(for: [expectation], timeout: 1.0)
    }
}
```

## Deployment

### TestFlight Checklist

- [ ] Set bundle identifier
- [ ] Configure signing
- [ ] Archive build
- [ ] Upload to App Store Connect
- [ ] Wait for review (~24-48 hours)
- [ ] Add testers
- [ ] Distribute

### Configuration for Production

**Before TestFlight release:**

1. Update aggregator URL in `NetworkService.swift`
2. Implement real SMA provisioning in `ProvisioningView.swift`
3. Add analytics/crash reporting (optional)
4. Test on multiple devices
5. Verify battery usage is acceptable

## Future Enhancements

### Short Term (Phase 2)

1. **Real SMA integration**
   - Replace mock provisioning
   - Call actual SMA endpoints
   - Handle errors gracefully

2. **GPS hashing**
   - Optional location authentication
   - Hash coordinates (not send raw location)
   - Privacy-preserving

3. **Background upload**
   - iOS Background Tasks framework
   - Scheduled queue processing
   - Battery-efficient

### Long Term (Post-Phase 2)

1. **Verification viewer**
   - Query blockchain for hash
   - Show verification status
   - Provenance chain display

2. **Federated aggregators**
   - User selects trusted institution
   - Multiple server support
   - Fallback if primary fails

3. **Social media warnings**
   - Detect screenshot or screen recording
   - Warn user about metadata stripping
   - Explain limitations

---

*This architecture is designed for Phase 2 validation. Phase 3 manufacturer integration will provide hardware-level authentication with proper raw sensor access.*
