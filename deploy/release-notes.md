# syauth 0.3.0

This release adds Nix packaging and declarative NixOS integration, with installed-PAM VM coverage and a fix for audit ownership when PAM starts before the user daemon.

- Install the CLI, presence daemon, and PAM module through the pinned Nix flake.
- Configure one desktop account, its private bond store, user service, and opt-in PAM services through `nixosModules.default`.
- Generate the PAM socket argument from a declared desktop UID; require an explicit absolute socket when the UID is allocated at activation.
- Create new PAM audit logs with mode `0600` and the bond-store account's ownership, allowing the user daemon to append detailed transaction records.
- Run Nix package/module checks and a booted NixOS VM in CI, covering approvals, signature rejection, password fallback, account isolation, profile removal, and disable/rollback preserving bonds.

Thanks to [@xBLACKICEx](https://github.com/xBLACKICEx) for contributing Nix and NixOS support in [#7](https://github.com/Mewplane/syauth/pull/7). The audit fix is [#9](https://github.com/Mewplane/syauth/pull/9).

Nix setup: https://mewplane.github.io/syauth/how-to/install/#install-with-nix

Existing audit logs retain their contents and ownership. If an older version created a root-owned log, have an administrator restore the desktop account's ownership and mode `0600` as documented in https://mewplane.github.io/syauth/reference/configuration/#files-and-ownership.

Each authentication still requires explicit phone approval and a strong biometric. The existing PAM control policy and documented security boundaries are unchanged.

Release downloads include native DEB, RPM, and Arch packages and Linux archives for x86_64 and ARM64, a signed Android companion with four native ABIs, the source archive, installer, public signing certificate, build metadata, and `SHA256SUMS`.

Linux requires glibc 2.36+; supported package paths include Debian 12+, Ubuntu 24.04+, and current Fedora/openSUSE/Arch systems. Android signing requires Android 13+ and a supported Ed25519 Keystore implementation, despite the APK's lower installation minimum.

Verify downloads against `SHA256SUMS`. `release.json` records the source revision and artifact digests. The persistent Android certificate SHA-256 fingerprint is `25:58:5E:64:1E:DB:3D:A8:7B:98:90:56:B3:D1:65:CA:C2:AF:AF:2A:AE:DD:35:87:56:66:B5:21:EC:C0:22:1C`.

Documentation and security boundaries: https://mewplane.github.io/syauth/
Installer: `curl -fsSL https://mewplane.github.io/syauth/install.sh | sh`

Packages leave PAM activation to the administrator. NixOS PAM services are also opt-in; select the complete service policy and verify recovery before relying on phone authentication.
