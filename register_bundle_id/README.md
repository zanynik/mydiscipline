# register_bundle_id

Register a **bundle ID (App ID)** in the Apple Developer Portal from CI using
an **App Store Connect API key** — no Apple ID or password required.

Calls Apple's [`POST /v1/bundleIds`](https://developer.apple.com/documentation/appstoreconnectapi/post-v1-bundleids)
endpoint directly. Reusable across projects.

## Why not fastlane `produce`?

In fastlane 2.236.x, `produce` authenticates only via the **legacy Apple
Developer Portal web session** (Apple ID + password), not the App Store
Connect API. So it cannot be driven by an API key in a non-interactive CI run
(it errors with `[!] No value found for 'username'` or prompts for a password).

There is **no fastlane action** that registers a bundle ID via the modern API,
so this script calls the endpoint directly. See
[fastlane/fastlane#29435](https://github.com/fastlane/fastlane/issues/29435)
and [discussion #17889](https://github.com/fastlane/fastlane/discussions/17889).

## Secrets required

Store these as repository/environment secrets (the names are just a convention;
the workflow maps them onto what the script reads):

| Secret | Meaning |
|--------|---------|
| `APP_STORE_CONNECT_KEY_ID` | API key ID |
| `APP_STORE_CONNECT_ISSUER_ID` | Issuer ID |
| `APP_STORE_CONNECT_PRIVATE_KEY` | `.p8` contents — full PEM **or** just the raw base64 body |

The API key must have the **Admin** role (App Manager may also work; Admin is
guaranteed). Bundle identifiers are **globally unique across all of Apple**, so
pick a reverse-DNS string under a domain you control (e.g. `com.yourname.app`).

## Usage locally

```bash
export APP_STORE_CONNECT_API_KEY_KEY_ID=...
export APP_STORE_CONNECT_API_KEY_ISSUER_ID=...
export APP_STORE_CONNECT_API_KEY_KEY_CONTENT="$(cat AuthKey_XXXXXXXXXX.p8)"
BUNDLE_ID=com.example.app BUNDLE_NAME="Example" python3 register_bundle_id.py
```

## Usage in GitHub Actions

Copy the workflow below into the target repo's
`.github/workflows/register_bundle_id.yml`, then run it via **Actions → Run
workflow** (it's `workflow_dispatch` — manual trigger only).

```yaml
name: Register bundle ID

on:
  workflow_dispatch:

jobs:
  register_bundle_id:
    runs-on: macos-latest
    environment: macOS          # env holding your 3 API-key secrets
    env:
      APP_STORE_CONNECT_API_KEY_KEY_ID: ${{ secrets.APP_STORE_CONNECT_KEY_ID }}
      APP_STORE_CONNECT_API_KEY_ISSUER_ID: ${{ secrets.APP_STORE_CONNECT_ISSUER_ID }}
      APP_STORE_CONNECT_API_KEY_KEY_CONTENT: ${{ secrets.APP_STORE_CONNECT_PRIVATE_KEY }}
    steps:
      - uses: actions/checkout@v4
      - name: Register bundle ID
        env:
          BUNDLE_ID: "com.example.app"      # <-- change per project
          BUNDLE_NAME: "Example"
        run: python3 register_bundle_id/register_bundle_id.py
```

> GitHub only runs workflows from `.github/workflows/`, so the YAML must live
> there even though the script + this README live in `register_bundle_id/`.

## What it does

1. Builds an ES256 JWT from the three API-key values (stdlib + `cryptography`,
   which is preinstalled on GitHub's macOS runners).
2. `POST /v1/bundleIds` with `{ identifier, name, platform }`.
3. On `201` → registered. On `409 ENTITY_ERROR.ATTRIBUTE.INVALID` → the
   identifier already exists; it then does a `GET /v1/bundleIds?filter[identifier]=…`
   to report whether it belongs to **your team** or **another team**.

The script is idempotent in the sense that re-running on an identifier that's
already yours exits 0; re-running on one owned by another team reports it as
taken (and exits 0 from the registration standpoint — see the note below).

## Notes

- **Platform** defaults to `IOS`. Override with `BUNDLE_PLATFORM=MAC_OS` or
  `UNIVERSAL`. (Apple may normalize `IOS` to `UNIVERSAL` in the response.)
- **"Already registered to another team" exits 0.** The script treats a
  globally-taken identifier as non-fatal because, from the registration
  endpoint's perspective, there's nothing to create. Check the run log — the
  lookup line tells you the ownership status explicitly.
- One-off by nature: once a bundle ID is registered it stays forever, so you
  only run this once per project.
