package org.birthmarkstandard.camera.services

import org.birthmarkstandard.camera.BuildConfig
import org.birthmarkstandard.camera.models.AuthenticationBundle
import org.birthmarkstandard.camera.models.ProvisionRequest
import org.birthmarkstandard.camera.models.ProvisionResponse
import org.birthmarkstandard.camera.models.SubmissionResponse
import org.birthmarkstandard.camera.models.VerificationResponse
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Network API interface for SMA (Simulated Manufacturer Authority).
 */
interface SmaApi {
    /**
     * Request device provisioning from SMA.
     * Returns device certificate and key tables.
     */
    @POST("api/v1/provision")
    suspend fun provision(@Body request: ProvisionRequest): Response<ProvisionResponse>

    /**
     * Health check for SMA connection.
     */
    @GET("api/v1/health")
    suspend fun health(): Response<Map<String, Any>>
}

/**
 * Network API interface for Aggregation Server.
 */
interface AggregatorApi {
    /**
     * Submit authentication bundle for a captured photo.
     */
    @POST("api/v1/submit")
    suspend fun submit(@Body bundle: AuthenticationBundle): Response<SubmissionResponse>

    /**
     * Verify an image hash against the blockchain.
     */
    @GET("api/v1/verify/{imageHash}")
    suspend fun verify(@Path("imageHash") imageHash: String): Response<VerificationResponse>

    /**
     * Health check for aggregator connection.
     */
    @GET("api/v1/health")
    suspend fun health(): Response<Map<String, Any>>
}

/**
 * Network service for communicating with SMA and Aggregation Server.
 *
 * Handles:
 * - Device provisioning with SMA
 * - Authentication bundle submission to aggregator
 * - Image hash verification queries
 */
@Singleton
class NetworkService @Inject constructor() {

    private val smaApi: SmaApi by lazy {
        Retrofit.Builder()
            .baseUrl(BuildConfig.SMA_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(SmaApi::class.java)
    }

    private val aggregatorApi: AggregatorApi by lazy {
        Retrofit.Builder()
            .baseUrl(BuildConfig.AGGREGATOR_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(AggregatorApi::class.java)
    }

    /**
     * Provision device with SMA.
     *
     * @param deviceId Unique device identifier (Android ID)
     * @param deviceSecretHash SHA-256 hash of device secret (hex string)
     * @param appVersion Current app version
     * @return ProvisionResponse with certificates and key tables, or null on failure
     */
    suspend fun provisionDevice(
        deviceId: String,
        deviceSecretHash: String,
        appVersion: String
    ): Result<ProvisionResponse> {
        return try {
            val request = ProvisionRequest(
                deviceId = deviceId,
                deviceSecretHash = deviceSecretHash,
                platform = "Android",
                appVersion = appVersion
            )

            val response = smaApi.provision(request)

            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(
                    NetworkException(
                        "Provisioning failed: ${response.code()} - ${response.errorBody()?.string()}"
                    )
                )
            }
        } catch (e: Exception) {
            Result.failure(NetworkException("Provisioning error: ${e.message}", e))
        }
    }

    /**
     * Submit authentication bundle to aggregation server.
     *
     * @param bundle Complete authentication bundle for the photo
     * @return SubmissionResponse with receipt ID, or failure
     */
    suspend fun submitBundle(bundle: AuthenticationBundle): Result<SubmissionResponse> {
        return try {
            val response = aggregatorApi.submit(bundle)

            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(
                    NetworkException(
                        "Submission failed: ${response.code()} - ${response.errorBody()?.string()}"
                    )
                )
            }
        } catch (e: Exception) {
            Result.failure(NetworkException("Submission error: ${e.message}", e))
        }
    }

    /**
     * Verify an image hash against the blockchain.
     *
     * @param imageHash SHA-256 hash of the image (64 hex characters)
     * @return VerificationResponse indicating if image is verified
     */
    suspend fun verifyImage(imageHash: String): Result<VerificationResponse> {
        return try {
            val response = aggregatorApi.verify(imageHash)

            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(
                    NetworkException(
                        "Verification failed: ${response.code()} - ${response.errorBody()?.string()}"
                    )
                )
            }
        } catch (e: Exception) {
            Result.failure(NetworkException("Verification error: ${e.message}", e))
        }
    }

    /**
     * Check SMA connectivity.
     */
    suspend fun checkSmaHealth(): Boolean {
        return try {
            val response = smaApi.health()
            response.isSuccessful
        } catch (e: Exception) {
            false
        }
    }

    /**
     * Check aggregator connectivity.
     */
    suspend fun checkAggregatorHealth(): Boolean {
        return try {
            val response = aggregatorApi.health()
            response.isSuccessful
        } catch (e: Exception) {
            false
        }
    }
}

/**
 * Exception for network-related errors.
 */
class NetworkException(message: String, cause: Throwable? = null) : Exception(message, cause)
