#!/usr/bin/env bash
# Journey: specs/journeys/JOURNEY-release-publication.md
# Build an unsigned release, align it, then sign with credentials from the environment.
set -euo pipefail

: "${SYAUTH_RELEASE_KEYSTORE:?SYAUTH_RELEASE_KEYSTORE is required}"
: "${SYAUTH_RELEASE_KEYSTORE_PASSWORD:?SYAUTH_RELEASE_KEYSTORE_PASSWORD is required}"

VERSION="${VERSION:-0.3.0}"
if [[ ! "$VERSION" =~ ^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]]; then
    echo "Error: VERSION must be a numeric major.minor.patch" >&2
    exit 1
fi
export VERSION

if [[ ! -f "$SYAUTH_RELEASE_KEYSTORE" ]]; then
    echo "Error: Signing keystore does not exist" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SDK_ROOT="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
BUILD_TOOLS="$SDK_ROOT/build-tools/${ANDROID_BUILD_TOOLS_VERSION:-34.0.0}"
if [[ ! -x "$BUILD_TOOLS/zipalign" || ! -x "$BUILD_TOOLS/apksigner" ]]; then
    echo "Error: Android build tools are missing; set ANDROID_HOME and install build-tools;34.0.0" >&2
    exit 1
fi

SYAUTH_RELEASE_KEY_ALIAS="${SYAUTH_RELEASE_KEY_ALIAS:-syauth}"
export SYAUTH_RELEASE_KEY_PASSWORD="${SYAUTH_RELEASE_KEY_PASSWORD:-$SYAUTH_RELEASE_KEYSTORE_PASSWORD}"
OUTPUT_DIR="$PROJECT_ROOT/target/release-artifacts"
mkdir -p "$OUTPUT_DIR"
SIGNING_DIR="$(mktemp -d "$OUTPUT_DIR/.android-sign.XXXXXXXX")"
trap 'rm -rf "$SIGNING_DIR"' EXIT

echo "==> Building Android release $VERSION"
(
    cd "$PROJECT_ROOT/syauth-android"
    ./gradlew :app:assembleRelease --console=plain "$@"
)
UNSIGNED="$PROJECT_ROOT/syauth-android/app/build/outputs/apk/release/app-release-unsigned.apk"
"$BUILD_TOOLS/zipalign" -p -f 4 "$UNSIGNED" "$SIGNING_DIR/aligned.apk"
"$BUILD_TOOLS/apksigner" sign \
    --ks "$SYAUTH_RELEASE_KEYSTORE" \
    --ks-key-alias "$SYAUTH_RELEASE_KEY_ALIAS" \
    --ks-pass env:SYAUTH_RELEASE_KEYSTORE_PASSWORD \
    --key-pass env:SYAUTH_RELEASE_KEY_PASSWORD \
    --out "$SIGNING_DIR/signed.apk" "$SIGNING_DIR/aligned.apk"
"$BUILD_TOOLS/apksigner" verify --verbose --print-certs "$SIGNING_DIR/signed.apk" > "$SIGNING_DIR/certificate.txt"
"$BUILD_TOOLS/zipalign" -c -v 4 "$SIGNING_DIR/signed.apk" > /dev/null
EXPECTED_CERTIFICATE="$PROJECT_ROOT/deploy/android-release-signing.pem"
EXPECTED_DIGEST="$(openssl x509 -in "$EXPECTED_CERTIFICATE" -noout -fingerprint -sha256 | cut -d= -f2 | tr -d ':' | tr '[:upper:]' '[:lower:]')"
ACTUAL_DIGEST="$(sed -n 's/^Signer #1 certificate SHA-256 digest: //p' "$SIGNING_DIR/certificate.txt")"
if [[ "$ACTUAL_DIGEST" != "$EXPECTED_DIGEST" || ! "$ACTUAL_DIGEST" =~ ^[0-9a-f]{64}$ ]]; then
    echo "Error: Signing certificate does not match deploy/android-release-signing.pem" >&2
    exit 1
fi

mv "$SIGNING_DIR/signed.apk" "$OUTPUT_DIR/syauth-$VERSION-android.apk"
mv "$SIGNING_DIR/certificate.txt" "$OUTPUT_DIR/android-signing-certificate.txt"
cp "$EXPECTED_CERTIFICATE" "$OUTPUT_DIR/android-signing-certificate.pem"
echo "==> Verified signed APK: $OUTPUT_DIR/syauth-$VERSION-android.apk"
