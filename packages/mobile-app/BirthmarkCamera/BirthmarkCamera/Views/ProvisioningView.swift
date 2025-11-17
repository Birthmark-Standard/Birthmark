//
//  ProvisioningView.swift
//  BirthmarkCamera
//
//  First-launch provisioning to generate device fingerprint
//

import SwiftUI

struct ProvisioningView: View {
    @EnvironmentObject var appState: AppState
    @State private var isProvisioning = false
    @State private var errorMessage: String?

    var body: some View {
        VStack(spacing: 30) {
            Spacer()

            // Logo/Icon
            Image(systemName: "checkmark.seal.fill")
                .font(.system(size: 80))
                .foregroundColor(.blue)

            // Title
            Text("Birthmark Camera")
                .font(.largeTitle)
                .fontWeight(.bold)

            Text("Photo Authentication for iOS")
                .font(.subheadline)
                .foregroundColor(.secondary)

            Spacer()

            // Info box
            VStack(alignment: .leading, spacing: 12) {
                InfoRow(icon: "camera", text: "Authenticates every photo you take")
                InfoRow(icon: "lock.shield", text: "Device fingerprint stored securely")
                InfoRow(icon: "cloud.fill", text: "Submits hashes to blockchain")
                InfoRow(icon: "eye.slash", text: "Your photos never leave your device")
            }
            .padding()
            .background(Color(.systemGray6))
            .cornerRadius(12)
            .padding(.horizontal)

            Spacer()

            // Error message
            if let errorMessage = errorMessage {
                Text(errorMessage)
                    .font(.caption)
                    .foregroundColor(.red)
                    .padding(.horizontal)
            }

            // Setup button
            Button(action: startProvisioning) {
                if isProvisioning {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        .frame(maxWidth: .infinity)
                        .frame(height: 50)
                } else {
                    Text("Get Started")
                        .fontWeight(.semibold)
                        .frame(maxWidth: .infinity)
                        .frame(height: 50)
                }
            }
            .background(Color.blue)
            .foregroundColor(.white)
            .cornerRadius(12)
            .padding(.horizontal)
            .disabled(isProvisioning)

            Text("Phase 2 TestFlight Beta")
                .font(.caption2)
                .foregroundColor(.secondary)
                .padding(.bottom)
        }
    }

    private func startProvisioning() {
        isProvisioning = true
        errorMessage = nil

        Task {
            do {
                try await performProvisioning()

                DispatchQueue.main.async {
                    isProvisioning = false
                }
            } catch {
                DispatchQueue.main.async {
                    isProvisioning = false
                    errorMessage = "Provisioning failed: \(error.localizedDescription)"
                }
            }
        }
    }

    private func performProvisioning() async throws {
        // 1. Generate device fingerprint
        let fingerprint = CryptoService.shared.generateDeviceFingerprint()
        print("Generated fingerprint: \(fingerprint.prefix(16))...")

        // 2. For demo purposes, assign random tables locally
        // In production, this would come from SMA
        let tableAssignments = generateRandomTableAssignments()
        print("Assigned tables: \(tableAssignments)")

        // 3. Generate mock master keys for each table
        // In production, these would come from SMA
        for tableId in tableAssignments {
            let masterKey = generateMockMasterKey()
            KeychainService.shared.saveMasterKey(masterKey, forTable: tableId)
        }

        // 4. Save fingerprint and assignments
        DispatchQueue.main.async {
            appState.completeProvisioning(
                fingerprint: fingerprint,
                assignments: tableAssignments
            )
        }
    }

    private func generateRandomTableAssignments() -> [Int] {
        // Select 3 random tables from 0-2499
        var assignments: Set<Int> = []
        while assignments.count < 3 {
            assignments.insert(Int.random(in: 0..<2500))
        }
        return Array(assignments).sorted()
    }

    private func generateMockMasterKey() -> Data {
        // Generate random 256-bit key
        var bytes = [UInt8](repeating: 0, count: 32)
        _ = SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes)
        return Data(bytes)
    }
}

struct InfoRow: View {
    let icon: String
    let text: String

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 20))
                .foregroundColor(.blue)
                .frame(width: 30)

            Text(text)
                .font(.subheadline)

            Spacer()
        }
    }
}

struct ProvisioningView_Previews: PreviewProvider {
    static var previews: some View {
        ProvisioningView()
            .environmentObject(AppState())
    }
}
