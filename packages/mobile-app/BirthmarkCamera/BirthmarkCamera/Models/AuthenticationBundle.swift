//
//  AuthenticationBundle.swift
//  BirthmarkCamera
//
//  Data models for authentication submission
//

import Foundation
import CryptoKit

/// Authentication bundle sent to aggregation server
struct AuthenticationBundle: Codable {
    let imageHash: String
    let cameraToken: CameraToken
    let tableId: Int
    let keyIndex: Int
    let timestamp: Int
    let gpsHash: String?

    enum CodingKeys: String, CodingKey {
        case imageHash = "image_hash"
        case cameraToken = "camera_token"
        case tableId = "table_id"
        case keyIndex = "key_index"
        case timestamp
        case gpsHash = "gps_hash"
    }

    /// Convert to API format for aggregation server
    func toAPIFormat() -> [String: Any] {
        var dict: [String: Any] = [
            "image_hash": imageHash,
            "encrypted_nuc_token": cameraToken.toSealedBoxData().base64EncodedString(),
            "table_references": [tableId, tableId, tableId], // iOS uses single table, repeat 3x for compatibility
            "key_indices": [keyIndex, keyIndex, keyIndex], // iOS uses single key, repeat 3x
            "timestamp": timestamp,
            "device_signature": createBundleSignature().base64EncodedString()
        ]

        if let gpsHash = gpsHash {
            dict["gps_hash"] = gpsHash
        }

        return dict
    }

    /// Create signature over bundle data
    /// For Phase 2 demo: simple hash-based signature (not cryptographically secure)
    /// Production should use ECDSA with device's private key
    private func createBundleSignature() -> Data {
        // Concatenate bundle fields for signing
        let signatureInput = imageHash +
                           cameraToken.toSealedBoxData().base64EncodedString() +
                           "\(tableId)\(keyIndex)\(timestamp)"

        guard let data = signatureInput.data(using: .utf8) else {
            return Data()
        }

        // Use SHA-256 as mock signature for Phase 2
        // TODO Phase 3: Replace with ECDSA signature using device private key
        let hash = SHA256.hash(data: data)
        return Data(hash)
    }
}

/// Encrypted camera token (device fingerprint)
struct CameraToken: Codable {
    let ciphertext: Data
    let authTag: Data
    let nonce: Data

    enum CodingKeys: String, CodingKey {
        case ciphertext
        case authTag = "auth_tag"
        case nonce
    }

    /// Combine into standard AES-GCM sealed box format: nonce + ciphertext + tag
    /// This is the format expected by the aggregation server
    func toSealedBoxData() -> Data {
        var combined = Data()
        combined.append(nonce)        // 12 bytes
        combined.append(ciphertext)   // variable length (fingerprint size)
        combined.append(authTag)      // 16 bytes
        return combined
    }
}

/// Response from aggregation server
struct SubmissionResponse: Codable {
    let receiptId: String
    let status: String
    let message: String

    enum CodingKeys: String, CodingKey {
        case receiptId = "receipt_id"
        case status
        case message
    }
}

/// Queued submission for offline mode
struct QueuedSubmission: Codable {
    let id: UUID
    let bundle: AuthenticationBundle
    let createdAt: Date
    var attemptCount: Int
    var lastAttempt: Date?
}
