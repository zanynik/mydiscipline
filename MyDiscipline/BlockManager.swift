//
//  BlockManager.swift
//  MyDiscipline
//
//  Owns the Screen Time authorization state and the ManagedSettings shield
//  that blocks the user-selected apps. The shield lives in a named
//  ManagedSettingsStore, which the system persists across app launches, so a
//  block survives a kill/restart of the app until the user releases it.
//

import Foundation
import FamilyControls
import ManagedSettings

@MainActor
final class BlockManager: ObservableObject {

    /// The apps/categories the user picked. Kept in memory only (tokens are
    /// opaque and can't be persisted to disk by the app), so we re-read the
    /// *effective* shield from the store on launch to know whether we're
    /// currently blocking.
    @Published var selection = FamilyActivitySelection()

    /// True while the selected apps are actively blocked.
    @Published private(set) var isBlocking = false

    /// True once the user has chosen at least one app to block.
    @Published private(set) var hasSelection = false

    private let store = ManagedSettingsStore(named: .init("MyDisciplineShield"))

    init() {
        // Sync our state from whatever the system currently has applied. The
        // store persists shields across launches, so after a restart we want
        // the toggle button to reflect reality.
        isBlocking = !(store.shield.applications?.isEmpty ?? true)
    }

    /// Request Screen Time authorization. Must be called before any picker or
    /// shield API is used. Safe to call multiple times.
    func requestAuthorization() async {
        do {
            try await AuthorizationCenter.shared.requestAuthorization(for: .individual)
        } catch {
            // The user may decline; the UI will show an appropriate state.
            print("FamilyControls authorization failed: \(error.localizedDescription)")
        }
    }

    /// Called when the user finishes picking apps in FamilyActivityPicker.
    func setSelected(_ newSelection: FamilyActivitySelection) {
        selection = newSelection
        hasSelection = !newSelection.applicationTokens.isEmpty
            || !newSelection.categoryTokens.isEmpty
            || !newSelection.webDomainTokens.isEmpty
    }

    /// Block the currently selected apps immediately.
    func applyShield() {
        guard hasSelection else { return }
        store.shield.applications = selection.applicationTokens
        store.shield.applicationCategories = .specific(selection.categoryTokens)
        store.shield.webDomains = selection.webDomainTokens
        isBlocking = true
    }

    /// Release every block applied by this store.
    func clearShield() {
        store.shield.applications = nil
        store.shield.applicationCategories = nil
        store.shield.webDomains = nil
        isBlocking = false
    }

    /// Toggle between blocking and released. Returns the new state.
    @discardableResult
    func toggle() -> Bool {
        if isBlocking {
            clearShield()
        } else {
            applyShield()
        }
        return isBlocking
    }
}
