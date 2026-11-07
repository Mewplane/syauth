# Build and publish a release

The [release workflow](https://github.com/dmytrogajewski/syauth/actions/workflows/release.yml) builds native Linux packages and a signed Android APK from the same source revision. Pushes to `release/**` branches and manual workflow runs validate and upload artifacts without creating a public release. A `vMAJOR.MINOR.PATCH` tag publishes after every build and package-install check passes.

## Artifact contract

For version `0.2.0`, [GitHub Releases](https://github.com/dmytrogajewski/syauth/releases/tag/v0.2.0) contains:

| Artifact | Consumer |
| --- | --- |
| `syauth_0.2.0_amd64.deb`, `syauth_0.2.0_arm64.deb` | Debian / Ubuntu and compatible derivatives |
| `syauth-0.2.0-4.x86_64.rpm`, `syauth-0.2.0-4.aarch64.rpm` | Fedora / openSUSE and compatible RPM systems |
| `syauth-0.2.0-1-x86_64.pkg.tar.zst`, `syauth-0.2.0-1-aarch64.pkg.tar.zst` | Arch package-manager installations; ARM64 requires an appropriate Arch Linux ARM system |
| `syauth-0.2.0-linux-{x86_64,aarch64}.tar.gz` | Manual installation / inspection |
| `syauth-0.2.0-android.apk` | Android companion, signed with the persistent release key |
| `syauth-0.2.0-source.tar.gz` | Tagged project sources |
| `install.sh` | Version-selecting, checksum-verifying shell installer |
| `android-signing-certificate.pem`, `android-signing-certificate.txt` | Public signing identity and APK verification output |
| `release.json`, `SHA256SUMS` | Source revision, file sizes, SHA-256 digests |

Linux binaries are built on Debian 12 for glibc 2.36 or later. The workflow checks real install, reinstall, execution, shared-library resolution, state preservation, PAM permissions, user-unit paths, unchanged PAM configuration, and removal. Its matrix covers Debian 12 and Fedora on both CPUs, plus Ubuntu 24.04, Arch, and openSUSE on x86_64. Package format availability is broader than this tested matrix.

## Linux builds

Build the three desktop outputs and package them on the target CPU:

```sh
cargo build --locked --release -p syauth-cli -p syauth-pam -p syauth-presenced
scripts/build-linux-packages.sh --version 0.2.0 --arch x86_64 \
  --binaries target/release --output target/release-artifacts
scripts/test-package-install.sh target/release-artifacts 0.2.0 x86_64 debian
```

Use `--arch aarch64` for ARM64 binaries. The packager downloads checksum-pinned nFPM 2.47.0; it does not install build tools globally. Building on a newer distribution can raise the required glibc version, so use the workflow's Debian 12 build environment for published artifacts.

The canonical release path is `scripts/build-linux-packages.sh` and `scripts/build-release-apk.sh`. Older generated Makefile packaging targets retain their historical mock/pbuilder paths and are not used by release CI.

## Android builds and signing

The workflow installs JDK 21, Android platform 34, Build Tools 34.0.0, NDK 28.0.13004108, cargo-ndk 4.1.2, and all four Rust Android targets. `scripts/build_aar.sh` builds arm64-v8a, armeabi-v7a, x86_64, and x86 libraries and generates Kotlin bindings with the checked-in UniFFI 0.29.5 helper.

```sh
NDK_HOME="$ANDROID_HOME/ndk/28.0.13004108" scripts/build_aar.sh
VERSION=0.2.0 scripts/build-release-apk.sh
```

The signing script requires `SYAUTH_RELEASE_KEYSTORE` and `SYAUTH_RELEASE_KEYSTORE_PASSWORD`; the key alias defaults to `syauth`. Keep private material outside the checkout. The protected GitHub environment `release` stores `SYAUTH_RELEASE_KEYSTORE_BASE64` and `SYAUTH_RELEASE_KEYSTORE_PASSWORD`. Its key persists across releases; replacing it prevents ordinary Android updates from trusting the old installation.

The script builds the unsigned release, aligns it, signs it, verifies the signature and alignment, and compares its certificate with `deploy/android-release-signing.pem`. Missing credentials or a mismatched certificate fail the build. `VERSION` sets the Android version name and a monotonically encoded version code; `ANDROID_VERSION_CODE` provides an explicit override when required.

The public release certificate's SHA-256 fingerprint is:

```text
25:58:5E:64:1E:DB:3D:A8:7B:98:90:56:B3:D1:65:CA:C2:AF:AF:2A:AE:DD:35:87:56:66:B5:21:EC:C0:22:1C
```

## Publish and verify

1. Update the workspace and release version constants together, update documentation examples, and run `make lint`, `make test`, the Python release/installer tests, and the documentation browser checker.
2. Push the reviewed source and run the release workflow manually against that branch. Inspect the complete artifact and smoke-test results.
3. Merge the reviewed changes and push the matching release tag. The tag must match `[workspace.package].version`.
4. The workflow publishes only after both Linux architectures, signed Android output, and the package-install matrix pass. `release.json` records the source revision. The publishing job verifies all checksums again.
5. Download the published artifacts, verify `SHA256SUMS` and the APK certificate, and check the live Pages installation guide and installer.

The release workflow has write access only in its publishing job. Documentation checks run on pull requests; the Pages deployment job runs only from `master`, with Pages and OIDC permissions. Its deployment URL is [the documentation site](https://dmytrogajewski.github.io/syauth/), also shown in the repository's website field.
