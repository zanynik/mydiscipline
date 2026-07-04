#!/usr/bin/env python3
"""
Register a bundle ID (App ID) in the Apple Developer Portal via the
App Store Connect API (POST /v1/bundleIds).

Authenticates with an App Store Connect API key (ES256 JWT) built from
the APP_STORE_CONNECT_API_KEY_* env vars. No Apple ID / password needed.

This is a one-off: run once to register the bundle ID, then this script
(and the workflow that calls it) can be removed.

Env vars (mapped in the GitHub Actions workflow from repo secrets):
  APP_STORE_CONNECT_API_KEY_KEY_ID        -> key id
  APP_STORE_CONNECT_API_KEY_ISSUER_ID     -> issuer id
  APP_STORE_CONNECT_API_KEY_KEY_CONTENT   -> .p8 private key (PEM or raw base64 body)

Reference: https://developer.apple.com/documentation/appstoreconnectapi/post-v1-bundleids
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

# --- config (override via env if ever needed) ---
BUNDLE_ID = os.environ.get("BUNDLE_ID", "com.mydiscipline.app")
BUNDLE_NAME = os.environ.get("BUNDLE_NAME", "MyDiscipline")
PLATFORM = os.environ.get("BUNDLE_PLATFORM", "IOS")  # IOS | MAC_OS | UNIVERSAL
API_BASE = "https://api.appstoreconnect.apple.com"


def die(msg, code=1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def load_private_key(raw):
    """Accept either a full PEM string or the raw base64 body of the .p8 key."""
    raw = raw.strip()
    if "PRIVATE KEY" in raw:
        return raw
    # Wrap a bare base64 body in PEM framing.
    body = raw.replace(" ", "").replace("\n", "").replace("\r", "")
    return (
        "-----BEGIN PRIVATE KEY-----\n"
        + "\n".join(body[i:i + 64] for i in range(0, len(body), 64))
        + "\n-----END PRIVATE KEY-----\n"
    )


def make_jwt(key_id, issuer_id, private_key_pem):
    """Build an ES256 JWT for App Store Connect. Stdlib only (no third-party deps)."""
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.asymmetric.utils import (
            decode_dss_signature,
        )
        import base64
    except ImportError:
        die("The 'cryptography' package is required. It is preinstalled on GitHub's "
            "macOS runners; elsewhere run: pip install cryptography")

    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    header = {"alg": "ES256", "kid": key_id, "typ": "JWT"}
    now = int(time.time())
    payload = {
        "iss": issuer_id,
        "iat": now,
        "exp": now + 20 * 60,  # 20 min, the Apple-recommended max
        "aud": "appstoreconnect-v1",
    }
    signing_input = (
        b64url(json.dumps(header, separators=(",", ":")).encode())
        + "."
        + b64url(json.dumps(payload, separators=(",", ":")).encode())
    )

    private_key = serialization.load_pem_private_key(
        private_key_pem.encode(), password=None
    )
    der_sig = private_key.sign(signing_input.encode(), ec.ECDSA(hashes.SHA256()))
    # Convert ASN.1 DER r||s to the raw r||s concatenated form JWT requires.
    r, s = decode_dss_signature(der_sig)
    raw_sig = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    return signing_input + "." + b64url(raw_sig)


def register_bundle_id(jwt):
    url = f"{API_BASE}/v1/bundleIds"
    body = {
        "data": {
            "type": "bundleIds",
            "attributes": {
                "name": BUNDLE_NAME,
                "identifier": BUNDLE_ID,
                "platform": PLATFORM,
            },
        }
    }
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {jwt}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            status = resp.getcode()
            text = resp.read().decode()
    except urllib.error.HTTPError as e:
        status = e.code
        text = e.read().decode()
        # Apple returns 409 with ENTITY_ERROR.ATTRIBUTE.INVALID and a message like
        # "An App ID with Identifier '...' is not available" when the identifier is
        # already registered (by anyone, globally — bundle identifiers are unique
        # across all of Apple). For our one-off purpose that is a benign outcome.
        already_taken = (
            status == 409
            and ("ENTITY_ERROR.ATTRIBUTE.INVALID" in text)
            and ("not available" in text.lower() or "already" in text.lower())
        )
        if already_taken:
            print(f"Bundle ID '{BUNDLE_ID}' is already registered (not available).")
            print(f"ASC response ({status}): {text}")
            # Try to confirm it belongs to this team via a lookup GET.
            lookup(jwt)
            return 0
        print(f"ASC API error {status}:", file=sys.stderr)
        print(text, file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"Network error: {e}", file=sys.stderr)
        return 1

    if 200 <= status < 300:
        print(f"SUCCESS: registered bundle ID '{BUNDLE_ID}' (platform {PLATFORM}).")
        print(f"ASC response ({status}): {text}")
        return 0
    print(f"Unexpected status {status}:", file=sys.stderr)
    print(text, file=sys.stderr)
    return 1


def lookup(jwt):
    """GET /v1/bundleIds filtered by identifier, to confirm the existing App ID
    is visible to (and therefore registered to) this team."""
    import urllib.parse
    url = (
        f"{API_BASE}/v1/bundleIds?filter%5Bidentifier%5D="
        + urllib.parse.quote(BUNDLE_ID)
    )
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {jwt}",
            "Accept": "application/json",
        },
    )
    print(f"\nLooking up '{BUNDLE_ID}' via GET /v1/bundleIds ...")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  lookup failed ({e.code}); the identifier is registered outside "
              f"this team or the key lacks read access.", file=sys.stderr)
        print(f"  {e.read().decode()}", file=sys.stderr)
        return
    except urllib.error.URLError as e:
        print(f"  lookup network error: {e}", file=sys.stderr)
        return

    items = data.get("data", [])
    if not items:
        print(f"  '{BUNDLE_ID}' is registered to ANOTHER team (not visible to this key).")
        return
    for it in items:
        bid = it.get("id")
        attrs = it.get("attributes", {})
        print(f"  FOUND in this team: id={bid} identifier={attrs.get('identifier')} "
              f"name={attrs.get('name')} platform={attrs.get('platform')} "
              f"status={attrs.get('status')}")


def main():
    key_id = os.environ.get("APP_STORE_CONNECT_API_KEY_KEY_ID", "").strip()
    issuer_id = os.environ.get("APP_STORE_CONNECT_API_KEY_ISSUER_ID", "").strip()
    key_content = os.environ.get("APP_STORE_CONNECT_API_KEY_KEY_CONTENT", "").strip()

    print(f"key_id present: {bool(key_id)}")
    print(f"issuer_id present: {bool(issuer_id)}")
    print(f"key_content present: {bool(key_content)}")
    print(f"target bundle id: {BUNDLE_ID} ({PLATFORM})")
    if not (key_id and issuer_id and key_content):
        die("Missing one or more API key env vars (see script header).")

    pem = load_private_key(key_content)
    jwt = make_jwt(key_id, issuer_id, pem)
    print("Built JWT (length %d). Registering bundle ID..." % len(jwt))
    sys.exit(register_bundle_id(jwt))


if __name__ == "__main__":
    main()
