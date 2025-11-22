package org.birthmarkstandard.camera.services

import android.util.Base64
import java.io.InputStream
import java.security.MessageDigest
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.Mac
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Cryptographic operations for the Birthmark authentication system.
 *
 * Implements:
 * - SHA-256 hashing for images and data
 * - AES-256-GCM encryption for camera tokens
 * - HKDF key derivation for rotating encryption keys
 * - ECDSA signing for bundle authentication
 */
@Singleton
class CryptoService @Inject constructor() {

    private val secureRandom = SecureRandom()

    companion object {
        private const val HKDF_CONTEXT = "Birthmark"
        private const val AES_GCM_TAG_LENGTH = 128  // bits
        private const val AES_GCM_NONCE_LENGTH = 12  // bytes
        private const val KEY_SIZE = 32  // bytes (256 bits)
        private const val KEYS_PER_TABLE = 1000
    }

    /**
     * Compute SHA-256 hash of a byte array.
     * @return 32-byte hash
     */
    fun sha256(data: ByteArray): ByteArray {
        val digest = MessageDigest.getInstance("SHA-256")
        return digest.digest(data)
    }

    /**
     * Compute SHA-256 hash of an input stream (for large files like images).
     * @return 32-byte hash
     */
    fun sha256(inputStream: InputStream): ByteArray {
        val digest = MessageDigest.getInstance("SHA-256")
        val buffer = ByteArray(8192)
        var bytesRead: Int
        while (inputStream.read(buffer).also { bytesRead = it } != -1) {
            digest.update(buffer, 0, bytesRead)
        }
        return digest.digest()
    }

    /**
     * Convert byte array to hex string.
     */
    fun bytesToHex(bytes: ByteArray): String {
        return bytes.joinToString("") { "%02x".format(it) }
    }

    /**
     * Convert hex string to byte array.
     */
    fun hexToBytes(hex: String): ByteArray {
        return hex.chunked(2).map { it.toInt(16).toByte() }.toByteArray()
    }

    /**
     * Generate cryptographically secure random bytes.
     */
    fun generateRandomBytes(length: Int): ByteArray {
        val bytes = ByteArray(length)
        secureRandom.nextBytes(bytes)
        return bytes
    }

    /**
     * Derive encryption key from master key using HKDF-SHA256.
     * Must match exactly with SMA implementation.
     *
     * @param masterKey 32-byte master key for the table
     * @param keyIndex Key index within table (0-999)
     * @return 32-byte derived encryption key
     */
    fun deriveKey(masterKey: ByteArray, keyIndex: Int): ByteArray {
        require(masterKey.size == KEY_SIZE) { "Master key must be $KEY_SIZE bytes" }
        require(keyIndex in 0 until KEYS_PER_TABLE) { "Key index must be 0-${KEYS_PER_TABLE - 1}" }

        val context = HKDF_CONTEXT.toByteArray(Charsets.UTF_8)
        val info = ByteArray(4).apply {
            this[0] = ((keyIndex shr 24) and 0xFF).toByte()
            this[1] = ((keyIndex shr 16) and 0xFF).toByte()
            this[2] = ((keyIndex shr 8) and 0xFF).toByte()
            this[3] = (keyIndex and 0xFF).toByte()
        }

        // HKDF Extract
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(context, "HmacSHA256"))
        val prk = mac.doFinal(masterKey)

        // HKDF Expand
        mac.init(SecretKeySpec(prk, "HmacSHA256"))
        mac.update(info)
        mac.update(0x01.toByte())
        return mac.doFinal()
    }

    /**
     * Encrypt data using AES-256-GCM.
     *
     * @param plaintext Data to encrypt
     * @param key 32-byte encryption key
     * @param nonce 12-byte unique nonce (optional, generated if not provided)
     * @return Pair of (ciphertext with auth tag, nonce)
     */
    fun encryptAesGcm(
        plaintext: ByteArray,
        key: ByteArray,
        nonce: ByteArray? = null
    ): Pair<ByteArray, ByteArray> {
        require(key.size == KEY_SIZE) { "Key must be $KEY_SIZE bytes" }

        val actualNonce = nonce ?: generateRandomBytes(AES_GCM_NONCE_LENGTH)
        require(actualNonce.size == AES_GCM_NONCE_LENGTH) { "Nonce must be $AES_GCM_NONCE_LENGTH bytes" }

        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        val keySpec = SecretKeySpec(key, "AES")
        val gcmSpec = GCMParameterSpec(AES_GCM_TAG_LENGTH, actualNonce)

        cipher.init(Cipher.ENCRYPT_MODE, keySpec, gcmSpec)
        val ciphertext = cipher.doFinal(plaintext)

        return Pair(ciphertext, actualNonce)
    }

    /**
     * Decrypt data using AES-256-GCM.
     *
     * @param ciphertext Encrypted data with auth tag
     * @param key 32-byte decryption key
     * @param nonce 12-byte nonce used during encryption
     * @return Decrypted plaintext
     */
    fun decryptAesGcm(
        ciphertext: ByteArray,
        key: ByteArray,
        nonce: ByteArray
    ): ByteArray {
        require(key.size == KEY_SIZE) { "Key must be $KEY_SIZE bytes" }
        require(nonce.size == AES_GCM_NONCE_LENGTH) { "Nonce must be $AES_GCM_NONCE_LENGTH bytes" }

        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        val keySpec = SecretKeySpec(key, "AES")
        val gcmSpec = GCMParameterSpec(AES_GCM_TAG_LENGTH, nonce)

        cipher.init(Cipher.DECRYPT_MODE, keySpec, gcmSpec)
        return cipher.doFinal(ciphertext)
    }

    /**
     * Create device secret from random seed and Android ID.
     * The inputs are discarded after hashing - only the secret is stored.
     *
     * @param androidId Device's ANDROID_ID
     * @return 32-byte device secret
     */
    fun createDeviceSecret(androidId: String): ByteArray {
        val randomSeed = generateRandomBytes(KEY_SIZE)
        val combined = randomSeed + androidId.toByteArray(Charsets.UTF_8)
        return sha256(combined)
        // Note: randomSeed and androidId are discarded here (not stored)
    }

    /**
     * Create camera token (encrypted device secret) for a photo submission.
     *
     * @param deviceSecret 32-byte device secret
     * @param masterKeys List of 3 master keys for assigned tables
     * @param tableIndices Global indices of assigned tables
     * @return Triple of (encrypted token, global table index, key index, nonce)
     */
    fun createCameraToken(
        deviceSecret: ByteArray,
        masterKeys: List<ByteArray>,
        tableIndices: List<Int>
    ): CameraToken {
        require(masterKeys.size == 3) { "Must have 3 master keys" }
        require(tableIndices.size == 3) { "Must have 3 table indices" }

        // Randomly select one of 3 assigned tables
        val localTableIndex = secureRandom.nextInt(3)
        val globalTableIndex = tableIndices[localTableIndex]
        val masterKey = masterKeys[localTableIndex]

        // Randomly select a key from that table
        val keyIndex = secureRandom.nextInt(KEYS_PER_TABLE)

        // Derive encryption key
        val encryptionKey = deriveKey(masterKey, keyIndex)

        // Encrypt device secret
        val (ciphertext, nonce) = encryptAesGcm(deviceSecret, encryptionKey)

        return CameraToken(
            encryptedToken = ciphertext,
            tableIndex = globalTableIndex,
            keyIndex = keyIndex,
            nonce = nonce
        )
    }

    /**
     * Encode bytes to Base64 string.
     */
    fun encodeBase64(bytes: ByteArray): String {
        return Base64.encodeToString(bytes, Base64.NO_WRAP)
    }

    /**
     * Decode Base64 string to bytes.
     */
    fun decodeBase64(base64: String): ByteArray {
        return Base64.decode(base64, Base64.NO_WRAP)
    }
}

/**
 * Result of camera token creation.
 */
data class CameraToken(
    val encryptedToken: ByteArray,
    val tableIndex: Int,
    val keyIndex: Int,
    val nonce: ByteArray
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false
        other as CameraToken
        return encryptedToken.contentEquals(other.encryptedToken) &&
               tableIndex == other.tableIndex &&
               keyIndex == other.keyIndex &&
               nonce.contentEquals(other.nonce)
    }

    override fun hashCode(): Int {
        var result = encryptedToken.contentHashCode()
        result = 31 * result + tableIndex
        result = 31 * result + keyIndex
        result = 31 * result + nonce.contentHashCode()
        return result
    }
}
