# MyDiscipline

A minimal native SwiftUI iOS app that blocks the apps you choose using Apple's
**Screen Time API**, with a single big toggle to release or re-apply the block.

Built as a feasibility test for the "block other apps" pattern (à la Duolingo).

## How it works

1. Tap **Block other apps** → the system app picker (`FamilyActivityPicker`)
   opens. Select the apps you want to block and confirm.
2. The selected apps are **immediately shielded** — you can no longer open them.
3. The big circular button is **GREEN** while apps are blocked.
   - Tap it to **release** every lock. The button turns **RED**.
4. Tap the **RED** button to **re-lock** the same apps. Repeat.

The shields live in a named `ManagedSettingsStore`, so a block survives an app
kill/restart until you explicitly release it.

## Tech

- SwiftUI, iOS 16+
- `FamilyControls` (authorization + picker) and `ManagedSettings` (the shield).
  No `DeviceActivity` — the toggle is instant on/off, not scheduled.
- [XcodeGen](https://github.com/yonaskolb/XcodeGen) — the `.xcodeproj` is
  generated from `project.yml`, so it isn't committed.

## Run it locally (on a Mac, on a physical iPhone)

> The Screen Time API **does not work on the Simulator** — authorization,
> picker, and shields only function on real devices. Local development builds
> work immediately (no Apple approval needed).

```bash
brew install xcodegen
xcodegen generate
open MyDiscipline.xcodeproj
```

Then select your iPhone, set a development team in **Signing & Capabilities**,
and Run.

## ⚠️ Family Controls is a restricted entitlement

The CI workflow enables the **Family Controls** capability on the App ID via
the App Store Connect API, which makes the build sign and upload. But for the
feature to actually *function in a TestFlight build*, Apple must separately
approve the distribution entitlement (per bundle id, typically a few days):

➡️ [Request the Family Controls distribution entitlement](https://developer.apple.com/contact/request/privacy-and-data/)

Until then, in TestFlight `AuthorizationCenter.requestAuthorization(...)` may be
denied. Local dev builds are unaffected.

## CI / TestFlight

`.github/workflows/pub-testflight-ios.yml` (adapted from
[`zanynik/slowclaw.social`](https://github.com/zanynik/slowclaw.social)) runs on
`macos-26` and:

1. Installs XcodeGen, regenerates the project.
2. Enables **FAMILY_CONTROLS** on the App ID (idempotent; 409 = already on).
3. Mints a fresh **Apple Distribution** cert + **App Store** provisioning profile
   on the fly via the App Store Connect API.
4. `xcodebuild archive` + `-exportArchive` → signed IPA.
5. `xcrun altool --upload-app` → TestFlight.

Triggers: push to `main` (when `MyDiscipline/`, `project.yml`, or the workflow
changes), or a manual **workflow_dispatch** run.

### Prerequisites in GitHub

| Variable / Secret | Kind | Purpose |
| --- | --- | --- |
| `APP_STORE_CONNECT_ISSUER_ID` | secret | ASC API key issuer (already used by `create-app-store-app.yml`) |
| `APP_STORE_CONNECT_KEY_ID` | secret | ASC API key id |
| `APP_STORE_CONNECT_PRIVATE_KEY` | secret | `.p8` contents (raw base64 body or full PEM) |
| `APPLE_DEVELOPMENT_TEAM` | **variable** (or secret) | 10-char Team ID |

The API key must be **Admin** or **App Manager** role (to create certs/profiles
and enable capabilities). A `macOS` environment is already referenced.

## Project layout

```
project.yml                      # XcodeGen spec → MyDiscipline.xcodeproj
MyDiscipline/
  MyApp.swift                    # @main entry
  ContentView.swift              # UI: "Block other apps" + green/red toggle
  BlockManager.swift             # Screen Time auth + apply/clear shields
  Info.plist
  MyDiscipline.entitlements      # com.apple.developer.family-controls
  Assets.xcassets/               # AppIcon + AccentColor
.github/workflows/pub-testflight-ios.yml
scripts/make_appicon.py          # regenerates the 1024px AppIcon
```

`scripts/make_appicon.py` regenerates the placeholder app icon with Pillow
(`pip install Pillow`).

## Sources

- [Screen Time Technology Frameworks – Apple Developer](https://developer.apple.com/documentation/screentimeapidocumentation)
- [Meet the Screen Time API – WWDC21](https://developer.apple.com/videos/play/wwdc2021/10123/)
- [A Developer's Guide to Apple's Screen Time APIs](https://medium.com/@juliusbrussee/a-developer-guide-to-apple-s-screen-time-apis-familycontrols-managedsettings-deviceactivity-e660147367d7)
- [FamilyControls – request the entitlement](https://developer.apple.com/documentation/familycontrols/requesting-the-family-controls-entitlement)
