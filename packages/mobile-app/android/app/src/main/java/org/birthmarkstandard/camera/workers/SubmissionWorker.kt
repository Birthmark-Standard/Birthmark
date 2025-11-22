package org.birthmarkstandard.camera.workers

import android.content.Context
import android.util.Log
import androidx.hilt.work.HiltWorker
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import org.birthmarkstandard.camera.services.NetworkService
import org.birthmarkstandard.camera.services.SubmissionRepository
import java.util.concurrent.TimeUnit

/**
 * WorkManager worker for background submission of authentication bundles.
 *
 * Handles:
 * - Processing pending submissions from the queue
 * - Retry logic with exponential backoff
 * - Network connectivity requirements
 */
@HiltWorker
class SubmissionWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted workerParams: WorkerParameters,
    private val submissionRepository: SubmissionRepository,
    private val networkService: NetworkService
) : CoroutineWorker(appContext, workerParams) {

    companion object {
        private const val TAG = "SubmissionWorker"
        private const val WORK_NAME_IMMEDIATE = "submission_immediate"
        private const val WORK_NAME_PERIODIC = "submission_periodic"
        private const val MAX_RETRY_COUNT = 5
        private const val BATCH_SIZE = 10

        /**
         * Schedule immediate submission processing.
         */
        fun scheduleImmediate(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()

            val request = OneTimeWorkRequestBuilder<SubmissionWorker>()
                .setConstraints(constraints)
                .setBackoffCriteria(
                    BackoffPolicy.EXPONENTIAL,
                    30,
                    TimeUnit.SECONDS
                )
                .build()

            WorkManager.getInstance(context)
                .enqueueUniqueWork(
                    WORK_NAME_IMMEDIATE,
                    ExistingWorkPolicy.KEEP,
                    request
                )

            Log.d(TAG, "Scheduled immediate submission work")
        }

        /**
         * Schedule periodic submission processing (every 15 minutes).
         * Handles submissions that failed or were queued while offline.
         */
        fun schedulePeriodicSync(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()

            val request = PeriodicWorkRequestBuilder<SubmissionWorker>(
                15,
                TimeUnit.MINUTES
            )
                .setConstraints(constraints)
                .setBackoffCriteria(
                    BackoffPolicy.EXPONENTIAL,
                    1,
                    TimeUnit.MINUTES
                )
                .build()

            WorkManager.getInstance(context)
                .enqueueUniquePeriodicWork(
                    WORK_NAME_PERIODIC,
                    ExistingPeriodicWorkPolicy.KEEP,
                    request
                )

            Log.d(TAG, "Scheduled periodic submission sync")
        }

        /**
         * Cancel all scheduled work.
         */
        fun cancelAll(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME_IMMEDIATE)
            WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME_PERIODIC)
        }
    }

    override suspend fun doWork(): Result {
        Log.d(TAG, "Starting submission worker")

        // Check aggregator connectivity first
        if (!networkService.checkAggregatorHealth()) {
            Log.w(TAG, "Aggregator not reachable, will retry")
            return Result.retry()
        }

        // Get pending submissions
        val pendingSubmissions = submissionRepository.getPendingSubmissions(BATCH_SIZE)

        if (pendingSubmissions.isEmpty()) {
            Log.d(TAG, "No pending submissions")
            return Result.success()
        }

        Log.d(TAG, "Processing ${pendingSubmissions.size} pending submissions")

        var successCount = 0
        var failureCount = 0

        for (submission in pendingSubmissions) {
            // Skip if too many retries
            if (submission.retryCount >= MAX_RETRY_COUNT) {
                Log.w(TAG, "Submission ${submission.id} exceeded max retries, marking as failed")
                submissionRepository.markFailed(submission.id, "Max retries exceeded")
                continue
            }

            try {
                // Mark as submitting
                submissionRepository.markSubmitting(submission.id)

                // Get the bundle
                val bundle = submissionRepository.getBundle(submission)

                // Submit to aggregator
                val result = networkService.submitBundle(bundle)

                result.fold(
                    onSuccess = { response ->
                        Log.d(TAG, "Submission ${submission.id} successful: receipt=${response.receiptId}")
                        submissionRepository.markSubmitted(submission.id)
                        successCount++
                    },
                    onFailure = { error ->
                        Log.e(TAG, "Submission ${submission.id} failed: ${error.message}")
                        submissionRepository.markFailed(submission.id, error.message ?: "Unknown error")
                        failureCount++
                    }
                )
            } catch (e: Exception) {
                Log.e(TAG, "Error processing submission ${submission.id}", e)
                submissionRepository.markFailed(submission.id, e.message ?: "Processing error")
                failureCount++
            }
        }

        Log.d(TAG, "Submission worker complete: $successCount succeeded, $failureCount failed")

        // Cleanup old submitted entries
        submissionRepository.cleanupOldSubmissions()

        // If all failed due to network issues, retry
        return if (failureCount > 0 && successCount == 0) {
            Result.retry()
        } else {
            Result.success()
        }
    }
}
