package org.birthmarkstandard.camera

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import dagger.hilt.android.AndroidEntryPoint
import org.birthmarkstandard.camera.services.CameraService
import org.birthmarkstandard.camera.services.KeystoreService
import org.birthmarkstandard.camera.ui.screens.CameraScreen
import org.birthmarkstandard.camera.ui.screens.ProvisioningScreen
import org.birthmarkstandard.camera.ui.screens.SettingsScreen
import org.birthmarkstandard.camera.ui.theme.BirthmarkTheme
import javax.inject.Inject

/**
 * Main activity for Birthmark Camera app.
 */
@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject
    lateinit var keystoreService: KeystoreService

    @Inject
    lateinit var cameraService: CameraService

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            BirthmarkTheme {
                BirthmarkApp(
                    isProvisioned = keystoreService.isProvisioned(),
                    cameraService = cameraService
                )
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraService.shutdown()
    }
}

/**
 * Navigation routes.
 */
object Routes {
    const val PROVISIONING = "provisioning"
    const val CAMERA = "camera"
    const val SETTINGS = "settings"
}

/**
 * Main app composable with navigation.
 */
@Composable
fun BirthmarkApp(
    isProvisioned: Boolean,
    cameraService: CameraService
) {
    val navController = rememberNavController()

    // Determine start destination based on provisioning status
    val startDestination = if (isProvisioned) Routes.CAMERA else Routes.PROVISIONING

    Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = startDestination,
            modifier = Modifier.padding(innerPadding)
        ) {
            composable(Routes.PROVISIONING) {
                ProvisioningScreen(
                    onProvisioningComplete = {
                        navController.navigate(Routes.CAMERA) {
                            popUpTo(Routes.PROVISIONING) { inclusive = true }
                        }
                    }
                )
            }

            composable(Routes.CAMERA) {
                CameraScreen(
                    cameraService = cameraService,
                    onSettingsClick = {
                        navController.navigate(Routes.SETTINGS)
                    }
                )
            }

            composable(Routes.SETTINGS) {
                SettingsScreen(
                    onBackClick = {
                        navController.popBackStack()
                    },
                    onResetProvisioning = {
                        navController.navigate(Routes.PROVISIONING) {
                            popUpTo(Routes.CAMERA) { inclusive = true }
                        }
                    }
                )
            }
        }
    }
}
