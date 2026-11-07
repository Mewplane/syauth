# Install the desktop and companion app

This guide sets up the desktop daemon and Android companion, then explains how to enable one PAM service. It targets a single desktop account using the default `/var/lib/syauth` store.

## Prerequisites

Use Linux with glibc 2.36+, PAM, systemd user services, BlueZ, and a BLE adapter capable of advertising. Release packages target Debian 12+, Ubuntu 24.04+, and current Fedora, openSUSE, and Arch systems. Both x86_64 and ARM64 artifacts are available; the tested distribution/CPU matrix is listed in [release development](../contributing/releases.md#artifact-contract).

For the phone, use Android 13 / API 33 or later, a supported Ed25519 Keystore implementation, and an enrolled strong biometric. Hardware support varies; StrongBox is requested with a non-StrongBox Keystore fallback. A PIN alone cannot satisfy the unlock signing prompt.

Before enabling PAM, read [security boundaries](../explanation/security.md). Keep an authenticated administrator session open and retain your distribution's existing recovery method while testing.

## Install a release package

Install the latest release with your native package manager:

```sh
curl -fsSL https://mewplane.github.io/syauth/install.sh | sh
```

The POSIX shell installer reads your distribution and architecture, resolves one GitHub release tag, downloads that tag's package and `SHA256SUMS`, checks the exact package digest, then invokes `apt`, `dnf`, `zypper`, or `pacman`. It requests `sudo` when necessary. An unsupported system or checksum mismatch stops installation. It does not change PAM stacks, enable services, or change existing bond ownership.

To inspect the script, select a version, or preview package selection:

```sh
curl -fsSLo install-syauth.sh https://mewplane.github.io/syauth/install.sh
less install-syauth.sh
sh install-syauth.sh --version 0.2.0 --dry-run
sh install-syauth.sh --version 0.2.0
```

### Direct downloads

The [v0.2.0 release](https://github.com/Mewplane/syauth/releases/tag/v0.2.0) has the native packages, manual archives, source, signed APK, and checksums. For example, on Debian/Ubuntu x86_64:

```sh
release=https://github.com/Mewplane/syauth/releases/download/v0.2.0
curl -fSLO "$release/syauth_0.2.0_amd64.deb"
curl -fSLO "$release/SHA256SUMS"
sha256sum --check --ignore-missing SHA256SUMS
sudo apt install ./syauth_0.2.0_amd64.deb
```

Choose the corresponding artifact for other native managers, verify it against the same checksum file, then install it:

| System | x86_64 artifact | Install command |
| --- | --- | --- |
| Fedora | `syauth-0.2.0-4.x86_64.rpm` | `sudo dnf install ./syauth-0.2.0-4.x86_64.rpm` |
| openSUSE | `syauth-0.2.0-4.x86_64.rpm` | `sudo zypper install --allow-unsigned-rpm ./syauth-0.2.0-4.x86_64.rpm` |
| Arch | `syauth-0.2.0-1-x86_64.pkg.tar.zst` | `sudo pacman -U ./syauth-0.2.0-1-x86_64.pkg.tar.zst` |

For ARM64, use the DEB ending in `_arm64.deb`, or the RPM/Arch filename with `aarch64` replacing `x86_64`. The RPM is checksum-verified rather than RPM-signed; the openSUSE command permits that local unsigned RPM without disabling repository checks. These are downloadable native packages, not registered APT/DNF repositories or an AUR listing. Repeat the shell installer to fetch and install a newer release.

Packages install `/usr/bin/syauth`, `/usr/libexec/syauth-presenced`, the distribution's `pam_syauth.so`, and `/usr/lib/systemd/user/syauth-presenced.service`. Continue with storage preparation below.

## Build the desktop from source

Source builds additionally require a Rust toolchain compatible with `Cargo.lock`, a C toolchain, `pkg-config`, and development packages for D-Bus, PAM, and Bluetooth (`libdbus-1-dev`, `libpam0g-dev`, and `libbluetooth-dev` on Debian).

From a checkout of syauth:

```sh
cargo build --locked --release \
  -p syauth-cli -p syauth-pam -p syauth-presenced
```

The build produces `target/release/syauth`, `target/release/syauth-presenced`, and `target/release/libpam_syauth.so`.

Install the binaries:

```sh
sudo install -D -m 755 target/release/syauth /usr/local/bin/syauth
sudo install -D -m 755 target/release/syauth-presenced \
  /usr/local/libexec/syauth-presenced
```

Install the PAM library in your distribution's PAM module directory, with the name `pam_syauth.so`. Find that directory from existing modules; common locations are `/usr/lib/security`, `/usr/lib64/security`, and `/usr/lib/x86_64-linux-gnu/security`. For example, on a host using `/usr/lib64/security`:

```sh
sudo install -m 644 target/release/libpam_syauth.so \
  /usr/lib64/security/pam_syauth.so
```

## Prepare storage and the user service

For a new installation, create the default directories owned by the account that runs the daemon and pairing command:

```sh
sudo install -d -m 700 -o "$(id -un)" -g "$(id -gn)" \
  /var/lib/syauth /var/lib/syauth/keys /var/log/syauth
```

Do not give multiple accounts ownership of the same store. Existing installations should retain their intended ownership; inspect the paths with `syauth doctor` before changing permissions.

For a package installation, the user unit is already installed. Reload and activate it as your desktop user:

```sh
systemctl --user daemon-reload
systemctl --user enable --now syauth-presenced.service
```

For a source installation under `/usr/local`, write a user unit using the installed binary first:

```sh
syauth install-presenced --dry-run \
  --from /usr/local/libexec/syauth-presenced
systemctl --user daemon-reload
systemctl --user enable --now syauth-presenced.service
```

The `--dry-run` command **writes the unit file** but skips the binary copy and `systemctl` calls. This sequence performs the privileged binary installation separately and places the unit in your own user session. There is no `--live` flag. See [configuration](../reference/configuration.md#service-installation) for the installer's other behavior.

## Install the Android app

Download the [signed Android APK](https://github.com/Mewplane/syauth/releases/download/v0.2.0/syauth-0.2.0-android.apk) and [SHA256SUMS](https://github.com/Mewplane/syauth/releases/download/v0.2.0/SHA256SUMS). Verify the downloaded file before opening it on your phone, or install it with ADB:

```sh
sha256sum --check --ignore-missing SHA256SUMS
adb install -r syauth-0.2.0-android.apk
```

With Android SDK Build Tools installed, verify the signature using `apksigner verify --verbose --print-certs syauth-0.2.0-android.apk`. Compare its SHA-256 certificate digest with the [published release signing identity](../contributing/releases.md#android-builds-and-signing). The private signing key is retained across releases. A debug APK uses a different identity and must be uninstalled before installing this release; uninstalling removes its local app data and requires pairing again.

To build from source, provide Android SDK platform 34, JDK 21, NDK 28.0.13004108, cargo-ndk 4.1.2, and the four Rust Android targets required by `scripts/build_aar.sh`. Its checked-in helper generates the matching UniFFI 0.29.5 bindings.

Set `NDK_HOME` to your installed NDK, then run:

```sh
scripts/build_aar.sh
cd syauth-android
./gradlew :app:assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Confirm the AAR exists at `crates/syauth-mobile/target/syauth_mobile.aar` before running Gradle. See [release builds](../contributing/releases.md) for the signing workflow.

Open the app and grant the requested Bluetooth and notification permissions. Complete the companion-device and battery-optimization prompts presented by setup. Manufacturer background restrictions can affect delivery even after these grants.

## Pair, then enable one PAM service

Follow [pairing](pair-and-revoke.md) and confirm an active bond before changing a PAM service.

The installer defaults to `auth sufficient`, whereas SPEC §3.2 D7 specifies `auth required`. These policies behave differently. Read [the PAM policy reference](../reference/configuration.md#pam-policy) and have your administrator select the intended stack before running the installer.

If you have selected the installer's `sufficient` policy for `sudo`, install only its PAM line; the user daemon is already configured:

```sh
sudo syauth install-pam --service sudo --with-presenced=false \
  --control sufficient
```

Inspect `/etc/pam.d/sudo` and its `.bak` backup. Do not add U2F fallback unless `pam_u2f` is installed and enrolled. Do not copy a service chain from another distribution.

## Verify and undo

Run `syauth doctor`, then complete [your first unlock](../tutorials/first-unlock.md). Test the existing authentication method with the phone unavailable before closing the administrator session.

To undo this service's installation, restore its backup:

```sh
sudo syauth uninstall-pam --service sudo
```

The uninstall command restores the saved file, so preserve any edits made after installation before using it. Other enabled PAM services remain separate.

<!-- Structure: Diátaxis goal-oriented how-to; commands checked against CLI help and installer source. -->
