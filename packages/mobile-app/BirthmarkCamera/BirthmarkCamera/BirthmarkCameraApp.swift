//
//  BirthmarkCameraApp.swift
//  BirthmarkCamera
//
//  Main app entry point for Birthmark Standard iOS camera
//

import SwiftUI

@main
struct BirthmarkCameraApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
        }
    }
}

/// Global app state manager
class AppState: ObservableObject {
    @Published var isProvisioned: Bool = false
    @Published var deviceInfo: DeviceInfo?
    @Published var queueCount: Int = 0

    init() {
        checkProvisioningStatus()
    }

    private func checkProvisioningStatus() {
        // Check if device fingerprint exists in Keychain
        if let _ = KeychainService.shared.getDeviceFingerprint() {
            isProvisioned = true
            loadDeviceInfo()
        }
    }

    private func loadDeviceInfo() {
        if let fingerprint = KeychainService.shared.getDeviceFingerprint(),
           let assignments = KeychainService.shared.getTableAssignments() {
            deviceInfo = DeviceInfo(
                fingerprint: fingerprint,
                tableAssignments: assignments
            )
        }
    }

    func completeProvisioning(fingerprint: String, assignments: [Int]) {
        KeychainService.shared.saveDeviceFingerprint(fingerprint)
        KeychainService.shared.saveTableAssignments(assignments)
        isProvisioned = true
        loadDeviceInfo()
    }
}

struct DeviceInfo {
    let fingerprint: String
    let tableAssignments: [Int]
}
