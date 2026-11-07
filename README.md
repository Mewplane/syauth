# syauth

<img src="assets/syauth.png" width="160" alt="syauth pixel cat paw holding a gold key">

Approve Linux authentication on your Android phone with a fresh strong biometric. syauth connects a Linux PAM module, a desktop Bluetooth daemon, and an Android companion that signs each request through Android Keystore.

[Documentation](https://mewplane.github.io/syauth/) · [Downloads](https://github.com/Mewplane/syauth/releases/latest) · [How it works](https://mewplane.github.io/syauth/explanation/mechanics/) · [Security boundaries](https://mewplane.github.io/syauth/explanation/security/)

## Install

For Nix or NixOS, use the [Nix setup below](#nix-and-nixos).

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

### Nix and NixOS

The flake supports `x86_64-linux` and `aarch64-linux`. With Nix and flakes enabled, install into your user profile without cloning the repository:

```sh
nix profile install github:Mewplane/syauth
syauth --version
```

This installs the CLI, `syauth-presenced` daemon, and PAM module; storage, service activation, and PAM still need configuration. See [profile installation and setup](docs/how-to/install.md#install-with-nix) for details and update/removal commands.

For NixOS, add `github:Mewplane/syauth` as a flake input and import `syauth.nixosModules.default`. Enable `services.syauth`, set `desktopUser` to your existing desktop account, and select the PAM services through `pam.services` (empty by default). The module manages the package, private bond-store directory, and daemon in that account's systemd user session. Run pairing as that account, without `sudo`.

Follow the [installation guide](docs/how-to/install.md#configure-nixos) for the complete flake configuration and activation commands. The [NixOS module reference](docs/reference/nix-modules.md) documents all options and PAM policy.

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
- [Nix and NixOS setup](docs/how-to/install.md#install-with-nix), [NixOS module options](docs/reference/nix-modules.md)
- [CLI](https://mewplane.github.io/syauth/reference/cli/), [configuration](https://mewplane.github.io/syauth/reference/configuration/), [protocol](https://mewplane.github.io/syauth/reference/protocol/)
- [Illustrated mechanics](https://mewplane.github.io/syauth/explanation/mechanics/) with animated pairing, discovery, and unlock
- [Release builds and signing](https://mewplane.github.io/syauth/contributing/releases/)

## Development and contributing

For a pinned Rust development environment, run `nix develop .`. Entering the shell also installs the repository's pre-commit hooks. Build from a checkout with `nix build .` and try the CLI with `nix run . -- --version`. Run `nix flake check .` to build the package, check the generated NixOS configuration, and boot the installed-PAM integration VM (requires writable `/dev/kvm`); see [building with Nix](docs/how-to/install.md#with-nix) for details.

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
