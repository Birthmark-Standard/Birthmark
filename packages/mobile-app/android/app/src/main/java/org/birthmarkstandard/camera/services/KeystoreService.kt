package org.birthmarkstandard.camera.services

import android.content.Context
import android.content.SharedPreferences
import android.provider.Settings
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import dagger.hilt.android.qualifiers.ApplicationContext
import org.birthmarkstandard.camera.models.DeviceCredentials
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.PrivateKey
import java.security.PublicKey
import java.security.Signature
import java.security.spec.ECGenParameterSpec
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Secure credential storage using Android Keystore and EncryptedSharedPreferences.
 *
 * Stores:
 * - Device secret (32 bytes) - hashed random seed + Android ID
 * - Master keys (3 x 32 bytes) - from SMA provisioning
 * - Key table indices (3 integers) - assigned global table IDs
 * - ECDSA P-256 key pair - for signing authentication bundles
 */
@Singleton
class KeystoreService @Inject constructor(
    @ApplicationContext private val context: Context,
    private val cryptoService: CryptoService
) {
    private val keyStore: KeyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
    private val gson = Gson()

    private val encryptedPrefs: SharedPreferences by lazy {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()

        EncryptedSharedPreferences.create(
            context,
            PREFS_FILE_NAME,
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    companion object {
        private const val ANDROID_KEYSTORE = "AndroidKeyStore"
        private const val SIGNING_KEY_ALIAS = "birthmark_signing_key"
        private const val PREFS_FILE_NAME = "birthmark_credentials"

        // Preference keys
        private const val KEY_DEVICE_SECRET = "device_secret"
        private const val KEY_DEVICE_SERIAL = "device_serial"
        private const val KEY_DEVICE_CERTIFICATE = "device_certificate"
        private const val KEY_TABLE_INDICES = "table_indices"
        private const val KEY_MASTER_KEYS = "master_keys"
        private const val KEY_PROVISIONED_AT = "provisioned_at"
        private const val KEY_IS_PROVISIONED = "is_provisioned"
    }

    /**
     * Check if device has been provisioned with SMA.
     */
    fun isProvisioned(): Boolean {
        return encryptedPrefs.getBoolean(KEY_IS_PROVISIONED, false) &&
               keyStore.containsAlias(SIGNING_KEY_ALIAS)
    }

    /**
     * Get the Android ID for this device.
     * Used as part of device secret derivation.
     */
    fun getAndroidId(): String {
        return Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
    }

    /**
     * Initialize device secret during first-time setup.
     * Creates a unique device identifier from random bytes + Android ID.
     *
     * @return The device secret (for sending hash to SMA during provisioning)
     */
    fun initializeDeviceSecret(): ByteArray {
        val androidId = getAndroidId()
        val deviceSecret = cryptoService.createDeviceSecret(androidId)

        // Store encrypted device secret
        encryptedPrefs.edit()
            .putString(KEY_DEVICE_SECRET, cryptoService.encodeBase64(deviceSecret))
            .apply()

        return deviceSecret
    }

    /**
     * Generate ECDSA P-256 key pair for signing authentication bundles.
     * Key is stored in Android Keystore (hardware-backed if available).
     */
    fun generateSigningKeyPair() {
        if (keyStore.containsAlias(SIGNING_KEY_ALIAS)) {
            // Key already exists
            return
        }

        val keyPairGenerator = KeyPairGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_EC,
            ANDROID_KEYSTORE
        )

        val parameterSpec = KeyGenParameterSpec.Builder(
            SIGNING_KEY_ALIAS,
            KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY
        )
            .setAlgorithmParameterSpec(ECGenParameterSpec("secp256r1"))
            .setDigests(KeyProperties.DIGEST_SHA256)
            .setUserAuthenticationRequired(false) // For background operation
            .build()

        keyPairGenerator.initialize(parameterSpec)
        keyPairGenerator.generateKeyPair()
    }

    /**
     * Get the public key for registration with SMA.
     * @return PEM-encoded public key
     */
    fun getPublicKeyPem(): String {
        val publicKey = keyStore.getCertificate(SIGNING_KEY_ALIAS)?.publicKey
            ?: throw IllegalStateException("Signing key not initialized")

        return "-----BEGIN PUBLIC KEY-----\n" +
               android.util.Base64.encodeToString(publicKey.encoded, android.util.Base64.NO_WRAP)
                   .chunked(64).joinToString("\n") +
               "\n-----END PUBLIC KEY-----"
    }

    /**
     * Sign data with the device's private key.
     * Used for signing authentication bundles.
     *
     * @param data Data to sign
     * @return ECDSA signature
     */
    fun sign(data: ByteArray): ByteArray {
        val privateKey = keyStore.getKey(SIGNING_KEY_ALIAS, null) as? PrivateKey
            ?: throw IllegalStateException("Signing key not found")

        val signature = Signature.getInstance("SHA256withECDSA")
        signature.initSign(privateKey)
        signature.update(data)
        return signature.sign()
    }

    /**
     * Store credentials received from SMA provisioning.
     *
     * @param deviceSerial Device identifier assigned by SMA
     * @param deviceCertificate X.509 certificate in PEM format
     * @param tableIndices Global indices of assigned key tables (3)
     * @param masterKeys Master keys for each table (3 x 32 bytes)
     */
    fun storeProvisioningCredentials(
        deviceSerial: String,
        deviceCertificate: String,
        tableIndices: List<Int>,
        masterKeys: List<ByteArray>
    ) {
        require(tableIndices.size == 3) { "Must have 3 table indices" }
        require(masterKeys.size == 3) { "Must have 3 master keys" }
        require(masterKeys.all { it.size == 32 }) { "Each master key must be 32 bytes" }

        // Encode master keys as Base64 JSON array
        val masterKeysEncoded = masterKeys.map { cryptoService.encodeBase64(it) }

        encryptedPrefs.edit()
            .putString(KEY_DEVICE_SERIAL, deviceSerial)
            .putString(KEY_DEVICE_CERTIFICATE, deviceCertificate)
            .putString(KEY_TABLE_INDICES, gson.toJson(tableIndices))
            .putString(KEY_MASTER_KEYS, gson.toJson(masterKeysEncoded))
            .putLong(KEY_PROVISIONED_AT, System.currentTimeMillis())
            .putBoolean(KEY_IS_PROVISIONED, true)
            .apply()
    }

    /**
     * Retrieve stored device credentials.
     *
     * @return DeviceCredentials or null if not provisioned
     */
    fun getCredentials(): DeviceCredentials? {
        if (!isProvisioned()) return null

        val deviceSecretBase64 = encryptedPrefs.getString(KEY_DEVICE_SECRET, null) ?: return null
        val deviceSerial = encryptedPrefs.getString(KEY_DEVICE_SERIAL, null) ?: return null
        val deviceCertificate = encryptedPrefs.getString(KEY_DEVICE_CERTIFICATE, null) ?: return null
        val tableIndicesJson = encryptedPrefs.getString(KEY_TABLE_INDICES, null) ?: return null
        val masterKeysJson = encryptedPrefs.getString(KEY_MASTER_KEYS, null) ?: return null
        val provisionedAt = encryptedPrefs.getLong(KEY_PROVISIONED_AT, 0)

        val tableIndices: List<Int> = gson.fromJson(tableIndicesJson, object : TypeToken<List<Int>>() {}.type)
        val masterKeysEncoded: List<String> = gson.fromJson(masterKeysJson, object : TypeToken<List<String>>() {}.type)
        val masterKeys = masterKeysEncoded.map { cryptoService.decodeBase64(it) }

        return DeviceCredentials(
            deviceSecret = cryptoService.decodeBase64(deviceSecretBase64),
            deviceSerial = deviceSerial,
            deviceCertificate = deviceCertificate,
            privateKeyAlias = SIGNING_KEY_ALIAS,
            keyTableIndices = tableIndices,
            masterKeys = masterKeys,
            provisionedAt = provisionedAt
        )
    }

    /**
     * Get device secret for camera token creation.
     */
    fun getDeviceSecret(): ByteArray? {
        val deviceSecretBase64 = encryptedPrefs.getString(KEY_DEVICE_SECRET, null) ?: return null
        return cryptoService.decodeBase64(deviceSecretBase64)
    }

    /**
     * Get master keys for camera token creation.
     */
    fun getMasterKeys(): List<ByteArray>? {
        val masterKeysJson = encryptedPrefs.getString(KEY_MASTER_KEYS, null) ?: return null
        val masterKeysEncoded: List<String> = gson.fromJson(masterKeysJson, object : TypeToken<List<String>>() {}.type)
        return masterKeysEncoded.map { cryptoService.decodeBase64(it) }
    }

    /**
     * Get key table indices for camera token creation.
     */
    fun getTableIndices(): List<Int>? {
        val tableIndicesJson = encryptedPrefs.getString(KEY_TABLE_INDICES, null) ?: return null
        return gson.fromJson(tableIndicesJson, object : TypeToken<List<Int>>() {}.type)
    }

    /**
     * Clear all stored credentials (for testing/reset).
     */
    fun clearCredentials() {
        encryptedPrefs.edit().clear().apply()

        if (keyStore.containsAlias(SIGNING_KEY_ALIAS)) {
            keyStore.deleteEntry(SIGNING_KEY_ALIAS)
        }
    }
}
