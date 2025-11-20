//
//  NetworkService.swift
//  BirthmarkCamera
//
//  Network submission to aggregation server with offline queue
//

import Foundation

class NetworkService {
    static let shared = NetworkService()

    private let aggregatorURL: URL
    private let aggregatorCertURL: URL
    private let smaURL: URL
    private let queueKey = "com.birthmark.submission_queue"

    private init() {
        // TODO: Make this configurable in settings
        aggregatorURL = URL(string: "http://localhost:8545/api/v1/submit")!
        aggregatorCertURL = URL(string: "http://localhost:8545/api/v1/submit-cert")!
        smaURL = URL(string: "http://localhost:8001/api/v1/devices/provision")!
    }

    // MARK: - Submission

    /// Submit certificate bundle to aggregation server (Phase 2)
    ///
    /// This is the PRIMARY submission method for Phase 2 iOS app.
    /// Uses certificate-based authentication instead of encrypted tokens.
    ///
    /// - Parameter bundle: CertificateBundle with camera cert and signature
    /// - Returns: SubmissionResponse with receipt ID
    /// - Throws: NetworkError if submission fails
    func submitCertificateBundle(_ bundle: CertificateBundle) async throws -> SubmissionResponse {
        var request = URLRequest(url: aggregatorCertURL)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let jsonData = try JSONSerialization.data(withJSONObject: bundle.toAPIFormat())
        request.httpBody = jsonData

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw NetworkError.invalidResponse
        }

        guard httpResponse.statusCode == 202 else {
            throw NetworkError.serverError(httpResponse.statusCode)
        }

        let submissionResponse = try JSONDecoder().decode(SubmissionResponse.self, from: data)
        return submissionResponse
    }

    /// Submit authentication bundle to aggregation server (Phase 1 - DEPRECATED)
    ///
    /// This method is kept for backward compatibility with Phase 1 Raspberry Pi.
    /// iOS app should use submitCertificateBundle() instead.
    func submitBundle(_ bundle: AuthenticationBundle) async throws -> SubmissionResponse {
        var request = URLRequest(url: aggregatorURL)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let jsonData = try JSONSerialization.data(withJSONObject: bundle.toAPIFormat())
        request.httpBody = jsonData

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw NetworkError.invalidResponse
        }

        guard httpResponse.statusCode == 202 else {
            throw NetworkError.serverError(httpResponse.statusCode)
        }

        let submissionResponse = try JSONDecoder().decode(SubmissionResponse.self, from: data)
        return submissionResponse
    }

    // MARK: - Provisioning (Phase 2)

    /// Provision device with SMA (Simulated Manufacturing Authority)
    ///
    /// This method contacts the SMA to provision the device and receive:
    /// - Device certificate (contains encrypted device_secret)
    /// - Device private key (for signing bundles)
    /// - Certificate chain (for validation)
    /// - Key tables (3 tables of 1000 keys each)
    /// - Key table indices (global indices for the assigned tables)
    ///
    /// - Parameter deviceSecret: The device secret generated during provisioning
    /// - Returns: ProvisioningResponse containing all credentials
    /// - Throws: NetworkError if provisioning fails
    func provisionDevice(deviceSecret: Data) async throws -> ProvisioningResponse {
        var request = URLRequest(url: smaURL)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Create payload
        let payload: [String: Any] = [
            "device_serial": UIDevice.current.identifierForVendor?.uuidString ?? UUID().uuidString,
            "device_family": "iOS",
            "device_secret": deviceSecret.hexString
        ]

        let jsonData = try JSONSerialization.data(withJSONObject: payload)
        request.httpBody = jsonData

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw NetworkError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw NetworkError.serverError(httpResponse.statusCode)
        }

        let provisioningResponse = try JSONDecoder().decode(ProvisioningResponse.self, from: data)
        return provisioningResponse
    }

    // MARK: - Queue Management

    /// Add bundle to offline queue
    func queueBundle(_ bundle: AuthenticationBundle) {
        var queue = loadQueue()
        let queued = QueuedSubmission(
            id: UUID(),
            bundle: bundle,
            createdAt: Date(),
            attemptCount: 0,
            lastAttempt: nil
        )
        queue.append(queued)
        saveQueue(queue)
    }

    /// Process queued submissions
    func processQueue() async {
        var queue = loadQueue()
        var successfulIds: [UUID] = []

        for var submission in queue {
            // Skip if attempted too many times
            guard submission.attemptCount < 5 else { continue }

            submission.attemptCount += 1
            submission.lastAttempt = Date()

            do {
                _ = try await submitBundle(submission.bundle)
                successfulIds.append(submission.id)
                print("Successfully submitted queued bundle \(submission.id)")
            } catch {
                print("Failed to submit queued bundle \(submission.id): \(error)")
            }

            // Update queue after each attempt
            if let index = queue.firstIndex(where: { $0.id == submission.id }) {
                queue[index] = submission
            }
            saveQueue(queue)

            // Wait between requests
            try? await Task.sleep(nanoseconds: 1_000_000_000) // 1 second
        }

        // Remove successful submissions
        queue.removeAll { successfulIds.contains($0.id) }
        saveQueue(queue)
    }

    func getQueueCount() -> Int {
        return loadQueue().count
    }

    func clearQueue() {
        saveQueue([])
    }

    // MARK: - Persistence

    private func loadQueue() -> [QueuedSubmission] {
        guard let data = UserDefaults.standard.data(forKey: queueKey) else {
            return []
        }

        do {
            return try JSONDecoder().decode([QueuedSubmission].self, from: data)
        } catch {
            print("Failed to decode queue: \(error)")
            return []
        }
    }

    private func saveQueue(_ queue: [QueuedSubmission]) {
        do {
            let data = try JSONEncoder().encode(queue)
            UserDefaults.standard.set(data, forKey: queueKey)
        } catch {
            print("Failed to encode queue: \(error)")
        }
    }
}

enum NetworkError: Error {
    case invalidResponse
    case serverError(Int)
    case encodingFailed
    case provisioningFailed
    case missingCredentials
}

// MARK: - Response Models

/// Response from SMA provisioning endpoint
struct ProvisioningResponse: Codable {
    /// Device certificate (PEM or base64-encoded DER)
    /// Contains encrypted device_secret and key table assignments
    let deviceCertificate: String

    /// Device private key (PEM-encoded ECDSA P-256)
    /// Used to sign certificate bundles before submission
    let devicePrivateKey: String

    /// Certificate chain (PEM-encoded)
    /// Intermediate + root CA certificates for validation
    let certificateChain: String

    /// Key tables (3 arrays of 1000 hex-encoded keys each)
    /// Each key is 32 bytes, represented as 64-character hex string
    let keyTables: [[String]]

    /// Global key table indices (e.g., [42, 157, 891])
    /// Maps local indices (0-2) to global table IDs (0-2499)
    let keyTableIndices: [Int]

    /// Device secret (hex-encoded SHA-256 hash)
    /// Echo back from server for verification
    let deviceSecret: String

    enum CodingKeys: String, CodingKey {
        case deviceCertificate = "device_certificate"
        case devicePrivateKey = "device_private_key"
        case certificateChain = "certificate_chain"
        case keyTables = "key_tables"
        case keyTableIndices = "key_table_indices"
        case deviceSecret = "device_secret"
    }
}
