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
    private let tableAssignmentsKey = "com.birthmark.table_assignments"
    private let masterKeysPrefix = "com.birthmark.master_key_"

    private init() {}

    // MARK: - Device Fingerprint

    func saveDeviceFingerprint(_ fingerprint: String) {
        save(fingerprint, forKey: deviceFingerprintKey)
    }

    func getDeviceFingerprint() -> String? {
        return getString(forKey: deviceFingerprintKey)
    }

    // MARK: - Table Assignments

    func saveTableAssignments(_ assignments: [Int]) {
        let data = try? JSONEncoder().encode(assignments)
        save(data, forKey: tableAssignmentsKey)
    }

    func getTableAssignments() -> [Int]? {
        guard let data = getData(forKey: tableAssignmentsKey) else { return nil }
        return try? JSONDecoder().decode([Int].self, from: data)
    }

    // MARK: - Master Keys

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
