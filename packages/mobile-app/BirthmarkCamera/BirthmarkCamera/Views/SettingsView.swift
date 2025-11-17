//
//  SettingsView.swift
//  BirthmarkCamera
//
//  Settings and device information
//

import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var appState: AppState
    @State private var queueCount = 0
    @State private var isProcessingQueue = false
    @State private var showResetAlert = false

    var body: some View {
        NavigationView {
            List {
                // Device Info Section
                Section("Device Information") {
                    if let deviceInfo = appState.deviceInfo {
                        InfoRow(label: "Fingerprint", value: deviceInfo.fingerprint.prefix(16) + "...")
                        InfoRow(label: "Table Assignments", value: deviceInfo.tableAssignments.map(String.init).joined(separator: ", "))
                    }

                    InfoRow(label: "Status", value: appState.isProvisioned ? "Provisioned" : "Not Provisioned")
                }

                // Queue Section
                Section("Submission Queue") {
                    HStack {
                        Text("Pending Submissions")
                        Spacer()
                        Text("\(queueCount)")
                            .foregroundColor(.secondary)
                    }

                    Button(action: processQueue) {
                        HStack {
                            Text("Sync Now")
                            Spacer()
                            if isProcessingQueue {
                                ProgressView()
                            }
                        }
                    }
                    .disabled(isProcessingQueue || queueCount == 0)

                    Button("Clear Queue") {
                        NetworkService.shared.clearQueue()
                        updateQueueCount()
                    }
                    .foregroundColor(.red)
                    .disabled(queueCount == 0)
                }

                // App Info Section
                Section("About") {
                    InfoRow(label: "Version", value: "1.0.0 (Beta)")
                    InfoRow(label: "Phase", value: "Phase 2 - iOS Validation")

                    Link("View on GitHub", destination: URL(string: "https://github.com/Birthmark-Standard/Birthmark")!)
                }

                // Reset Section
                Section {
                    Button("Reset Device", role: .destructive) {
                        showResetAlert = true
                    }
                }
            }
            .navigationTitle("Settings")
            .onAppear {
                updateQueueCount()
            }
            .alert("Reset Device?", isPresented: $showResetAlert) {
                Button("Cancel", role: .cancel) { }
                Button("Reset", role: .destructive) {
                    resetDevice()
                }
            } message: {
                Text("This will delete your device fingerprint and all queued submissions. This cannot be undone.")
            }
        }
    }

    private func updateQueueCount() {
        queueCount = NetworkService.shared.getQueueCount()
    }

    private func processQueue() {
        isProcessingQueue = true

        Task {
            await AuthenticationService.shared.processQueuedSubmissions()

            DispatchQueue.main.async {
                isProcessingQueue = false
                updateQueueCount()
            }
        }
    }

    private func resetDevice() {
        KeychainService.shared.deleteAll()
        NetworkService.shared.clearQueue()
        appState.isProvisioned = false
        appState.deviceInfo = nil
    }
}

struct InfoRow: View {
    let label: String
    let value: String

    var body: some View {
        HStack {
            Text(label)
            Spacer()
            Text(value)
                .foregroundColor(.secondary)
                .lineLimit(1)
        }
    }
}

struct SettingsView_Previews: PreviewProvider {
    static var previews: some View {
        SettingsView()
            .environmentObject(AppState())
    }
}
