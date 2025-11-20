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
        print("[Phase 2] Starting provisioning...")

        // 1. Generate device secret (Phase 2)
        let deviceSecret = CryptoService.shared.generateDeviceSecret()
        print("[Phase 2] Generated device secret: \(deviceSecret.hexString.prefix(16))...")

        // 2. Assign random global table indices (Phase 2)
        // In production, this would come from SMA
        let keyTableIndices = generateRandomTableAssignments()
        print("[Phase 2] Assigned global table indices: \(keyTableIndices)")

        // 3. Generate mock key tables (Phase 2)
        // In production, these would come from SMA
        let keyTables = generateMockKeyTables()
        print("[Phase 2] Generated 3 key tables with 1000 keys each")

        // 4. Save Phase 2 data to Keychain
        KeychainService.shared.saveDeviceSecret(deviceSecret)
        KeychainService.shared.saveKeyTableIndices(keyTableIndices)
        KeychainService.shared.saveKeyTables(keyTables)

        // Backward compatibility: Save old format too
        let fingerprintString = deviceSecret.hexString
        KeychainService.shared.saveDeviceFingerprint(fingerprintString)
        KeychainService.shared.saveTableAssignments(keyTableIndices)

        print("[Phase 2] Provisioning complete")

        // 5. Mark app as provisioned
        DispatchQueue.main.async {
            appState.completeProvisioning(
                fingerprint: fingerprintString,
                assignments: keyTableIndices
            )
        }
    }

    private func generateMockKeyTables() -> [[String]] {
        // Generate 3 tables with 1000 keys each
        var tables: [[String]] = []

        for _ in 0..<3 {
            var table: [String] = []
            for _ in 0..<1000 {
                let key = generateMockMasterKey()
                table.append(key.hexString)
            }
            tables.append(table)
        }

        return tables
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
