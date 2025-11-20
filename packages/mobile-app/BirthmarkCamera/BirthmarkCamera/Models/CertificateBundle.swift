//
//  CertificateBundle.swift
//  BirthmarkCamera
//
//  Phase 2: Certificate-based submission bundle
//  Replaces AuthenticationBundle with self-contained certificate documents
//

import Foundation

/// Certificate-based submission bundle for Phase 2 architecture.
///
/// This bundle contains a self-contained camera certificate that includes:
/// - Encrypted device secret (replaces NUC hash)
/// - Key table assignments
/// - Device identity information
///
/// The certificate is validated by the SMA (Simulated Manufacturing Authority)
/// without the SMA ever seeing the image hash, preserving privacy.
struct CertificateBundle: Codable {
    /// SHA-256 hash of the captured image (64 hexadecimal characters)
    let imageHash: String

    /// Base64-encoded DER camera certificate
    /// Contains encrypted device_secret and key table information
    let cameraCert: String

    /// Optional: Base64-encoded DER software certificate (Phase 2)
    /// For apps that support modification tracking
    let softwareCert: String?

    /// Unix timestamp when photo was captured
    let timestamp: Int

    /// Optional: SHA-256 hash of GPS coordinates (64 hexadecimal characters)
    /// Format: SHA-256(latitude + longitude)
    let gpsHash: String?

    /// Base64-encoded ECDSA P-256 signature over the bundle
    /// Signed with device private key
    let bundleSignature: String

    enum CodingKeys: String, CodingKey {
        case imageHash = "image_hash"
        case cameraCert = "camera_cert"
        case softwareCert = "software_cert"
        case timestamp
        case gpsHash = "gps_hash"
        case bundleSignature = "bundle_signature"
    }

    /// Initialize a certificate bundle
    ///
    /// - Parameters:
    ///   - imageHash: SHA-256 hash of image (64 hex chars)
    ///   - cameraCert: Base64-encoded DER certificate
    ///   - timestamp: Unix timestamp
    ///   - gpsHash: Optional GPS hash
    ///   - bundleSignature: Base64-encoded ECDSA signature
    ///   - softwareCert: Optional software certificate
    init(
        imageHash: String,
        cameraCert: String,
        timestamp: Int,
        gpsHash: String? = nil,
        bundleSignature: String,
        softwareCert: String? = nil
    ) {
        self.imageHash = imageHash
        self.cameraCert = cameraCert
        self.softwareCert = softwareCert
        self.timestamp = timestamp
        self.gpsHash = gpsHash
        self.bundleSignature = bundleSignature
    }

    /// Convert to dictionary for API submission
    ///
    /// - Returns: Dictionary representation matching aggregator API schema
    func toAPIFormat() -> [String: Any] {
        var dict: [String: Any] = [
            "image_hash": imageHash,
            "camera_cert": cameraCert,
            "timestamp": timestamp,
            "bundle_signature": bundleSignature
        ]

        if let gpsHash = gpsHash {
            dict["gps_hash"] = gpsHash
        }

        if let softwareCert = softwareCert {
            dict["software_cert"] = softwareCert
        }

        return dict
    }

    /// Validate bundle format before submission
    ///
    /// - Throws: ValidationError if bundle is invalid
    func validate() throws {
        // Validate image hash format (64 hex characters)
        guard imageHash.count == 64,
              imageHash.range(of: "^[a-f0-9]{64}$", options: .regularExpression) != nil else {
            throw ValidationError.invalidImageHash
        }

        // Validate GPS hash format if present
        if let gpsHash = gpsHash {
            guard gpsHash.count == 64,
                  gpsHash.range(of: "^[a-f0-9]{64}$", options: .regularExpression) != nil else {
                throw ValidationError.invalidGPSHash
            }
        }

        // Validate timestamp is reasonable (not in future, not too old)
        let now = Int(Date().timeIntervalSince1970)
        guard timestamp <= now else {
            throw ValidationError.futureTimestamp
        }

        guard timestamp >= now - (86400 * 30) else { // 30 days
            throw ValidationError.timestampTooOld
        }

        // Validate base64 encoding of certificate
        guard Data(base64Encoded: cameraCert) != nil else {
            throw ValidationError.invalidCertificateEncoding
        }

        // Validate base64 encoding of signature
        guard Data(base64Encoded: bundleSignature) != nil else {
            throw ValidationError.invalidSignatureEncoding
        }

        // Validate software cert if present
        if let softwareCert = softwareCert {
            guard Data(base64Encoded: softwareCert) != nil else {
                throw ValidationError.invalidSoftwareCertEncoding
            }
        }
    }
}

// MARK: - Validation Errors

enum ValidationError: Error, LocalizedError {
    case invalidImageHash
    case invalidGPSHash
    case futureTimestamp
    case timestampTooOld
    case invalidCertificateEncoding
    case invalidSignatureEncoding
    case invalidSoftwareCertEncoding

    var errorDescription: String? {
        switch self {
        case .invalidImageHash:
            return "Image hash must be 64 hexadecimal characters"
        case .invalidGPSHash:
            return "GPS hash must be 64 hexadecimal characters"
        case .futureTimestamp:
            return "Timestamp cannot be in the future"
        case .timestampTooOld:
            return "Timestamp is too old (>30 days)"
        case .invalidCertificateEncoding:
            return "Camera certificate must be valid base64"
        case .invalidSignatureEncoding:
            return "Bundle signature must be valid base64"
        case .invalidSoftwareCertEncoding:
            return "Software certificate must be valid base64"
        }
    }
}
