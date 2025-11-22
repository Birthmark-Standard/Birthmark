package org.birthmarkstandard.camera.ui.viewmodels

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.birthmarkstandard.camera.services.KeystoreService
import org.birthmarkstandard.camera.services.NetworkService
import org.birthmarkstandard.camera.services.SubmissionRepository
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import javax.inject.Inject

/**
 * UI state for settings screen.
 */
data class SettingsUiState(
    val deviceId: String = "",
    val isProvisioned: Boolean = false,
    val provisionedAt: String? = null,
    val pendingCount: Int = 0,
    val submittedCount: Int = 0,
    val sessionCaptures: Int = 0,
    val smaConnected: Boolean = false,
    val aggregatorConnected: Boolean = false,
    val isRefreshing: Boolean = false
)

/**
 * ViewModel for settings screen.
 */
@HiltViewModel
class SettingsViewModel @Inject constructor(
    application: Application,
    private val keystoreService: KeystoreService,
    private val networkService: NetworkService,
    private val submissionRepository: SubmissionRepository
) : AndroidViewModel(application) {

    private val _uiState = MutableStateFlow(SettingsUiState())
    val uiState: StateFlow<SettingsUiState> = _uiState.asStateFlow()

    private val dateFormat = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault())

    init {
        loadSettings()
        refreshStatus()
    }

    /**
     * Load settings and device info.
     */
    private fun loadSettings() {
        viewModelScope.launch {
            val deviceId = keystoreService.getAndroidId()
            val isProvisioned = keystoreService.isProvisioned()
            val credentials = keystoreService.getCredentials()

            val provisionedAt = credentials?.provisionedAt?.let {
                dateFormat.format(Date(it))
            }

            val pendingCount = submissionRepository.getPendingCount()
            val submittedCount = submissionRepository.getSubmittedCount()

            _uiState.value = _uiState.value.copy(
                deviceId = deviceId,
                isProvisioned = isProvisioned,
                provisionedAt = provisionedAt,
                pendingCount = pendingCount,
                submittedCount = submittedCount
            )
        }
    }

    /**
     * Refresh server connectivity status.
     */
    fun refreshStatus() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isRefreshing = true)

            val smaConnected = networkService.checkSmaHealth()
            val aggregatorConnected = networkService.checkAggregatorHealth()

            _uiState.value = _uiState.value.copy(
                smaConnected = smaConnected,
                aggregatorConnected = aggregatorConnected,
                isRefreshing = false
            )
        }
    }

    /**
     * Reset device provisioning.
     */
    fun resetProvisioning() {
        viewModelScope.launch {
            keystoreService.clearCredentials()
            loadSettings()
        }
    }

    /**
     * Increment session capture count.
     */
    fun incrementSessionCaptures() {
        _uiState.value = _uiState.value.copy(
            sessionCaptures = _uiState.value.sessionCaptures + 1
        )
    }
}
