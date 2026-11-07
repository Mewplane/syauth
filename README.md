# syauth

<img src="assets/syauth.png" width="160" alt="syauth pixel cat paw holding a gold key">

Approve Linux authentication on your Android phone with a fresh strong biometric. syauth connects a Linux PAM module, a desktop Bluetooth daemon, and an Android companion that signs each request through Android Keystore.

[Documentation](https://mewplane.github.io/syauth/) · [Downloads](https://github.com/Mewplane/syauth/releases/latest) · [How it works](https://mewplane.github.io/syauth/explanation/mechanics/) · [Security boundaries](https://mewplane.github.io/syauth/explanation/security/)

## Install

On a supported Linux desktop:

```sh
curl -fsSL https://mewplane.github.io/syauth/install.sh | sh
```

The installer resolves the latest release, chooses the native package for your distribution and CPU, checks its SHA-256 checksum, and installs it with `apt`, `dnf`, `zypper`, or `pacman`. It requests `sudo` when needed. It leaves PAM configuration and service activation to you.

Prefer to review the script first?

```sh
curl -fsSLo install-syauth.sh https://mewplane.github.io/syauth/install.sh
less install-syauth.sh
sh install-syauth.sh --dry-run
sh install-syauth.sh
```

Release downloads include DEB, RPM, Arch Linux packages, and manual Linux archives for x86_64 and ARM64, plus a signed [Android APK](https://github.com/Mewplane/syauth/releases/download/v0.2.0/syauth-0.2.0-android.apk), source archive, signing certificate, build metadata, and `SHA256SUMS`. See [installation and verification](https://mewplane.github.io/syauth/how-to/install/) for direct package commands and version-pinned downloads.

Use Debian 12+, Ubuntu 24.04+, a current Fedora/openSUSE/Arch installation, or a compatible derivative, with glibc 2.36+, PAM, systemd user services, BlueZ, and a BLE adapter capable of advertising. The phone needs Android 13+ with a supported Ed25519 Keystore implementation and an enrolled strong biometric. The APK can install on older Android versions, but that does not establish signing-key support.

## Use

1. Install the desktop package and signed Android companion.
2. Follow [storage and user-service setup](https://mewplane.github.io/syauth/how-to/install/#prepare-storage-and-the-user-service).
3. Run `syauth pair`, complete numeric comparison on both devices, and confirm the bond with `syauth list`.
4. Read the [PAM policy reference](https://mewplane.github.io/syauth/reference/configuration/#pam-policy), configure one service, and complete [your first unlock](https://mewplane.github.io/syauth/tutorials/first-unlock/).

```sh
syauth pair
syauth list
syauth doctor
```

Being nearby prepares the connection; each authentication still needs explicit approval and a strong biometric. Keep the existing recovery method available while configuring PAM. The [security guide](https://mewplane.github.io/syauth/explanation/security/) describes the current implementation's differences from the design specification, including bond derivation and desktop key storage.

## Documentation

- [First unlock tutorial](https://mewplane.github.io/syauth/tutorials/first-unlock/)
- [Install](https://mewplane.github.io/syauth/how-to/install/), [pair and revoke](https://mewplane.github.io/syauth/how-to/pair-and-revoke/), [troubleshoot](https://mewplane.github.io/syauth/how-to/troubleshoot/)
- [CLI](https://mewplane.github.io/syauth/reference/cli/), [configuration](https://mewplane.github.io/syauth/reference/configuration/), [protocol](https://mewplane.github.io/syauth/reference/protocol/)
- [Illustrated mechanics](https://mewplane.github.io/syauth/explanation/mechanics/) with animated pairing, discovery, and unlock
- [Release builds and signing](https://mewplane.github.io/syauth/contributing/releases/)

## Development and contributing

The Rust workspace is under `crates/`; the Android app is under `syauth-android/`. Build from source with a toolchain compatible with the committed `Cargo.lock` and development packages for D-Bus, PAM, and Bluetooth:

```sh
make build
make test
make lint
python3 -m unittest discover -s tests -p 'test_release_*.py'
python3 -m unittest discover -s tests -p test_installer.py
```

See [documentation development](docs/contributing/documentation.md), [release development](docs/contributing/releases.md), and [AGENTS.md](AGENTS.md) for contributor contracts. Open an [issue](https://github.com/Mewplane/syauth/issues) with reproduction steps and sanitized diagnostics, or a pull request with the user-visible change and relevant test evidence. Avoid posting bond files, private keys, or unreviewed logs.

## Maintainers

Maintained by [dmytrogajewski](https://github.com/dmytrogajewski) and contributors.

## License

[MIT](LICENSE).
