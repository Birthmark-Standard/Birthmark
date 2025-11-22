package org.birthmarkstandard.camera

import android.app.Application
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import dagger.hilt.android.HiltAndroidApp
import org.birthmarkstandard.camera.workers.SubmissionWorker
import javax.inject.Inject

/**
 * Application class for Birthmark Camera.
 *
 * Initializes Hilt dependency injection and WorkManager for background processing.
 */
@HiltAndroidApp
class BirthmarkApplication : Application(), Configuration.Provider {

    @Inject
    lateinit var workerFactory: HiltWorkerFactory

    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder()
            .setWorkerFactory(workerFactory)
            .build()

    override fun onCreate() {
        super.onCreate()

        // Schedule periodic submission sync
        SubmissionWorker.schedulePeriodicSync(this)
    }
}
