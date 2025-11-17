//
//  ContentView.swift
//  BirthmarkCamera
//
//  Root view controller - shows provisioning or camera based on state
//

import SwiftUI

struct ContentView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        Group {
            if appState.isProvisioned {
                MainTabView()
            } else {
                ProvisioningView()
            }
        }
    }
}

struct MainTabView: View {
    var body: some View {
        TabView {
            CameraView()
                .tabItem {
                    Label("Camera", systemImage: "camera")
                }

            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gear")
                }
        }
    }
}
