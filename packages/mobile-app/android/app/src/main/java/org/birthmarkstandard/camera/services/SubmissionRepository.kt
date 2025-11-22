package org.birthmarkstandard.camera.services

import android.content.Context
import androidx.room.Dao
import androidx.room.Database
import androidx.room.Delete
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.Update
import com.google.gson.Gson
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import org.birthmarkstandard.camera.models.AuthenticationBundle
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Room entity for pending submissions.
 */
@Entity(tableName = "pending_submissions")
data class PendingSubmissionEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,

    /** Serialized AuthenticationBundle as JSON */
    val bundleJson: String,

    /** URI of the captured image */
    val imageUri: String,

    /** Image hash (for display/lookup) */
    val imageHash: String,

    /** When the submission was created */
    val createdAt: Long = System.currentTimeMillis(),

    /** Number of submission attempts */
    val retryCount: Int = 0,

    /** Last error message if failed */
    val lastError: String? = null,

    /** Status: pending, submitting, submitted, failed */
    val status: String = "pending"
)

/**
 * Room DAO for pending submissions.
 */
@Dao
interface PendingSubmissionDao {
    @Query("SELECT * FROM pending_submissions WHERE status = 'pending' OR status = 'failed' ORDER BY createdAt ASC")
    fun getPendingSubmissions(): Flow<List<PendingSubmissionEntity>>

    @Query("SELECT * FROM pending_submissions WHERE status = 'pending' OR status = 'failed' ORDER BY createdAt ASC LIMIT :limit")
    suspend fun getPendingSubmissionsSync(limit: Int = 10): List<PendingSubmissionEntity>

    @Query("SELECT * FROM pending_submissions ORDER BY createdAt DESC")
    fun getAllSubmissions(): Flow<List<PendingSubmissionEntity>>

    @Query("SELECT * FROM pending_submissions WHERE id = :id")
    suspend fun getById(id: Long): PendingSubmissionEntity?

    @Query("SELECT * FROM pending_submissions WHERE imageHash = :imageHash")
    suspend fun getByImageHash(imageHash: String): PendingSubmissionEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(submission: PendingSubmissionEntity): Long

    @Update
    suspend fun update(submission: PendingSubmissionEntity)

    @Delete
    suspend fun delete(submission: PendingSubmissionEntity)

    @Query("DELETE FROM pending_submissions WHERE status = 'submitted' AND createdAt < :beforeTimestamp")
    suspend fun deleteOldSubmitted(beforeTimestamp: Long)

    @Query("SELECT COUNT(*) FROM pending_submissions WHERE status = 'pending' OR status = 'failed'")
    suspend fun getPendingCount(): Int

    @Query("SELECT COUNT(*) FROM pending_submissions WHERE status = 'submitted'")
    suspend fun getSubmittedCount(): Int
}

/**
 * Room database for the app.
 */
@Database(entities = [PendingSubmissionEntity::class], version = 1, exportSchema = false)
abstract class BirthmarkDatabase : RoomDatabase() {
    abstract fun pendingSubmissionDao(): PendingSubmissionDao
}

/**
 * Repository for managing pending submissions.
 */
@Singleton
class SubmissionRepository @Inject constructor(
    @ApplicationContext context: Context
) {
    private val gson = Gson()

    private val database = Room.databaseBuilder(
        context,
        BirthmarkDatabase::class.java,
        "birthmark_database"
    ).build()

    private val dao = database.pendingSubmissionDao()

    /**
     * Queue a new submission.
     *
     * @param bundle Authentication bundle to submit
     * @param imageUri URI of the captured image
     * @return ID of the queued submission
     */
    suspend fun queueSubmission(bundle: AuthenticationBundle, imageUri: String): Long {
        val entity = PendingSubmissionEntity(
            bundleJson = gson.toJson(bundle),
            imageUri = imageUri,
            imageHash = bundle.imageHash,
            status = "pending"
        )
        return dao.insert(entity)
    }

    /**
     * Get pending submissions as a Flow for observing.
     */
    fun observePendingSubmissions(): Flow<List<PendingSubmissionEntity>> {
        return dao.getPendingSubmissions()
    }

    /**
     * Get all submissions for history.
     */
    fun observeAllSubmissions(): Flow<List<PendingSubmissionEntity>> {
        return dao.getAllSubmissions()
    }

    /**
     * Get pending submissions for processing.
     */
    suspend fun getPendingSubmissions(limit: Int = 10): List<PendingSubmissionEntity> {
        return dao.getPendingSubmissionsSync(limit)
    }

    /**
     * Get submission by ID.
     */
    suspend fun getSubmission(id: Long): PendingSubmissionEntity? {
        return dao.getById(id)
    }

    /**
     * Deserialize authentication bundle from entity.
     */
    fun getBundle(entity: PendingSubmissionEntity): AuthenticationBundle {
        return gson.fromJson(entity.bundleJson, AuthenticationBundle::class.java)
    }

    /**
     * Mark submission as submitting (in progress).
     */
    suspend fun markSubmitting(id: Long) {
        dao.getById(id)?.let { entity ->
            dao.update(entity.copy(status = "submitting"))
        }
    }

    /**
     * Mark submission as successfully submitted.
     */
    suspend fun markSubmitted(id: Long) {
        dao.getById(id)?.let { entity ->
            dao.update(entity.copy(status = "submitted", lastError = null))
        }
    }

    /**
     * Mark submission as failed with error.
     */
    suspend fun markFailed(id: Long, error: String) {
        dao.getById(id)?.let { entity ->
            dao.update(entity.copy(
                status = "failed",
                lastError = error,
                retryCount = entity.retryCount + 1
            ))
        }
    }

    /**
     * Reset failed submission for retry.
     */
    suspend fun resetForRetry(id: Long) {
        dao.getById(id)?.let { entity ->
            dao.update(entity.copy(status = "pending"))
        }
    }

    /**
     * Delete a submission.
     */
    suspend fun deleteSubmission(id: Long) {
        dao.getById(id)?.let { entity ->
            dao.delete(entity)
        }
    }

    /**
     * Clean up old submitted entries (older than 7 days).
     */
    suspend fun cleanupOldSubmissions() {
        val sevenDaysAgo = System.currentTimeMillis() - (7 * 24 * 60 * 60 * 1000L)
        dao.deleteOldSubmitted(sevenDaysAgo)
    }

    /**
     * Get count of pending submissions.
     */
    suspend fun getPendingCount(): Int {
        return dao.getPendingCount()
    }

    /**
     * Get count of submitted (successful) submissions.
     */
    suspend fun getSubmittedCount(): Int {
        return dao.getSubmittedCount()
    }
}
