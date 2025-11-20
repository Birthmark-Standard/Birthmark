//
//  CryptoService.swift
//  BirthmarkCamera
//
//  Cryptographic operations: SHA-256, HKDF, AES-GCM
//

import Foundation
import CryptoKit
import UIKit

class CryptoService {
    static let shared = CryptoService()

    private init() {}

    // MARK: - Device Secret Generation (Phase 2)

    /// Generate device secret (frozen at provisioning time)
    ///
    /// Phase 2 Architecture:
    /// 1. Generate random seed (32 bytes)
    /// 2. Get device name
    /// 3. Hash: device_secret = SHA256(random_seed + device_name)
    /// 4. Store ONLY device_secret in Keychain
    /// 5. DISCARD random_seed and device_name (never stored)
    ///
    /// Critical: device_secret remains unchanged even if device name changes later
    func generateDeviceSecret() -> Data {
        // Step 1: Generate random seed (32 bytes)
        var randomBytes = [UInt8](repeating: 0, count: 32)
        let status = SecRandomCopyBytes(kSecRandomDefault, 32, &randomBytes)
        guard status == errSecSuccess else {
            fatalError("Failed to generate random bytes")
        }
        let randomSeed = Data(randomBytes)

        // Step 2: Get device name
        let deviceName = UIDevice.current.name

        // Step 3: Create device secret (PERMANENT)
        var combined = Data()
        combined.append(randomSeed)
        combined.append(deviceName.data(using: .utf8)!)

        let deviceSecret = SHA256.hash(data: combined)

        // Step 4: random_seed and device_name are now discarded (function scope ends)
        // Only device_secret (return value) will be stored in Keychain

        return Data(deviceSecret)
    }

    /// Generate unique device fingerprint on first launch (Phase 1 backward compatibility)
    func generateDeviceFingerprint() -> String {
        // Use device ID + random seed + standard prefix
        let deviceId = UIDevice.current.identifierForVendor?.uuidString ?? UUID().uuidString
        let randomSeed = UUID().uuidString
        let input = deviceId + randomSeed + "Birthmark-Standard-iOS-v1"

        return sha256(input)
    }

    // MARK: - SHA-256 Hashing

    /// Compute SHA-256 hash of image data
    func sha256(_ data: Data) -> String {
        let hash = SHA256.hash(data: data)
        return hash.compactMap { String(format: "%02x", $0) }.joined()
    }

    /// Compute SHA-256 hash of string
    func sha256(_ string: String) -> String {
        guard let data = string.data(using: .utf8) else { return "" }
        return sha256(data)
    }

    // MARK: - Key Derivation (HKDF)

    /// Derive encryption key from master key using HKDF
    /// - Parameters:
    ///   - masterKey: 256-bit master key for table
    ///   - keyIndex: Key index (0-999)
    ///   - tableId: Table ID for info string
    /// - Returns: Derived 256-bit key
    func deriveKey(masterKey: Data, keyIndex: Int, tableId: Int) -> SymmetricKey {
        let salt = Data() // Empty salt (SMA uses same)
        let info = "Birthmark\(keyIndex)".data(using: .utf8)!

        let derivedKey = HKDF<SHA256>.deriveKey(
            inputKeyMaterial: SymmetricKey(data: masterKey),
            salt: salt,
            info: info,
            outputByteCount: 32 // 256 bits
        )

        return derivedKey
    }

    // MARK: - AES-GCM Encryption

    /// Encrypt device fingerprint with derived key
    /// - Parameters:
    ///   - fingerprint: Device fingerprint string
    ///   - key: Derived symmetric key
    /// - Returns: Camera token with ciphertext, auth tag, and nonce
    func encryptFingerprint(_ fingerprint: String, key: SymmetricKey) throws -> CameraToken {
        guard let data = fingerprint.data(using: .utf8) else {
            throw CryptoError.invalidInput
        }

        // Generate random nonce
        let nonce = AES.GCM.Nonce()

        // Encrypt
        let sealedBox = try AES.GCM.seal(data, using: key, nonce: nonce)

        guard let ciphertext = sealedBox.ciphertext,
              let tag = sealedBox.tag else {
            throw CryptoError.encryptionFailed
        }

        return CameraToken(
            ciphertext: Data(ciphertext),
            authTag: Data(tag),
            nonce: Data(nonce)
        )
    }

    // MARK: - Random Selection

    /// Select random table from assignments
    func selectRandomTable(from assignments: [Int]) -> Int {
        return assignments.randomElement() ?? 0
    }

    /// Generate random key index (0-999)
    func generateRandomKeyIndex() -> Int {
        return Int.random(in: 0..<1000)
    }

    // MARK: - ECDSA Signing (Phase 2)

    /// Sign certificate bundle with device private key (ECDSA P-256)
    ///
    /// Creates a canonical representation of the bundle and signs it with the
    /// device private key received during provisioning.
    ///
    /// Canonical bundle format (signed data):
    /// - image_hash (64 hex chars, lowercase)
    /// - camera_cert (base64 string)
    /// - timestamp (string representation)
    /// - gps_hash (64 hex chars or empty string)
    ///
    /// - Parameters:
    ///   - imageHash: SHA-256 image hash (64 hex chars)
    ///   - cameraCert: Base64-encoded camera certificate
    ///   - timestamp: Unix timestamp
    ///   - gpsHash: Optional GPS hash
    /// - Returns: Base64-encoded ECDSA signature
    /// - Throws: CryptoError if signing fails
    func signCertificateBundle(
        imageHash: String,
        cameraCert: String,
        timestamp: Int,
        gpsHash: String?
    ) throws -> String {
        // 1. Get device private key from Keychain
        guard let privateKeyPEM = KeychainService.shared.getDevicePrivateKey() else {
            throw CryptoError.missingPrivateKey
        }

        // 2. Parse PEM private key to P256.Signing.PrivateKey
        let privateKey = try parsePrivateKey(pem: privateKeyPEM)

        // 3. Create canonical bundle data
        let bundleData = createCanonicalBundleData(
            imageHash: imageHash,
            cameraCert: cameraCert,
            timestamp: timestamp,
            gpsHash: gpsHash
        )

        // 4. Sign with ECDSA P-256
        let signature = try privateKey.signature(for: bundleData)

        // 5. Return base64-encoded signature
        return signature.rawRepresentation.base64EncodedString()
    }

    /// Create canonical bundle data for signing
    ///
    /// Format: Concatenate fields in order with newlines
    /// This ensures consistent signing across all implementations
    private func createCanonicalBundleData(
        imageHash: String,
        cameraCert: String,
        timestamp: Int,
        gpsHash: String?
    ) -> Data {
        var canonical = ""
        canonical += imageHash.lowercased() + "\n"
        canonical += cameraCert + "\n"
        canonical += String(timestamp) + "\n"
        canonical += (gpsHash?.lowercased() ?? "") + "\n"

        return canonical.data(using: .utf8)!
    }

    /// Parse PEM-encoded private key to P256.Signing.PrivateKey
    ///
    /// Handles PEM format from SMA provisioning response
    private func parsePrivateKey(pem: String) throws -> P256.Signing.PrivateKey {
        // Try parsing as PEM
        do {
            return try P256.Signing.PrivateKey(pemRepresentation: pem)
        } catch {
            // If PEM fails, try parsing as raw DER (base64-decoded)
            // Some implementations may send base64-encoded DER instead of PEM
            if let derData = Data(base64Encoded: pem) {
                do {
                    return try P256.Signing.PrivateKey(derRepresentation: derData)
                } catch {
                    throw CryptoError.invalidPrivateKey
                }
            }
            throw CryptoError.invalidPrivateKey
        }
    }

    /// Verify bundle signature (for testing)
    ///
    /// - Parameters:
    ///   - signature: Base64-encoded signature
    ///   - imageHash: Image hash that was signed
    ///   - cameraCert: Certificate that was signed
    ///   - timestamp: Timestamp that was signed
    ///   - gpsHash: GPS hash that was signed
    ///   - publicKeyPEM: PEM-encoded public key
    /// - Returns: true if signature is valid
    func verifyCertificateBundleSignature(
        signature: String,
        imageHash: String,
        cameraCert: String,
        timestamp: Int,
        gpsHash: String?,
        publicKeyPEM: String
    ) throws -> Bool {
        // Parse public key
        let publicKey = try P256.Signing.PublicKey(pemRepresentation: publicKeyPEM)

        // Recreate canonical bundle data
        let bundleData = createCanonicalBundleData(
            imageHash: imageHash,
            cameraCert: cameraCert,
            timestamp: timestamp,
            gpsHash: gpsHash
        )

        // Decode signature
        guard let signatureData = Data(base64Encoded: signature) else {
            throw CryptoError.invalidSignature
        }

        let ecdsaSignature = try P256.Signing.ECDSASignature(rawRepresentation: signatureData)

        // Verify
        return publicKey.isValidSignature(ecdsaSignature, for: bundleData)
    }
}

enum CryptoError: Error {
    case invalidInput
    case encryptionFailed
    case keyDerivationFailed
    case missingPrivateKey
    case invalidPrivateKey
    case invalidSignature
    case signingFailed
}
