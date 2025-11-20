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

    /// Complete authentication flow: hash, encrypt, create bundle, submit (Phase 2)
    func authenticateImage(_ imageData: Data) async throws -> SubmissionResponse {
        let startTime = Date()

        // 1. Compute SHA-256 hash (~10ms)
        let imageHash = CryptoService.shared.sha256(imageData)
        print("Image hash computed: \(imageHash.prefix(16))...")

        // 2. Get device secret from Keychain (Phase 2)
        guard let deviceSecret = KeychainService.shared.getDeviceSecret() else {
            // Fallback to Phase 1 fingerprint
            guard let fingerprint = KeychainService.shared.getDeviceFingerprint() else {
                throw AuthError.notProvisioned
            }
            return try await authenticateImagePhase1(imageData, fingerprint: fingerprint)
        }

        // 3. Get key table indices (global indices)
        guard let keyTableIndices = KeychainService.shared.getKeyTableIndices() else {
            throw AuthError.notProvisioned
        }

        // 4. Select random table (local index 0-2)
        let localTableIndex = Int.random(in: 0..<3)
        let globalTableIndex = keyTableIndices[localTableIndex]  // Map to global index

        // 5. Select random key index (0-999)
        let keyIndex = CryptoService.shared.generateRandomKeyIndex()

        // 6. Get encryption key directly from key tables (Phase 2)
        guard let encryptionKey = KeychainService.shared.getKey(
            localTableIndex: localTableIndex,
            keyIndex: keyIndex
        ) else {
            throw AuthError.missingKey
        }

        // 7. Encrypt device secret (~1ms)
        let deviceSecretString = deviceSecret.hexString
        let cameraToken = try CryptoService.shared.encryptFingerprint(
            deviceSecretString,
            key: SymmetricKey(data: encryptionKey)
        )

        // 8. Create authentication bundle with global table index
        let bundle = AuthenticationBundle(
            imageHash: imageHash,
            cameraToken: cameraToken,
            tableId: globalTableIndex,  // Use GLOBAL index (e.g., 157)
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
    case encryptionFailed
    case submissionFailed
}
