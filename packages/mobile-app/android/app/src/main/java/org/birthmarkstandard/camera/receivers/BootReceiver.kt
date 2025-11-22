package org.birthmarkstandard.camera.receivers

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import org.birthmarkstandard.camera.workers.SubmissionWorker

/**
 * Broadcast receiver that reschedules submission work after device boot.
 *
 * Ensures pending submissions are processed even if the device was restarted.
 */
class BootReceiver : BroadcastReceiver() {

    companion object {
        private const val TAG = "BootReceiver"
    }

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            Log.d(TAG, "Device boot completed, scheduling submission work")

            // Reschedule periodic submission sync
            SubmissionWorker.schedulePeriodicSync(context)

            // Also schedule immediate check for pending submissions
            SubmissionWorker.scheduleImmediate(context)
        }
    }
}
