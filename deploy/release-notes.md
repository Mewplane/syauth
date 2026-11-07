# syauth 0.2.0

This release restores phone discovery after Bluetooth controller resets and
reports transport health separately from daemon liveness.

- Automatically rebuild GATT and rotating advertising after controller loss,
  including controllers renamed from hci0 to hci1. Keep the existing pairing.
- Retry while the controller is unavailable without exhausting the service
  restart limit. Bluetooth setup failures request recovery instead of leaving
  a socket-only daemon.
- Add `daemon.transport_ready` to `syauth status --json`. Phone absence and an
  unanswered approval do not indicate a failed local Bluetooth transport.
- Include patched ctutils and Tokio dependencies.

The companion panel update is in https://github.com/dmytrogajewski/sy/pull/9.
Each authentication still requires explicit phone approval and a strong biometric.

Approve Linux authentication on Android with a fresh strong biometric.

- Native desktop DEB, RPM, and Arch packages and Linux archives for x86_64 and ARM64.
- Signed Android companion with four native ABIs and a published signing certificate.
- Illustrated documentation: https://mewplane.github.io/syauth/
- Installer: `curl -fsSL https://mewplane.github.io/syauth/install.sh | sh`

Packages install the CLI, PAM module, presence daemon, and user service. They do not enable PAM or start the service automatically. Follow the installation guide to prepare storage, pair the phone, select a PAM policy, and test your recovery method.

Linux requires glibc 2.36+; supported package paths include Debian 12+, Ubuntu 24.04+, and current Fedora/openSUSE/Arch systems. Android signing requires Android 13+ and a supported Ed25519 Keystore implementation, despite the APK's lower installation minimum.

Verify downloads against `SHA256SUMS`. `release.json` records the source commit and artifact digests. The Android release certificate SHA-256 fingerprint is `25:58:5E:64:1E:DB:3D:A8:7B:98:90:56:B3:D1:65:CA:C2:AF:AF:2A:AE:DD:35:87:56:66:B5:21:EC:C0:22:1C`.

Read the documented security boundaries before enabling PAM: https://mewplane.github.io/syauth/explanation/security/
