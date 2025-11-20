//
//  AuthenticationService.swift
//  BirthmarkCamera
//
//  Orchestrates the complete authentication flow
//

import Foundation
import CryptoKit

class AuthenticationService {
    static let shared = AuthenticationService()

    private init() {}

    /// Complete authentication flow: hash, create certificate bundle, sign, submit (Phase 2)
    func authenticateImage(_ imageData: Data) async throws -> SubmissionResponse {
        let startTime = Date()

        // 1. Compute SHA-256 hash (~10ms)
        let imageHash = CryptoService.shared.sha256(imageData)
        print("[Phase 2] Image hash computed: \(imageHash.prefix(16))...")

        // 2. Check if device is fully provisioned with certificate
        guard KeychainService.shared.isFullyProvisioned() else {
            print("[Phase 2] Device not fully provisioned, checking Phase 1 fallback...")
            // Fallback to Phase 1 token-based authentication
            guard let fingerprint = KeychainService.shared.getDeviceFingerprint() else {
                throw AuthError.notProvisioned
            }
            return try await authenticateImagePhase1(imageData, fingerprint: fingerprint)
        }

        // 3. Get device certificate from Keychain
        guard let deviceCertificate = KeychainService.shared.getDeviceCertificate() else {
            throw AuthError.missingCertificate
        }
        print("[Phase 2] Retrieved device certificate")

        // 4. Create timestamp
        let timestamp = Int(Date().timeIntervalSince1970)

        // 5. Get optional GPS hash (if location services enabled)
        let gpsHash: String? = nil // TODO: Implement GPS hashing if location available

        // 6. Sign bundle with device private key (ECDSA P-256)
        print("[Phase 2] Signing certificate bundle...")
        let bundleSignature = try CryptoService.shared.signCertificateBundle(
            imageHash: imageHash,
            cameraCert: deviceCertificate,
            timestamp: timestamp,
            gpsHash: gpsHash
        )
        print("[Phase 2] Bundle signed with ECDSA P-256")

        // 7. Create certificate bundle (Phase 2 format)
        let bundle = CertificateBundle(
            imageHash: imageHash,
            cameraCert: deviceCertificate,
            timestamp: timestamp,
            gpsHash: gpsHash,
            bundleSignature: bundleSignature,
            softwareCert: nil // Phase 2: No software cert yet
        )

        // 8. Validate bundle format before submission
        try bundle.validate()

        let elapsed = Date().timeIntervalSince(startTime) * 1000
        print("[Phase 2] Certificate bundle created in \(String(format: "%.1f", elapsed))ms")

        // 9. Submit to aggregation server /api/v1/submit-cert endpoint
        do {
            let response = try await NetworkService.shared.submitCertificateBundle(bundle)
            print("[Phase 2] Submission successful: \(response.receiptId)")
            return response
        } catch {
            print("[Phase 2] Network error, queueing for later: \(error)")
            // TODO: Implement certificate bundle queue (currently only supports AuthenticationBundle)
            // For now, return error to user
            throw AuthError.submissionFailed
        }
    }

    /// Background task to process queued submissions
    func processQueuedSubmissions() async {
        await NetworkService.shared.processQueue()
    }

    // MARK: - Phase 1 Fallback

    /// Phase 1 authentication (for backward compatibility)
    private func authenticateImagePhase1(_ imageData: Data, fingerprint: String) async throws -> SubmissionResponse {
        let startTime = Date()

        // 1. Compute SHA-256 hash
        let imageHash = CryptoService.shared.sha256(imageData)
        print("[Phase 1] Image hash computed: \(imageHash.prefix(16))...")

        // 2. Get table assignments
        guard let assignments = KeychainService.shared.getTableAssignments() else {
            throw AuthError.notProvisioned
        }

        // 3. Select random table and key index
        let tableId = CryptoService.shared.selectRandomTable(from: assignments)
        let keyIndex = CryptoService.shared.generateRandomKeyIndex()

        // 4. Get master key for selected table
        guard let masterKey = KeychainService.shared.getMasterKey(forTable: tableId) else {
            throw AuthError.missingKey
        }

        // 5. Derive encryption key
        let derivedKey = CryptoService.shared.deriveKey(
            masterKey: masterKey,
            keyIndex: keyIndex,
            tableId: tableId
        )

        // 6. Encrypt device fingerprint
        let cameraToken = try CryptoService.shared.encryptFingerprint(
            fingerprint,
            key: derivedKey
        )

        // 7. Create authentication bundle
        let bundle = AuthenticationBundle(
            imageHash: imageHash,
            cameraToken: cameraToken,
            tableId: tableId,
            keyIndex: keyIndex,
            timestamp: Int(Date().timeIntervalSince1970),
            gpsHash: nil
        )

        let elapsed = Date().timeIntervalSince(startTime) * 1000
        print("[Phase 1] Authentication bundle created in \(String(format: "%.1f", elapsed))ms")

        // 8. Submit
        do {
            let response = try await NetworkService.shared.submitBundle(bundle)
            print("[Phase 1] Submission successful: \(response.receiptId)")
            return response
        } catch {
            print("[Phase 1] Network error, queueing: \(error)")
            NetworkService.shared.queueBundle(bundle)
            return SubmissionResponse(
                receiptId: UUID().uuidString,
                status: "queued",
                message: "Queued for submission when online"
            )
        }
    }
}

enum AuthError: Error {
    case notProvisioned
    case missingKey
    case missingCertificate
    case encryptionFailed
    case submissionFailed
    case signingFailed
}
