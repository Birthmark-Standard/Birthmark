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

    // MARK: - Device Fingerprint Generation

    /// Generate unique device fingerprint on first launch
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
}

enum CryptoError: Error {
    case invalidInput
    case encryptionFailed
    case keyDerivationFailed
}
