package org.birthmarkstandard.camera.ui.viewmodels

import android.app.Application
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.birthmarkstandard.camera.services.CameraService
import org.birthmarkstandard.camera.services.SubmissionRepository
import org.birthmarkstandard.camera.workers.SubmissionWorker
import javax.inject.Inject

/**
 * UI state for camera screen.
 */
data class CameraUiState(
    val isCapturing: Boolean = false,
    val lastCaptureUri: Uri? = null,
    val lastCaptureHash: String? = null,
    val error: String? = null,
    val captureCount: Int = 0,
    val pendingSubmissions: Int = 0,
    val submittedCount: Int = 0
)

/**
 * ViewModel for camera capture screen.
 */
@HiltViewModel
class CameraViewModel @Inject constructor(
    application: Application,
    private val cameraService: CameraService,
    private val submissionRepository: SubmissionRepository
) : AndroidViewModel(application) {

    private val _uiState = MutableStateFlow(CameraUiState())
    val uiState: StateFlow<CameraUiState> = _uiState.asStateFlow()

    init {
        loadStats()
    }

    /**
     * Load submission statistics.
     */
    private fun loadStats() {
        viewModelScope.launch {
            val pending = submissionRepository.getPendingCount()
            val submitted = submissionRepository.getSubmittedCount()

            _uiState.value = _uiState.value.copy(
                pendingSubmissions = pending,
                submittedCount = submitted
            )
        }
    }

    /**
     * Capture a photo and create authentication bundle.
     */
    fun capturePhoto() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                isCapturing = true,
                error = null
            )

            try {
                val result = cameraService.capturePhoto()

                // Queue for submission
                submissionRepository.queueSubmission(
                    bundle = result.authBundle,
                    imageUri = result.imageUri.toString()
                )

                // Trigger immediate submission
                SubmissionWorker.scheduleImmediate(getApplication())

                _uiState.value = _uiState.value.copy(
                    isCapturing = false,
                    lastCaptureUri = result.imageUri,
                    lastCaptureHash = result.imageHash,
                    captureCount = _uiState.value.captureCount + 1
                )

                // Refresh stats
                loadStats()

            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isCapturing = false,
                    error = "Capture failed: ${e.message}"
                )
            }
        }
    }

    /**
     * Clear the last capture preview.
     */
    fun clearLastCapture() {
        _uiState.value = _uiState.value.copy(
            lastCaptureUri = null,
            lastCaptureHash = null
        )
    }

    /**
     * Clear error message.
     */
    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }

    /**
     * Refresh submission stats.
     */
    fun refreshStats() {
        loadStats()
    }

    override fun onCleared() {
        super.onCleared()
        cameraService.shutdown()
    }
}
