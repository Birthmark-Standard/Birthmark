//
//  AuthenticationBundle.swift
//  BirthmarkCamera
//
//  Data models for authentication submission
//

import Foundation

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

    /// Convert to API format (different from the Phase 1 format)
    func toAPIFormat() -> [String: Any] {
        var dict: [String: Any] = [
            "image_hash": imageHash,
            "encrypted_nuc_token": cameraToken.ciphertext.base64EncodedString(),
            "table_references": [tableId, tableId, tableId], // iOS uses single table, repeat 3x for compatibility
            "key_indices": [keyIndex, keyIndex, keyIndex], // iOS uses single key, repeat 3x
            "timestamp": timestamp,
            "device_signature": Data().base64EncodedString() // Placeholder for now
        ]

        if let gpsHash = gpsHash {
            dict["gps_hash"] = gpsHash
        }

        return dict
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
