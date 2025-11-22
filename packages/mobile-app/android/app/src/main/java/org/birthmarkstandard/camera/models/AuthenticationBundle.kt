package org.birthmarkstandard.camera.models

import com.google.gson.annotations.SerializedName

/**
 * Authentication bundle sent to aggregation server for each photo.
 * Contains everything needed to verify the photo came from a legitimate device.
 */
data class AuthenticationBundle(
    /** SHA-256 hash of the image (64 hex characters) */
    @SerializedName("image_hash")
    val imageHash: String,

    /** Encrypted device secret (camera token) - Base64 encoded */
    @SerializedName("camera_token")
    val cameraToken: String,

    /** Global table index used for encryption (0-2499) */
    @SerializedName("table_index")
    val tableIndex: Int,

    /** Key index within the table (0-999) */
    @SerializedName("key_index")
    val keyIndex: Int,

    /** AES-GCM nonce used for encryption - Base64 encoded */
    @SerializedName("nonce")
    val nonce: String,

    /** Unix timestamp when photo was captured */
    @SerializedName("timestamp")
    val timestamp: Long,

    /** Optional SHA-256 hash of GPS coordinates */
    @SerializedName("gps_hash")
    val gpsHash: String? = null,

    /** ECDSA signature over the bundle - Base64 encoded */
    @SerializedName("signature")
    val signature: String
)

/**
 * Response from aggregation server after submission.
 */
data class SubmissionResponse(
    @SerializedName("receipt_id")
    val receiptId: String,

    @SerializedName("status")
    val status: String,

    @SerializedName("timestamp")
    val timestamp: Long? = null
)

/**
 * Verification response from blockchain query.
 */
data class VerificationResponse(
    @SerializedName("verified")
    val verified: Boolean,

    @SerializedName("timestamp")
    val timestamp: Long? = null,

    @SerializedName("block_height")
    val blockHeight: Long? = null,

    @SerializedName("aggregator")
    val aggregator: String? = null
)

/**
 * Local queue entry for pending submissions.
 */
data class PendingSubmission(
    val id: Long = 0,
    val bundle: AuthenticationBundle,
    val imageUri: String,
    val createdAt: Long = System.currentTimeMillis(),
    val retryCount: Int = 0,
    val lastError: String? = null
)
