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
    private let queueKey = "com.birthmark.submission_queue"

    private init() {
        // TODO: Make this configurable in settings
        aggregatorURL = URL(string: "http://localhost:8545/api/v1/submit")!
    }

    // MARK: - Submission

    /// Submit authentication bundle to aggregation server
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
}
