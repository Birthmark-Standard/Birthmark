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
        print("[Phase 2] Starting provisioning with SMA...")

        // 1. Generate device secret (Phase 2)
        // This is a permanent, frozen identity: SHA256(random_seed + device_name)
        let deviceSecret = CryptoService.shared.generateDeviceSecret()
        print("[Phase 2] Generated device secret: \(deviceSecret.hexString.prefix(16))...")

        // 2. Call SMA API for provisioning
        // This replaces all mock data generation with real server call
        print("[Phase 2] Calling SMA /api/v1/devices/provision...")
        let response = try await NetworkService.shared.provisionDevice(deviceSecret: deviceSecret)
        print("[Phase 2] Received provisioning response from SMA")
        print("[Phase 2] - Global table indices: \(response.keyTableIndices)")
        print("[Phase 2] - Key tables: 3 tables × 1000 keys")
        print("[Phase 2] - Certificate received: \(response.deviceCertificate.prefix(50))...")

        // 3. Verify response matches our device secret
        guard response.deviceSecret == deviceSecret.hexString else {
            throw ProvisioningError.secretMismatch
        }
        print("[Phase 2] Device secret verified")

        // 4. Save ALL provisioning data to Keychain
        print("[Phase 2] Saving credentials to Keychain...")

        // Certificate credentials
        KeychainService.shared.saveDeviceCertificate(response.deviceCertificate)
        KeychainService.shared.saveDevicePrivateKey(response.devicePrivateKey)
        KeychainService.shared.saveCertificateChain(response.certificateChain)

        // Device identity and keys
        KeychainService.shared.saveDeviceSecret(deviceSecret)
        KeychainService.shared.saveKeyTableIndices(response.keyTableIndices)
        KeychainService.shared.saveKeyTables(response.keyTables)

        // Backward compatibility: Save old format for Phase 1 fallback
        let fingerprintString = deviceSecret.hexString
        KeychainService.shared.saveDeviceFingerprint(fingerprintString)
        KeychainService.shared.saveTableAssignments(response.keyTableIndices)

        print("[Phase 2] Provisioning complete - device fully provisioned")

        // 5. Verify all credentials are saved
        guard KeychainService.shared.isFullyProvisioned() else {
            throw ProvisioningError.incompleteSave
        }

        // 6. Mark app as provisioned
        DispatchQueue.main.async {
            appState.completeProvisioning(
                fingerprint: fingerprintString,
                assignments: response.keyTableIndices
            )
        }
    }
}

// MARK: - Provisioning Errors

enum ProvisioningError: Error, LocalizedError {
    case secretMismatch
    case incompleteSave
    case networkFailed
    case smaUnavailable

    var errorDescription: String? {
        switch self {
        case .secretMismatch:
            return "Device secret mismatch from SMA"
        case .incompleteSave:
            return "Failed to save all credentials to Keychain"
        case .networkFailed:
            return "Network connection to SMA failed"
        case .smaUnavailable:
            return "SMA server is unavailable"
        }
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
