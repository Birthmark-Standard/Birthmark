package org.birthmarkstandard.camera.services

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import org.birthmarkstandard.camera.models.AuthenticationBundle
import java.io.ByteArrayOutputStream
import java.io.File
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/**
 * Camera service using CameraX for photo capture and authentication.
 *
 * Handles:
 * - Camera preview setup
 * - Photo capture
 * - Image hashing
 * - Authentication bundle creation
 */
@Singleton
class CameraService @Inject constructor(
    @ApplicationContext private val context: Context,
    private val cryptoService: CryptoService,
    private val keystoreService: KeystoreService
) {
    private var imageCapture: ImageCapture? = null
    private var cameraProvider: ProcessCameraProvider? = null
    private val cameraExecutor: ExecutorService = Executors.newSingleThreadExecutor()

    companion object {
        private const val FILENAME_FORMAT = "yyyy-MM-dd-HH-mm-ss-SSS"
        private const val PHOTO_EXTENSION = ".jpg"
        private const val JPEG_QUALITY = 95
    }

    /**
     * Result of a photo capture operation.
     */
    data class CaptureResult(
        val imageUri: Uri,
        val imageHash: String,
        val authBundle: AuthenticationBundle
    )

    /**
     * Initialize camera preview on a PreviewView.
     *
     * @param previewView The view to show camera preview
     * @param lifecycleOwner Lifecycle owner for camera binding
     * @param lensFacing Which camera to use (default: back)
     */
    suspend fun initializeCamera(
        previewView: PreviewView,
        lifecycleOwner: LifecycleOwner,
        lensFacing: Int = CameraSelector.LENS_FACING_BACK
    ) = withContext(Dispatchers.Main) {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(context)

        cameraProvider = suspendCancellableCoroutine { continuation ->
            cameraProviderFuture.addListener({
                try {
                    continuation.resume(cameraProviderFuture.get())
                } catch (e: Exception) {
                    continuation.resumeWithException(e)
                }
            }, ContextCompat.getMainExecutor(context))
        }

        val provider = cameraProvider ?: throw IllegalStateException("Camera not available")

        // Unbind any existing use cases
        provider.unbindAll()

        // Build preview use case
        val preview = Preview.Builder()
            .build()
            .also {
                it.setSurfaceProvider(previewView.surfaceProvider)
            }

        // Build image capture use case
        imageCapture = ImageCapture.Builder()
            .setCaptureMode(ImageCapture.CAPTURE_MODE_MAXIMIZE_QUALITY)
            .setJpegQuality(JPEG_QUALITY)
            .build()

        // Select camera
        val cameraSelector = CameraSelector.Builder()
            .requireLensFacing(lensFacing)
            .build()

        // Bind use cases to camera
        provider.bindToLifecycle(
            lifecycleOwner,
            cameraSelector,
            preview,
            imageCapture
        )
    }

    /**
     * Capture a photo, hash it, and create authentication bundle.
     *
     * @return CaptureResult with image URI, hash, and auth bundle
     */
    suspend fun capturePhoto(): CaptureResult = withContext(Dispatchers.IO) {
        val capture = imageCapture
            ?: throw IllegalStateException("Camera not initialized")

        // Check if device is provisioned
        if (!keystoreService.isProvisioned()) {
            throw IllegalStateException("Device not provisioned")
        }

        // Create output file
        val photoFile = createPhotoFile()

        // Capture image
        val outputOptions = ImageCapture.OutputFileOptions.Builder(photoFile).build()

        val imageUri = suspendCancellableCoroutine<Uri> { continuation ->
            capture.takePicture(
                outputOptions,
                cameraExecutor,
                object : ImageCapture.OnImageSavedCallback {
                    override fun onImageSaved(output: ImageCapture.OutputFileResults) {
                        val savedUri = output.savedUri ?: Uri.fromFile(photoFile)
                        continuation.resume(savedUri)
                    }

                    override fun onError(exception: ImageCaptureException) {
                        continuation.resumeWithException(exception)
                    }
                }
            )
        }

        // Read image bytes and compute hash
        val imageBytes = readImageBytes(imageUri)
        val imageHash = cryptoService.bytesToHex(cryptoService.sha256(imageBytes))

        // Create authentication bundle
        val authBundle = createAuthenticationBundle(imageHash)

        CaptureResult(
            imageUri = imageUri,
            imageHash = imageHash,
            authBundle = authBundle
        )
    }

    /**
     * Create authentication bundle for an image hash.
     */
    private fun createAuthenticationBundle(imageHash: String): AuthenticationBundle {
        val deviceSecret = keystoreService.getDeviceSecret()
            ?: throw IllegalStateException("Device secret not found")
        val masterKeys = keystoreService.getMasterKeys()
            ?: throw IllegalStateException("Master keys not found")
        val tableIndices = keystoreService.getTableIndices()
            ?: throw IllegalStateException("Table indices not found")

        // Create camera token (encrypted device secret)
        val cameraToken = cryptoService.createCameraToken(deviceSecret, masterKeys, tableIndices)

        val timestamp = System.currentTimeMillis() / 1000 // Unix timestamp

        // Create bundle data for signing
        val bundleData = buildString {
            append(imageHash)
            append(cryptoService.encodeBase64(cameraToken.encryptedToken))
            append(cameraToken.tableIndex)
            append(cameraToken.keyIndex)
            append(cryptoService.encodeBase64(cameraToken.nonce))
            append(timestamp)
        }.toByteArray()

        // Sign the bundle
        val signature = keystoreService.sign(bundleData)

        return AuthenticationBundle(
            imageHash = imageHash,
            cameraToken = cryptoService.encodeBase64(cameraToken.encryptedToken),
            tableIndex = cameraToken.tableIndex,
            keyIndex = cameraToken.keyIndex,
            nonce = cryptoService.encodeBase64(cameraToken.nonce),
            timestamp = timestamp,
            gpsHash = null, // GPS not implemented in v1
            signature = cryptoService.encodeBase64(signature)
        )
    }

    /**
     * Hash an existing image file.
     *
     * @param uri URI of the image to hash
     * @return SHA-256 hash as hex string
     */
    suspend fun hashImage(uri: Uri): String = withContext(Dispatchers.IO) {
        val imageBytes = readImageBytes(uri)
        cryptoService.bytesToHex(cryptoService.sha256(imageBytes))
    }

    /**
     * Create authentication bundle for an existing image.
     *
     * @param uri URI of the image
     * @return Authentication bundle ready for submission
     */
    suspend fun createBundleForExistingImage(uri: Uri): AuthenticationBundle = withContext(Dispatchers.IO) {
        val imageHash = hashImage(uri)
        createAuthenticationBundle(imageHash)
    }

    /**
     * Read image bytes from URI.
     */
    private fun readImageBytes(uri: Uri): ByteArray {
        return context.contentResolver.openInputStream(uri)?.use { inputStream ->
            inputStream.readBytes()
        } ?: throw IllegalStateException("Cannot read image: $uri")
    }

    /**
     * Create a file for saving captured photo.
     */
    private fun createPhotoFile(): File {
        val timestamp = SimpleDateFormat(FILENAME_FORMAT, Locale.US).format(System.currentTimeMillis())
        val filename = "BIRTHMARK_$timestamp$PHOTO_EXTENSION"

        val photosDir = File(context.filesDir, "photos").apply {
            if (!exists()) mkdirs()
        }

        return File(photosDir, filename)
    }

    /**
     * Get the directory where photos are stored.
     */
    fun getPhotosDirectory(): File {
        return File(context.filesDir, "photos")
    }

    /**
     * Release camera resources.
     */
    fun shutdown() {
        cameraProvider?.unbindAll()
        cameraExecutor.shutdown()
    }
}
