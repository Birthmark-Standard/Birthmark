//
//  CameraView.swift
//  BirthmarkCamera
//
//  Main camera interface with authentication
//

import SwiftUI
import AVFoundation

struct CameraView: View {
    @StateObject private var cameraService = CameraService()
    @State private var isCapturing = false
    @State private var lastStatus = ""
    @State private var showAlert = false
    @State private var alertMessage = ""

    var body: some View {
        ZStack {
            // Camera preview
            if cameraService.isAuthorized {
                CameraPreviewView(session: cameraService.captureSession)
                    .ignoresSafeArea()
            } else {
                VStack {
                    Text("Camera access required")
                        .font(.headline)
                    Text("Please enable camera access in Settings")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                        .padding()
                }
            }

            // Controls overlay
            VStack {
                Spacer()

                // Status message
                if !lastStatus.isEmpty {
                    Text(lastStatus)
                        .font(.caption)
                        .padding(8)
                        .background(Color.black.opacity(0.7))
                        .foregroundColor(.white)
                        .cornerRadius(8)
                        .padding(.bottom, 20)
                }

                // Capture button
                Button(action: capturePhoto) {
                    Circle()
                        .fill(Color.white)
                        .frame(width: 70, height: 70)
                        .overlay(
                            Circle()
                                .stroke(Color.white, lineWidth: 4)
                                .frame(width: 82, height: 82)
                        )
                        .opacity(isCapturing ? 0.5 : 1.0)
                }
                .disabled(isCapturing || !cameraService.isAuthorized)
                .padding(.bottom, 30)
            }
        }
        .onAppear {
            cameraService.startSession()
        }
        .onDisappear {
            cameraService.stopSession()
        }
        .alert("Error", isPresented: $showAlert) {
            Button("OK", role: .cancel) { }
        } message: {
            Text(alertMessage)
        }
    }

    private func capturePhoto() {
        guard !isCapturing else { return }

        isCapturing = true
        lastStatus = "Capturing..."

        cameraService.capturePhoto { result in
            switch result {
            case .success(let imageData):
                handleCapturedImage(imageData)
            case .failure(let error):
                isCapturing = false
                lastStatus = "Capture failed"
                alertMessage = error.localizedDescription
                showAlert = true
            }
        }
    }

    private func handleCapturedImage(_ imageData: Data) {
        lastStatus = "Authenticating..."

        Task {
            do {
                // Authenticate the image
                let response = try await AuthenticationService.shared.authenticateImage(imageData)

                // Save to photo library
                await saveImage(imageData)

                DispatchQueue.main.async {
                    isCapturing = false
                    lastStatus = "✓ Authenticated"
                }

                // Clear status after 3 seconds
                DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
                    lastStatus = ""
                }

            } catch {
                DispatchQueue.main.async {
                    isCapturing = false
                    lastStatus = "Authentication error"
                    alertMessage = error.localizedDescription
                    showAlert = true
                }
            }
        }
    }

    private func saveImage(_ imageData: Data) async {
        await withCheckedContinuation { continuation in
            cameraService.saveToPhotoLibrary(imageData) { result in
                switch result {
                case .success:
                    print("Photo saved to library")
                case .failure(let error):
                    print("Failed to save photo: \(error)")
                }
                continuation.resume()
            }
        }
    }
}

/// Camera preview layer wrapper
struct CameraPreviewView: UIViewRepresentable {
    let session: AVCaptureSession?

    func makeUIView(context: Context) -> UIView {
        let view = UIView(frame: .zero)
        view.backgroundColor = .black

        if let session = session {
            let previewLayer = AVCaptureVideoPreviewLayer(session: session)
            previewLayer.videoGravity = .resizeAspectFill
            previewLayer.frame = view.bounds
            view.layer.addSublayer(previewLayer)
            context.coordinator.previewLayer = previewLayer
        }

        return view
    }

    func updateUIView(_ uiView: UIView, context: Context) {
        // Update frame when view size changes
        if let previewLayer = context.coordinator.previewLayer {
            DispatchQueue.main.async {
                previewLayer.frame = uiView.bounds
            }
        }
    }

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    class Coordinator {
        var previewLayer: AVCaptureVideoPreviewLayer?
    }
}

struct CameraView_Previews: PreviewProvider {
    static var previews: some View {
        CameraView()
    }
}
