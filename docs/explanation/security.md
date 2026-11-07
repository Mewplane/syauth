# Security boundaries

syauth requires active phone approval and a fresh strong biometric for signing. That limits what a nearby device or a stolen unlocked phone can do without your cooperation. It does not prove physical distance, make the desktop daemon untrusted, or eliminate risks in the surrounding PAM policy.

This page describes source revision `648375e`. The original design specification and some repository guides describe stronger properties than the active path implements. Treat the following distinctions as implementation facts, not changes to the approved specification.

## What verifies an unlock

The daemon checks an Ed25519 signature over its original challenge body using the bonded phone's public key. A new random nonce changes that body for every request. The per-peer cache rejects an accepted nonce while it remains among the last 64 entries in that running daemon.

The phone requests a Keystore signing key with per-use strong biometric authentication and asks BiometricPrompt to authorize the signing operation. The active prompt has no PIN or device-credential fallback. StrongBox is requested; unsupported StrongBox configurations fall back to Android Keystore without that requirement. The actual device's key backing must not be inferred from the request alone.

## Implementation and design

| Boundary | Active implementation | Consequence |
| --- | --- | --- |
| Bond exchange, SPEC D4 | HKDF-SHA256 over the exchanged host and phone **public keys** | Public inputs do not establish a confidential shared secret; do not claim the specified X25519 + ML-KEM exchange |
| Message protection, SPEC D4 | Challenge body plus a truncated keyed-BLAKE3 tag; no application ChaCha20-Poly1305 on this path | Do not claim application AEAD; link protection and identity pinning remain distinct concerns |
| Incoming challenge | MainActivity and companion-service callbacks remove the trailing tag and launch approval without calling the core MAC verifier | The core verification helper does not establish that incoming prompts are authenticated in the active path |
| Desktop storage, SPEC D6 | Application bond material is read from `/var/lib/syauth/keys/<peer_id>.bin` | File permissions matter; this daemon path does not use the specified kernel-keyring/libsecret storage |
| Android storage | Private Ed25519 key behind a Keystore alias; application bond material in app-private storage | Keystore protection of the signing key does not automatically protect every stored field in the same way |
| PAM policy, SPEC D7 | Installer defaults to `sufficient`; specification says `required` | Full-stack authentication and fallback differ; an administrator must review the selected policy |
| Local RPC | PAM maps the daemon's reason to its return code without independently verifying the signature or checking `ok` | The daemon, socket, and local account are trusted components for authentication |
| Socket peer check | Socket mode `0600` inside the user's runtime directory; unexpected peer credentials are warned about but accepted | Filesystem access control is the active barrier; do not claim strict UID rejection |
| Expiry and cancellation | Desktop deadline without authenticated phone cancellation | A stale prompt may remain after the caller has stopped waiting |

These are existing mismatches and limitations; the documentation work does not approve a SPEC deviation or change any production behavior. The historical [known-gaps ledger](https://github.com/Mewplane/syauth/blob/master/docs/known-gaps.md) and [design specification](https://github.com/Mewplane/syauth/blob/master/specs/syauth/SPEC.md) provide design context, not proof that every property is present in the runtime path.

## Relay and unwanted approval

A BLE connection and an RSSI reading are not distance proofs. An attacker can attempt to relay traffic or provoke an approval while you are elsewhere. A relay cannot create your phone's signature by itself, but an unexpected request that you approve can still authorize authentication. Approve only a request you initiated, after checking the saved computer name. The active empty-payload challenge does not cryptographically describe a sudo command or application action.

Pairing's Bluetooth numeric comparison and separate application-code comparison require your attention. Do not accept mismatched codes or use noninteractive confirmation as a normal setup shortcut. The application code is derived from the exchanged public keys; it does not repair every possible failure of the Bluetooth link or local endpoints.

## Local compromise and availability

A process that controls the trusted daemon account, its socket, or its bond files is within the authentication boundary. A compromised root account can also change PAM and its libraries. Hardware-backed signing on the phone does not remove those desktop trust assumptions.

Radio loss, a depleted phone battery, missing permissions, background restrictions, and daemon failure can prevent phone authentication. Whether the user can then authenticate another way depends on the service's complete PAM stack. A phone-side denial returns an error through syauth; with a `sufficient` control flag, other methods can still run. See [PAM policy](../reference/configuration.md#pam-policy).

## Storage and diagnostics

Keep desktop key files private and do not copy them into logs or issue reports. The current daemon audit records include peer identifiers and nonce values; review logs before sharing them. A rotating advertised UUID does not hide all Bluetooth metadata, and anyone with its derivation inputs can calculate it.

If you lose a phone, [revoke its application bond](../how-to/pair-and-revoke.md#revoke-a-phone) and remove the OS association when possible. Revoked records are retained for history and excluded from active daemon peers.

Source: [public-input bond derivation](https://github.com/Mewplane/syauth/blob/648375e/crates/syauth-core/src/bond.rs), [challenge verification](https://github.com/Mewplane/syauth/blob/648375e/crates/syauth-presenced/src/orchestrator.rs), [socket admission](https://github.com/Mewplane/syauth/blob/648375e/crates/syauth-presenced/src/server.rs), [PAM handler](https://github.com/Mewplane/syauth/blob/648375e/crates/syauth-pam/src/auth.rs), [Android challenge callback](https://github.com/Mewplane/syauth/blob/648375e/syauth-android/app/src/main/kotlin/com/sy/syauth/android/bg/SyauthCompanionService.kt).

<!-- Structure: Diátaxis explanation; original prose for syauth. -->
