//
//  ContentView.swift
//  MyDiscipline
//
//  UI:
//   - "Block other apps" opens the system app picker. Confirming the selection
//     immediately applies the shield, so the chosen apps can't be opened.
//   - A big circular toggle button: GREEN (blocking → press to RELEASE all
//     apps) / RED (released → press to re-lock the same apps).
//

import SwiftUI
import FamilyControls

struct ContentView: View {
    @StateObject private var manager = BlockManager()
    @State private var showingPicker = false

    var body: some View {
        VStack(spacing: 32) {
            Spacer()

            // Status line
            VStack(spacing: 6) {
                Text("MyDiscipline")
                    .font(.title2.bold())
                Text(manager.isBlocking
                     ? "Selected apps are blocked."
                     : "No active block.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            // Big circular toggle button.
            // Per spec: GREEN button = release all locks; RED button = re-lock.
            Button {
                manager.toggle()
            } label: {
                Circle()
                    .fill(manager.isBlocking ? Color.green : Color.red)
                    .frame(width: 200, height: 200)
                    .overlay(
                        Text(manager.isBlocking ? "RELEASE" : "BLOCK")
                            .font(.system(size: 26, weight: .bold))
                            .foregroundStyle(.white)
                    )
                    .shadow(radius: 6, y: 3)
            }
            .accessibilityIdentifier("toggleButton")
            .accessibilityLabel(manager.isBlocking ? "Release blocked apps" : "Block selected apps")
            .disabled(!manager.hasSelection)
            .opacity(manager.hasSelection ? 1.0 : 0.5)

            Spacer()

            // Choose which apps to block.
            Button {
                showingPicker = true
            } label: {
                Label("Block other apps", systemImage: "shield.lefthalf.filled")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 16))
            }
            .accessibilityIdentifier("blockOtherAppsButton")
        }
        .padding(24)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(.systemBackground))
        .task {
            await manager.requestAuthorization()
        }
        .familyActivityPicker(
            isPresented: $showingPicker,
            selection: Binding(
                get: { manager.selection },
                // When the user confirms the picker, record the selection and
                // immediately lock those apps so they can't be opened until the
                // green button is pressed.
                set: {
                    manager.setSelected($0)
                    if manager.hasSelection {
                        manager.applyShield()
                    }
                }
            )
        )
    }
}

#Preview {
    ContentView()
}
