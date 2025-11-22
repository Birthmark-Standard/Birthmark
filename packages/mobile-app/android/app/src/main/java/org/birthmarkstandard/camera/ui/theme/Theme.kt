package org.birthmarkstandard.camera.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

// Birthmark brand colors
val BirthmarkPrimary = Color(0xFF1976D2)
val BirthmarkPrimaryDark = Color(0xFF0D47A1)
val BirthmarkSecondary = Color(0xFF4CAF50)
val BirthmarkBackground = Color(0xFFFAFAFA)
val BirthmarkSurface = Color(0xFFFFFFFF)
val BirthmarkError = Color(0xFFD32F2F)

private val DarkColorScheme = darkColorScheme(
    primary = BirthmarkPrimary,
    secondary = BirthmarkSecondary,
    background = Color(0xFF121212),
    surface = Color(0xFF1E1E1E),
    error = BirthmarkError,
    onPrimary = Color.White,
    onSecondary = Color.White,
    onBackground = Color.White,
    onSurface = Color.White,
    onError = Color.White
)

private val LightColorScheme = lightColorScheme(
    primary = BirthmarkPrimary,
    secondary = BirthmarkSecondary,
    background = BirthmarkBackground,
    surface = BirthmarkSurface,
    error = BirthmarkError,
    onPrimary = Color.White,
    onSecondary = Color.White,
    onBackground = Color.Black,
    onSurface = Color.Black,
    onError = Color.White
)

@Composable
fun BirthmarkTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colorScheme.primary.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !darkTheme
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        content = content
    )
}
