//
//  CameraService.swift
//  BirthmarkCamera
//
//  Camera capture using AVFoundation
//

import AVFoundation
import UIKit
import Photos

class CameraService: NSObject, ObservableObject {
    @Published var isAuthorized = false
    @Published var captureSession: AVCaptureSession?
    @Published var previewLayer: AVCaptureVideoPreviewLayer?

    private var photoOutput: AVCapturePhotoOutput?
    private var captureCompletionHandler: ((Result<Data, Error>) -> Void)?

    override init() {
        super.init()
        checkAuthorization()
    }

    // MARK: - Authorization

    func checkAuthorization() {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            isAuthorized = true
            setupCaptureSession()
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
                DispatchQueue.main.async {
                    self?.isAuthorized = granted
                    if granted {
                        self?.setupCaptureSession()
                    }
                }
            }
        default:
            isAuthorized = false
        }
    }

    // MARK: - Capture Session Setup

    private func setupCaptureSession() {
        let session = AVCaptureSession()
        session.beginConfiguration()
        session.sessionPreset = .photo

        // Add camera input
        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back),
              let input = try? AVCaptureDeviceInput(device: device),
              session.canAddInput(input) else {
            session.commitConfiguration()
            return
        }
        session.addInput(input)

        // Add photo output
        let output = AVCapturePhotoOutput()
        if session.canAddOutput(output) {
            session.addOutput(output)
            photoOutput = output
        }

        session.commitConfiguration()

        DispatchQueue.main.async {
            self.captureSession = session
        }
    }

    func startSession() {
        guard let session = captureSession, !session.isRunning else { return }
        DispatchQueue.global(qos: .userInitiated).async {
            session.startRunning()
        }
    }

    func stopSession() {
        guard let session = captureSession, session.isRunning else { return }
        DispatchQueue.global(qos: .userInitiated).async {
            session.stopRunning()
        }
    }

    // MARK: - Photo Capture

    func capturePhoto(completion: @escaping (Result<Data, Error>) -> Void) {
        guard let photoOutput = photoOutput else {
            completion(.failure(CameraError.outputNotAvailable))
            return
        }

        captureCompletionHandler = completion

        let settings = AVCapturePhotoSettings()
        settings.flashMode = .auto

        photoOutput.capturePhoto(with: settings, delegate: self)
    }

    // MARK: - Photo Library

    func saveToPhotoLibrary(_ imageData: Data, completion: @escaping (Result<Void, Error>) -> Void) {
        PHPhotoLibrary.requestAuthorization { status in
            guard status == .authorized else {
                completion(.failure(CameraError.photoLibraryUnauthorized))
                return
            }

            guard let image = UIImage(data: imageData) else {
                completion(.failure(CameraError.invalidImageData))
                return
            }

            PHPhotoLibrary.shared().performChanges({
                PHAssetCreationRequest.creationRequestForAsset(from: image)
            }) { success, error in
                if let error = error {
                    completion(.failure(error))
                } else if success {
                    completion(.success(()))
                } else {
                    completion(.failure(CameraError.saveFailed))
                }
            }
        }
    }
}

// MARK: - AVCapturePhotoCaptureDelegate

extension CameraService: AVCapturePhotoCaptureDelegate {
    func photoOutput(_ output: AVCapturePhotoOutput, didFinishProcessingPhoto photo: AVCapturePhoto, error: Error?) {
        if let error = error {
            captureCompletionHandler?(.failure(error))
            return
        }

        guard let data = photo.fileDataRepresentation() else {
            captureCompletionHandler?(.failure(CameraError.noImageData))
            return
        }

        captureCompletionHandler?(.success(data))
        captureCompletionHandler = nil
    }
}

enum CameraError: Error {
    case outputNotAvailable
    case noImageData
    case invalidImageData
    case photoLibraryUnauthorized
    case saveFailed
}
