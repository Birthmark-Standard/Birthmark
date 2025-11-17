//
//  AuthenticationService.swift
//  BirthmarkCamera
//
//  Orchestrates the complete authentication flow
//

import Foundation

class AuthenticationService {
    static let shared = AuthenticationService()

    private init() {}

    /// Complete authentication flow: hash, encrypt, create bundle, submit
    func authenticateImage(_ imageData: Data) async throws -> SubmissionResponse {
        let startTime = Date()

        // 1. Compute SHA-256 hash (~10ms)
        let imageHash = CryptoService.shared.sha256(imageData)
        print("Image hash computed: \(imageHash.prefix(16))...")

        // 2. Get device fingerprint from Keychain
        guard let fingerprint = KeychainService.shared.getDeviceFingerprint() else {
            throw AuthError.notProvisioned
        }

        // 3. Get table assignments
        guard let assignments = KeychainService.shared.getTableAssignments() else {
            throw AuthError.notProvisioned
        }

        // 4. Select random table and key index
        let tableId = CryptoService.shared.selectRandomTable(from: assignments)
        let keyIndex = CryptoService.shared.generateRandomKeyIndex()

        // 5. Get master key for selected table
        guard let masterKey = KeychainService.shared.getMasterKey(forTable: tableId) else {
            throw AuthError.missingKey
        }

        // 6. Derive encryption key (~1ms)
        let derivedKey = CryptoService.shared.deriveKey(
            masterKey: masterKey,
            keyIndex: keyIndex,
            tableId: tableId
        )

        // 7. Encrypt device fingerprint (~1ms)
        let cameraToken = try CryptoService.shared.encryptFingerprint(
            fingerprint,
            key: derivedKey
        )

        // 8. Create authentication bundle
        let bundle = AuthenticationBundle(
            imageHash: imageHash,
            cameraToken: cameraToken,
            tableId: tableId,
            keyIndex: keyIndex,
            timestamp: Int(Date().timeIntervalSince1970),
            gpsHash: nil // TODO: Add GPS hashing if desired
        )

        let elapsed = Date().timeIntervalSince(startTime) * 1000
        print("Authentication bundle created in \(String(format: "%.1f", elapsed))ms")

        // 9. Submit to aggregation server (or queue if offline)
        do {
            let response = try await NetworkService.shared.submitBundle(bundle)
            print("Submission successful: \(response.receiptId)")
            return response
        } catch {
            print("Network error, queueing for later: \(error)")
            NetworkService.shared.queueBundle(bundle)

            // Return synthetic response
            return SubmissionResponse(
                receiptId: UUID().uuidString,
                status: "queued",
                message: "Queued for submission when online"
            )
        }
    }

    /// Background task to process queued submissions
    func processQueuedSubmissions() async {
        await NetworkService.shared.processQueue()
    }
}

enum AuthError: Error {
    case notProvisioned
    case missingKey
    case encryptionFailed
    case submissionFailed
}
