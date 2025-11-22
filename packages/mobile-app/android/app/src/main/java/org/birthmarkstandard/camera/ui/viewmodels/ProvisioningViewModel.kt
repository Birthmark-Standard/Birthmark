package org.birthmarkstandard.camera.ui.viewmodels

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.birthmarkstandard.camera.BuildConfig
import org.birthmarkstandard.camera.services.CryptoService
import org.birthmarkstandard.camera.services.KeystoreService
import org.birthmarkstandard.camera.services.NetworkService
import javax.inject.Inject

/**
 * UI state for provisioning screen.
 */
data class ProvisioningUiState(
    val isLoading: Boolean = false,
    val isProvisioned: Boolean = false,
    val error: String? = null,
    val statusMessage: String = "Checking provisioning status...",
    val deviceId: String = "",
    val smaConnected: Boolean = false
)

/**
 * ViewModel for device provisioning screen.
 */
@HiltViewModel
class ProvisioningViewModel @Inject constructor(
    application: Application,
    private val keystoreService: KeystoreService,
    private val networkService: NetworkService,
    private val cryptoService: CryptoService
) : AndroidViewModel(application) {

    private val _uiState = MutableStateFlow(ProvisioningUiState())
    val uiState: StateFlow<ProvisioningUiState> = _uiState.asStateFlow()

    init {
        checkProvisioningStatus()
    }

    /**
     * Check if device is already provisioned.
     */
    fun checkProvisioningStatus() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                isLoading = true,
                statusMessage = "Checking provisioning status..."
            )

            val isProvisioned = keystoreService.isProvisioned()
            val deviceId = keystoreService.getAndroidId()

            if (isProvisioned) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    isProvisioned = true,
                    deviceId = deviceId,
                    statusMessage = "Device is provisioned"
                )
            } else {
                // Check SMA connectivity
                val smaConnected = networkService.checkSmaHealth()

                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    isProvisioned = false,
                    deviceId = deviceId,
                    smaConnected = smaConnected,
                    statusMessage = if (smaConnected) "Ready to provision" else "Cannot reach SMA server"
                )
            }
        }
    }

    /**
     * Start device provisioning with SMA.
     */
    fun startProvisioning() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                isLoading = true,
                error = null,
                statusMessage = "Initializing device secret..."
            )

            try {
                // Step 1: Initialize device secret
                val deviceSecret = keystoreService.initializeDeviceSecret()
                val deviceSecretHash = cryptoService.bytesToHex(cryptoService.sha256(deviceSecret))

                _uiState.value = _uiState.value.copy(
                    statusMessage = "Generating signing key..."
                )

                // Step 2: Generate ECDSA key pair
                keystoreService.generateSigningKeyPair()

                _uiState.value = _uiState.value.copy(
                    statusMessage = "Connecting to SMA..."
                )

                // Step 3: Request provisioning from SMA
                val deviceId = keystoreService.getAndroidId()
                val appVersion = BuildConfig.VERSION_NAME

                val result = networkService.provisionDevice(
                    deviceId = deviceId,
                    deviceSecretHash = deviceSecretHash,
                    appVersion = appVersion
                )

                result.fold(
                    onSuccess = { response ->
                        _uiState.value = _uiState.value.copy(
                            statusMessage = "Storing credentials..."
                        )

                        // Step 4: Decode and store master keys
                        val masterKeys = response.keyTables.map { tableKeys ->
                            // Each table has multiple keys, we store the master key (first key)
                            cryptoService.decodeBase64(tableKeys.first())
                        }

                        // Step 5: Store credentials
                        keystoreService.storeProvisioningCredentials(
                            deviceSerial = response.deviceId,
                            deviceCertificate = response.deviceCertificate,
                            tableIndices = response.keyTableIndices,
                            masterKeys = masterKeys
                        )

                        _uiState.value = _uiState.value.copy(
                            isLoading = false,
                            isProvisioned = true,
                            statusMessage = "Provisioning complete!"
                        )
                    },
                    onFailure = { error ->
                        _uiState.value = _uiState.value.copy(
                            isLoading = false,
                            error = "Provisioning failed: ${error.message}",
                            statusMessage = "Provisioning failed"
                        )
                    }
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = "Error: ${e.message}",
                    statusMessage = "Provisioning error"
                )
            }
        }
    }

    /**
     * Clear provisioning (for testing).
     */
    fun clearProvisioning() {
        viewModelScope.launch {
            keystoreService.clearCredentials()
            checkProvisioningStatus()
        }
    }
}
