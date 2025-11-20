//
//  KeychainService.swift
//  BirthmarkCamera
//
//  Secure storage for device fingerprint and keys using iOS Keychain
//

import Foundation
import Security

class KeychainService {
    static let shared = KeychainService()

    private let deviceFingerprintKey = "com.birthmark.device_fingerprint"
    private let deviceSecretKey = "com.birthmark.device_secret"  // Phase 2
    private let tableAssignmentsKey = "com.birthmark.table_assignments"
    private let keyTableIndicesKey = "com.birthmark.key_table_indices"  // Phase 2
    private let keyTablesKey = "com.birthmark.key_tables"  // Phase 2
    private let masterKeysPrefix = "com.birthmark.master_key_"

    private init() {}

    // MARK: - Device Fingerprint (Phase 1)

    func saveDeviceFingerprint(_ fingerprint: String) {
        save(fingerprint, forKey: deviceFingerprintKey)
    }

    func getDeviceFingerprint() -> String? {
        return getString(forKey: deviceFingerprintKey)
    }

    // MARK: - Device Secret (Phase 2)

    /// Save device secret (32-byte hash)
    func saveDeviceSecret(_ secret: Data) {
        save(secret, forKey: deviceSecretKey)
    }

    /// Get device secret
    func getDeviceSecret() -> Data? {
        return getData(forKey: deviceSecretKey)
    }

    // MARK: - Table Assignments (Phase 1)

    func saveTableAssignments(_ assignments: [Int]) {
        let data = try? JSONEncoder().encode(assignments)
        save(data, forKey: tableAssignmentsKey)
    }

    func getTableAssignments() -> [Int]? {
        guard let data = getData(forKey: tableAssignmentsKey) else { return nil }
        return try? JSONDecoder().decode([Int].self, from: data)
    }

    // MARK: - Key Table Indices (Phase 2)

    /// Save global key table indices (e.g., [42, 157, 891])
    func saveKeyTableIndices(_ indices: [Int]) {
        let data = try? JSONEncoder().encode(indices)
        save(data, forKey: keyTableIndicesKey)
    }

    /// Get global key table indices
    func getKeyTableIndices() -> [Int]? {
        guard let data = getData(forKey: keyTableIndicesKey) else { return nil }
        return try? JSONDecoder().decode([Int].self, from: data)
    }

    // MARK: - Key Tables (Phase 2)

    /// Save all key tables (3 tables × 1000 keys each)
    /// Each key is 32 bytes, stored as hex string for JSON encoding
    func saveKeyTables(_ tables: [[String]]) {
        let data = try? JSONEncoder().encode(tables)
        save(data, forKey: keyTablesKey)
    }

    /// Get all key tables
    func getKeyTables() -> [[String]]? {
        guard let data = getData(forKey: keyTablesKey) else { return nil }
        return try? JSONDecoder().decode([[String]].self, from: data)
    }

    /// Get specific key from loaded tables
    /// - Parameters:
    ///   - localTableIndex: Local table index (0-2)
    ///   - keyIndex: Key index within table (0-999)
    /// - Returns: Key data (32 bytes)
    func getKey(localTableIndex: Int, keyIndex: Int) -> Data? {
        guard let tables = getKeyTables(),
              localTableIndex < tables.count,
              keyIndex < tables[localTableIndex].count else {
            return nil
        }

        let hexKey = tables[localTableIndex][keyIndex]
        return Data(hex: hexKey)
    }

    // MARK: - Master Keys (Phase 1)

    func saveMasterKey(_ key: Data, forTable tableId: Int) {
        save(key, forKey: masterKeysPrefix + "\(tableId)")
    }

    func getMasterKey(forTable tableId: Int) -> Data? {
        return getData(forKey: masterKeysPrefix + "\(tableId)")
    }

    // MARK: - Generic Keychain Operations

    private func save(_ string: String, forKey key: String) {
        guard let data = string.data(using: .utf8) else { return }
        save(data, forKey: key)
    }

    private func save(_ data: Data?, forKey key: String) {
        guard let data = data else { return }

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlock
        ]

        // Delete existing item
        SecItemDelete(query as CFDictionary)

        // Add new item
        let status = SecItemAdd(query as CFDictionary, nil)
        if status != errSecSuccess {
            print("Keychain save error for \(key): \(status)")
        }
    }

    private func getString(forKey key: String) -> String? {
        guard let data = getData(forKey: key) else { return nil }
        return String(data: data, encoding: .utf8)
    }

    private func getData(forKey key: String) -> Data? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        if status == errSecSuccess {
            return result as? Data
        } else {
            return nil
        }
    }

    func deleteAll() {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword
        ]
        SecItemDelete(query as CFDictionary)
    }
}

// MARK: - Data Hex Extension

extension Data {
    /// Initialize Data from hex string
    init?(hex: String) {
        let len = hex.count / 2
        var data = Data(capacity: len)
        var i = hex.startIndex
        for _ in 0..<len {
            let j = hex.index(i, offsetBy: 2)
            let bytes = hex[i..<j]
            if var num = UInt8(bytes, radix: 16) {
                data.append(&num, count: 1)
            } else {
                return nil
            }
            i = j
        }
        self = data
    }

    /// Convert Data to hex string
    var hexString: String {
        return map { String(format: "%02hhx", $0) }.joined()
    }
}
