---
hide:
  - toc
---

<div class="sy-hero" markdown>
<img class="sy-hero__mascot" src="assets/syauth.png" alt="syauth pixel cat paw holding a gold key">
<div markdown>
<p class="sy-eyebrow">PHONE · BIOMETRIC · LINUX</p>

# A paw of approval.

Approve Linux authentication on your Android phone. syauth carries a fresh challenge over Bluetooth, asks for your approval and a strong biometric, and verifies the phone's signature on your desktop.

[Set up syauth](how-to/install.md){ .md-button .md-button--primary }
[See the mechanics](explanation/mechanics.md){ .md-button }
[Download a release](https://github.com/dmytrogajewski/syauth/releases/latest){ .md-button }

</div>
</div>

## Install the release

Install the desktop with `curl -fsSL https://dmytrogajewski.github.io/syauth/install.sh | sh`, then follow [installation and setup](how-to/install.md). The [published v0.2.0 assets](https://github.com/dmytrogajewski/syauth/releases/tag/v0.2.0) include DEB/RPM/Arch packages for both CPU architectures, the [signed Android companion](https://github.com/dmytrogajewski/syauth/releases/download/v0.2.0/syauth-0.2.0-android.apk), and [checksums](https://github.com/dmytrogajewski/syauth/releases/download/v0.2.0/SHA256SUMS).

## Follow one unlock

<div class="sy-mechanics" data-flow="unlock"></div>

1. A Linux application calls PAM. The syauth module asks the desktop daemon to challenge your bonded phone.
2. The daemon sends a fresh nonce over the existing BLE connection.
3. You tap **Approve** on the phone and complete a strong biometric prompt.
4. Android Keystore signs the challenge. The daemon verifies the signature and checks its replay cache.
5. PAM receives the result. The service's PAM stack decides whether to grant access or continue to another authentication method.

The animation is a teaching model, not a connection to your phone. Use **Play**, **Next step**, or **Restart**; playback starts paused. The steps above remain readable without JavaScript.

## Find your path

<div class="grid cards" markdown>

- **Try your first approval**

    Follow the [first unlock tutorial](tutorials/first-unlock.md) on a configured desktop.

- **Set up and operate**

    [Install](how-to/install.md), [pair or revoke a phone](how-to/pair-and-revoke.md), and [troubleshoot a failed approval](how-to/troubleshoot.md).

- **Understand the system**

    Explore [pairing, discovery, and unlock](explanation/mechanics.md), then read the [security boundaries](explanation/security.md).

- **Look up the details**

    Find [commands](reference/cli.md), [paths and configuration](reference/configuration.md), [wire formats](reference/protocol.md), and the [glossary](reference/glossary.md).

</div>

## What to expect

The desktop advertises; the phone connects. Being nearby prepares the channel: every unlock still needs your explicit approval and a strong biometric. Unlock does not require an Internet service.

Use Android 13 or later with a supported Ed25519 Android Keystore implementation and an enrolled strong biometric. The APK's lower installation minimum does not mean pairing works on older Android versions.

These pages describe the implementation, including its limitations. In particular, the current bond derivation is not the hybrid key exchange described in the design specification, and the desktop stores application bond material in files. Read [the implementation boundaries](explanation/security.md#implementation-and-design) before enabling PAM.

[Source code](https://github.com/dmytrogajewski/syauth) · [Report a problem](https://github.com/dmytrogajewski/syauth/issues) · [Build these docs](contributing/documentation.md)
