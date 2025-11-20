# Phase 2 iOS Implementation - Errors and Missing Code

**Date:** November 2025
**Status:** Critical Issues Found
**Impact:** iOS app cannot properly submit to aggregation server or SMA

---

## Executive Summary

The Phase 2 iOS implementation has **critical architectural mismatches** between the iOS app and the backend infrastructure. The iOS app is using the **deprecated Phase 1 submission format** while the backend expects **certificate-based submissions**. Additionally, the iOS app is missing certificate generation, storage, and submission code.

**Result:** The iOS app will fail to submit photos correctly in Phase 2.

---

## Critical Errors Found

### 1. **iOS App Uses Wrong Submission Format** ❌

**File:** `packages/mobile-app/BirthmarkCamera/BirthmarkCamera/Models/AuthenticationBundle.swift`

**Problem:**
The iOS app creates submissions using the OLD Phase 1 format:
```swift
func toAPIFormat() -> [String: Any] {
    var dict: [String: Any] = [
        "image_hash": imageHash,
        "encrypted_nuc_token": cameraToken.toSealedBoxData().base64EncodedString(),
        "table_references": [tableId, tableId, tableId],  // ❌ Wrong: repeating single table 3x
        "key_indices": [keyIndex, keyIndex, keyIndex],    // ❌ Wrong: repeating single key 3x
        "timestamp": timestamp,
        "device_signature": createBundleSignature().base64EncodedString()
    ]
}
```

**Expected Format (Phase 2 - Certificate Bundle):**
```json
{
  "image_hash": "abc123...",
  "camera_cert": "base64_encoded_DER_certificate",
  "timestamp": 1732000000,
  "gps_hash": "optional",
  "bundle_signature": "base64_ecdsa_signature"
}
```

**Impact:**
- Submissions will be rejected or processed incorrectly
- No certificate document being sent
- Wrong data structure

**Fix Required:**
- Create new `CertificateBundle` struct matching server schema
- Generate proper certificate-based submissions
- Remove old `AuthenticationBundle.toAPIFormat()` method

---

### 2. **iOS App Uses Wrong Endpoint** ❌

**File:** `packages/mobile-app/BirthmarkCamera/BirthmarkCamera/Services/NetworkService.swift`

**Problem:**
```swift
aggregatorURL = URL(string: "http://localhost:8545/api/v1/submit")!
```

**Issues:**
- Endpoint `/api/v1/submit` expects OLD Phase 1 `AuthenticationBundle` format
- Should use `/api/v1/submit-cert` for certificate-based submissions
- Port 8545 is correct (blockchain node)

**Expected:**
```swift
aggregatorURL = URL(string: "http://localhost:8545/api/v1/submit-cert")!
```

**Impact:**
- Submissions go to wrong endpoint
- Wrong validation logic applied
- Certificate not processed

**Fix Required:**
- Change endpoint to `/api/v1/submit-cert`
- Update submission method to send `CertificateBundle` format

---

### 3. **iOS App Missing Certificate Generation** ❌

**Problem:**
The iOS app has **NO code** to generate device certificates during provisioning.

**What's Missing:**
1. **Certificate Request to SMA:**
   - No call to SMA `/api/v1/devices/provision` endpoint
   - Currently generates mock local data instead

2. **Certificate Storage:**
   - No Keychain method to save certificate
   - No Keychain method to retrieve certificate

3. **Certificate Usage:**
   - No code to include certificate in submissions
   - No code to sign bundles with certificate

**Current Implementation:**
```swift
// ❌ WRONG: Generates mock data locally
func performProvisioning() async throws {
    let deviceSecret = CryptoService.shared.generateDeviceSecret()
    let keyTableIndices = generateRandomTableAssignments()  // Random local
    let keyTables = generateMockKeyTables()  // Mock local data
    // ... saves to Keychain, but NO certificate
}
```

**Expected Implementation:**
```swift
// ✅ CORRECT: Call SMA for provisioning
func performProvisioning() async throws {
    // 1. Generate device secret
    let deviceSecret = CryptoService.shared.generateDeviceSecret()

    // 2. Call SMA /api/v1/devices/provision
    let response = try await NetworkService.shared.provisionDevice(
        deviceSecret: deviceSecret
    )

    // 3. Save certificate + keys
    KeychainService.shared.saveDeviceCertificate(response.device_certificate)
    KeychainService.shared.saveDeviceSecret(deviceSecret)
    KeychainService.shared.saveKeyTableIndices(response.key_table_indices)
    KeychainService.shared.saveKeyTables(response.key_tables)
}
```

**Impact:**
- No certificate to send with submissions
- Cannot authenticate with aggregation server
- Cannot validate with SMA

**Fix Required:**
- Add `provisionDevice()` method to `NetworkService.swift`
- Add certificate storage methods to `KeychainService.swift`
- Update `ProvisioningView.swift` to call SMA instead of generating mock data

---

### 4. **iOS Keychain Service Missing Certificate Storage** ❌

**File:** `packages/mobile-app/BirthmarkCamera/BirthmarkCamera/Services/KeychainService.swift`

**Problem:**
No methods exist to store or retrieve device certificates.

**Missing Methods:**
```swift
// ❌ MISSING in KeychainService
func saveDeviceCertificate(_ certificate: String)  // PEM or DER
func getDeviceCertificate() -> String?
func saveDevicePrivateKey(_ privateKey: String)  // For signing
func getDevicePrivateKey() -> String?
func saveCertificateChain(_ chain: String)
func getCertificateChain() -> String?
```

**Impact:**
- Certificate received from SMA cannot be persisted
- No certificate available for submissions
- Cannot sign bundles

**Fix Required:**
- Add certificate storage methods to KeychainService
- Store certificate as PEM or DER string
- Store private key securely for bundle signing

---

### 5. **iOS Authentication Service Creates Wrong Bundle** ❌

**File:** `packages/mobile-app/BirthmarkCamera/BirthmarkCamera/Services/AuthenticationService.swift`

**Problem:**
Creates `AuthenticationBundle` instead of certificate-based submission.

**Current Code:**
```swift
let bundle = AuthenticationBundle(
    imageHash: imageHash,
    cameraToken: cameraToken,  // ❌ Old format
    tableId: globalTableIndex,
    keyIndex: keyIndex,
    timestamp: Int(Date().timeIntervalSince1970),
    gpsHash: nil
)
```

**Expected Code:**
```swift
// ✅ Should create CertificateBundle
guard let deviceCertificate = KeychainService.shared.getDeviceCertificate() else {
    throw AuthError.missingCertificate
}

let bundle = CertificateBundle(
    imageHash: imageHash,
    cameraCert: deviceCertificate,  // Base64-encoded DER
    timestamp: Int(Date().timeIntervalSince1970),
    gpsHash: nil,
    bundleSignature: signBundle(...)  // ECDSA signature
)
```

**Impact:**
- Wrong bundle type sent to aggregation server
- Validation will fail
- Cannot be processed by certificate validator

**Fix Required:**
- Create new `CertificateBundle` struct
- Update `authenticateImage()` to create certificate bundles
- Implement bundle signing with device private key

---

### 6. **iOS App Missing Bundle Signing** ❌

**Problem:**
The iOS app creates a **mock signature** instead of proper ECDSA signing.

**Current Implementation:**
```swift
// ❌ WRONG: SHA-256 hash as "signature"
private func createBundleSignature() -> Data {
    let signatureInput = imageHash + cameraToken.toSealedBoxData().base64EncodedString() + ...
    let hash = SHA256.hash(data: data)
    return Data(hash)  // NOT a signature!
}
```

**Expected Implementation:**
```swift
// ✅ CORRECT: ECDSA signature with device private key
func signBundle(imageHash: String, cameraCert: String, timestamp: Int) throws -> String {
    guard let privateKey = KeychainService.shared.getDevicePrivateKey() else {
        throw SigningError.noPrivateKey
    }

    // Create canonical bundle data
    let bundleData = createCanonicalBundleData(imageHash, cameraCert, timestamp)

    // Sign with P-256 ECDSA
    let signature = try P256.Signing.PrivateKey(pemRepresentation: privateKey)
        .signature(for: bundleData)

    return signature.rawRepresentation.base64EncodedString()
}
```

**Impact:**
- Bundle signatures are invalid
- Aggregation server cannot verify bundle integrity
- Security vulnerability

**Fix Required:**
- Implement proper ECDSA signing
- Use device private key from provisioning
- Follow canonical bundle format for signing

---

### 7. **SMA Provisioning Returns Data iOS Doesn't Use** ⚠️

**File:** `packages/sma/src/main.py` (Endpoint: `/api/v1/devices/provision`)

**Problem:**
SMA returns:
```python
{
    "device_certificate": "PEM...",  # ✅ Generated
    "device_private_key": "PEM...",  # ✅ Generated
    "certificate_chain": "PEM...",   # ✅ Generated
    "key_tables": [[...], [...], [...]], # ✅ 3 arrays of 1000 keys
    "key_table_indices": [42, 157, 891], # ✅ Global indices
    "device_secret": "hex..."            # ✅ For validation
}
```

But iOS app:
```swift
// ❌ Doesn't call SMA - generates mock data locally
// ❌ Doesn't save certificate even if it received it
// ❌ Doesn't save private key
```

**Impact:**
- Provisioning data from SMA is wasted
- iOS generates incompatible local mock data
- No valid certificate for submissions

**Fix Required:**
- Update iOS provisioning to call SMA API
- Save ALL provisioning data to Keychain
- Remove local mock data generation

---

### 8. **Architecture Mismatch: Certificate vs Token Flow** ❌

**Problem:**
The architecture documentation describes two different flows that are mixed incorrectly.

**Phase 1 Flow (Token-based - Raspberry Pi):**
```
Camera → Encrypted Token → Aggregator → SMA /validate
                                     (token + table refs)
```

**Phase 2 Flow (Certificate-based - iOS, SHOULD BE):**
```
Camera → Certificate Bundle → Aggregator /submit-cert → SMA /validate-cert
         (includes cert)                               (cert + image hash)
```

**Current iOS Implementation (BROKEN):**
```
iOS → Old Token Bundle → Aggregator /submit → SMA /validate
      (wrong format)     (wrong endpoint)     (wrong format)
```

**Impact:**
- iOS app uses wrong flow
- Mixed Phase 1 and Phase 2 concepts
- Incompatible with backend

**Fix Required:**
- Implement pure Phase 2 certificate-based flow for iOS
- Remove token-based submission code from iOS
- Ensure iOS uses `/submit-cert` endpoint

---

### 9. **Data Format Incompatibility: Table Indices** ❌

**Problem:**
iOS repeats single table/key 3 times, backend expects proper format.

**Current iOS Code:**
```swift
"table_references": [tableId, tableId, tableId],  // ❌ [157, 157, 157]
"key_indices": [keyIndex, keyIndex, keyIndex]     // ❌ [42, 42, 42]
```

**Phase 1 Expected (Raspberry Pi):**
```json
"table_references": [42, 157, 891],  // 3 different tables
"key_indices": [7, 99, 512]          // 3 different keys
```

**Phase 2 Expected (iOS - Certificate):**
- **No table_references/key_indices in CertificateBundle at all**
- This data is embedded in the certificate itself
- SMA extracts from certificate during validation

**Impact:**
- Invalid submission format if using old endpoint
- Doesn't match any expected format
- Will fail validation

**Fix Required:**
- Remove table_references/key_indices from iOS submissions
- Use CertificateBundle format (cert contains this data)
- Let SMA extract table/key info from certificate

---

## Missing Code Summary

### iOS App Missing Components

1. **NetworkService.swift:**
   - ❌ `provisionDevice()` method to call SMA
   - ❌ `submitCertificateBundle()` method for /submit-cert
   - ✅ Has queue management (can keep)

2. **KeychainService.swift:**
   - ❌ `saveDeviceCertificate()` / `getDeviceCertificate()`
   - ❌ `saveDevicePrivateKey()` / `getDevicePrivateKey()`
   - ❌ `saveCertificateChain()` / `getCertificateChain()`
   - ✅ Has device_secret, key_tables storage (good)

3. **CryptoService.swift:**
   - ❌ `signBundle()` method with ECDSA
   - ✅ Has device secret generation (good)

4. **AuthenticationService.swift:**
   - ❌ Create certificate bundle instead of token bundle
   - ❌ Sign bundle with private key
   - ❌ Submit to /submit-cert endpoint

5. **ProvisioningView.swift:**
   - ❌ Call SMA API for provisioning
   - ❌ Save certificate to Keychain
   - ❌ Remove mock data generation

6. **Models/CertificateBundle.swift:**
   - ❌ **COMPLETELY MISSING FILE**
   - Need new struct matching server schema

### Backend Missing/Issues

1. **SMA (`packages/sma/src/main.py`):**
   - ✅ Has `/api/v1/devices/provision` endpoint
   - ✅ Returns certificate in provisioning response
   - ✅ Has `/validate-cert` endpoint
   - ✅ Phase 2 validation logic implemented
   - **No issues found in SMA**

2. **Aggregation Server (`packages/blockchain/`):**
   - ✅ Has `/api/v1/submit-cert` endpoint
   - ✅ Has certificate validation logic
   - ✅ Calls SMA for validation
   - **No issues found in aggregation server**

---

## Recommended Fix Priority

### Priority 1: Critical (Blocks all submissions)

1. **Create CertificateBundle model in iOS**
   - File: `packages/mobile-app/BirthmarkCamera/BirthmarkCamera/Models/CertificateBundle.swift`
   - Match schema from `packages/blockchain/src/shared/models/schemas.py`

2. **Add certificate storage to KeychainService**
   - Add save/get methods for certificate, private key, chain

3. **Update NetworkService to call SMA for provisioning**
   - Add `provisionDevice()` method
   - Call SMA `/api/v1/devices/provision` endpoint

4. **Update ProvisioningView to use SMA**
   - Remove mock data generation
   - Call NetworkService.provisionDevice()
   - Save certificate to Keychain

### Priority 2: High (Blocks validation)

5. **Update NetworkService submission endpoint**
   - Change to `/api/v1/submit-cert`
   - Send CertificateBundle format

6. **Update AuthenticationService to create certificates**
   - Create CertificateBundle instead of AuthenticationBundle
   - Retrieve certificate from Keychain

7. **Implement proper bundle signing**
   - Add ECDSA signing to CryptoService
   - Sign with device private key

### Priority 3: Medium (Cleanup)

8. **Remove deprecated code**
   - Remove `AuthenticationBundle.toAPIFormat()`
   - Remove mock key table generation
   - Remove table_references/key_indices arrays

9. **Update error handling**
   - Add `missingCertificate` error
   - Add provisioning failure handling

---

## Testing Requirements

After fixes, test:

1. **Provisioning Flow:**
   - iOS calls SMA `/api/v1/devices/provision`
   - Receives certificate, private key, key tables
   - Saves all to Keychain
   - Can retrieve certificate

2. **Submission Flow:**
   - iOS creates CertificateBundle
   - Signs bundle with private key
   - Submits to `/api/v1/submit-cert`
   - Aggregation server validates certificate
   - SMA validates via `/validate-cert`
   - Submission succeeds

3. **Validation:**
   - SMA decrypts device_secret from certificate
   - Looks up device by secret
   - Checks blacklist
   - Logs submission
   - Returns PASS

---

## Impact Assessment

**Current State:** ❌ **BROKEN**
- iOS app cannot submit photos correctly
- Will fail at aggregation server
- Wrong data format
- Missing certificate

**After Fixes:** ✅ **WORKING**
- iOS provisions via SMA
- Receives and stores certificates
- Creates certificate-based bundles
- Submits to correct endpoint
- Validation succeeds

**Estimated Fix Time:** 4-6 hours

---

## Code Examples

### Example: iOS CertificateBundle (NEW FILE NEEDED)

```swift
// packages/mobile-app/BirthmarkCamera/BirthmarkCamera/Models/CertificateBundle.swift

import Foundation

struct CertificateBundle: Codable {
    let imageHash: String
    let cameraCert: String  // Base64-encoded DER certificate
    let timestamp: Int
    let gpsHash: String?
    let bundleSignature: String  // Base64-encoded ECDSA signature

    enum CodingKeys: String, CodingKey {
        case imageHash = "image_hash"
        case cameraCert = "camera_cert"
        case timestamp
        case gpsHash = "gps_hash"
        case bundleSignature = "bundle_signature"
    }
}
```

### Example: Provisioning via SMA

```swift
// In NetworkService.swift

func provisionDevice(deviceSecret: Data) async throws -> ProvisioningResponse {
    let smaURL = URL(string: "http://localhost:8001/api/v1/devices/provision")!
    var request = URLRequest(url: smaURL)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")

    let payload: [String: Any] = [
        "device_serial": UIDevice.current.identifierForVendor?.uuidString ?? UUID().uuidString,
        "device_family": "iOS",
        "device_secret": deviceSecret.hexString
    ]

    request.httpBody = try JSONSerialization.data(withJSONObject: payload)

    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(ProvisioningResponse.self, from: data)
}
```

---

**End of Report**
