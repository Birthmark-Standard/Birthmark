package org.birthmarkstandard.camera.models

import com.google.gson.annotations.SerializedName

/**
 * Device credentials stored securely in Android Keystore.
 * Created during provisioning and used for all subsequent authentications.
 */
data class DeviceCredentials(
    /** 32-byte device secret - permanent device identifier */
    val deviceSecret: ByteArray,

    /** Device serial/ID used during provisioning */
    val deviceSerial: String,

    /** Device certificate in PEM format */
    val deviceCertificate: String,

    /** Private key alias in Android Keystore */
    val privateKeyAlias: String,

    /** Global indices of assigned key tables (3 tables from pool of 2500) */
    val keyTableIndices: List<Int>,

    /** Master keys for each assigned table (3 x 32 bytes) */
    val masterKeys: List<ByteArray>,

    /** Timestamp when device was provisioned */
    val provisionedAt: Long
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false
        other as DeviceCredentials
        return deviceSecret.contentEquals(other.deviceSecret) &&
               deviceSerial == other.deviceSerial
    }

    override fun hashCode(): Int {
        var result = deviceSecret.contentHashCode()
        result = 31 * result + deviceSerial.hashCode()
        return result
    }
}

/**
 * Response from SMA provisioning endpoint.
 */
data class ProvisionResponse(
    @SerializedName("device_id")
    val deviceId: String,

    @SerializedName("device_certificate")
    val deviceCertificate: String,

    @SerializedName("certificate_chain")
    val certificateChain: List<String>,

    @SerializedName("key_tables")
    val keyTables: List<List<String>>,  // Base64-encoded keys

    @SerializedName("key_table_indices")
    val keyTableIndices: List<Int>,

    @SerializedName("provisioning_id")
    val provisioningId: String
)

/**
 * Request to SMA provisioning endpoint.
 */
data class ProvisionRequest(
    @SerializedName("device_id")
    val deviceId: String,

    @SerializedName("device_secret_hash")
    val deviceSecretHash: String,

    @SerializedName("platform")
    val platform: String = "Android",

    @SerializedName("app_version")
    val appVersion: String
)
