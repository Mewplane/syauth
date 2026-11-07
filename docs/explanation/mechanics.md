---
hide:
  - toc
---

# How syauth works

syauth turns a phone's biometric-gated signing key into an authentication method for Linux PAM. Bluetooth transports the request; your approval authorizes the signature. Merely bringing the phone nearby does not unlock the computer.

Three mechanisms work together: pairing pins an identity, discovery prepares a channel, and each unlock asks for a fresh signature. The animations below show their message order. They start paused, support keyboard-operated controls, and retain a full text explanation without animation.

## The actors

| Actor | Responsibility |
| --- | --- |
| Application and PAM stack | Ask for authentication and apply the service's access policy |
| `pam_syauth.so` | Select an active peer, call the daemon over a local Unix socket, and map the returned reason to a PAM code |
| `syauth-presenced` | Own the Linux BLE peripheral, advertise, send challenges, verify phone signatures, and keep recent accepted nonces |
| Android companion | Maintain the GATT client, show the bonded host's name, obtain approval, and return a signature |
| Android Keystore and BiometricPrompt | Gate use of the phone's signing key on a fresh strong biometric |

The long-running daemon keeps radio state outside the synchronous PAM call. PAM does not create a new BLE connection for each request or perform the signature verification itself.

## Pairing: establish the phone identity

<div class="sy-mechanics" data-flow="pairing"></div>

1. **Rendezvous.** You open a desktop pairing window and select the computer in Android's companion-device picker. Linux exposes the pair GATT service; Android connects as an LE client.
2. **Bluetooth confirmation.** LE Secure Connections displays a six-digit numeric-comparison code. You compare and confirm it on both devices.
3. **Exchange public keys.** The phone creates an Ed25519 key in Android Keystore. It reads the desktop's 32-byte public key first, then writes its own 32-byte public key. The order matters: the phone-key write permits the desktop to finish pairing and replace the transient service.
4. **Derive application material.** Both sides run HKDF-SHA256 over `host_public_key || phone_public_key` with the label `syauth-bond-v1`, producing the same 32-byte `bond_key`.
5. **Application confirmation.** Both display a derived four-word code. You compare and confirm this separately from the Bluetooth code.
6. **Remember the bond.** Desktop and phone persist their application records, and Android records the companion association. The desktop pins the phone's public key for later signature verification.

The private signing key remains behind its Android Keystore alias. The public-key derivation in step 4 does not create a secret unknown to anyone who knows those public keys. The application confirmation is useful for checking the exchanged identities, but is not a substitute for a confidential key exchange. See [the security boundaries](security.md#implementation-and-design).

Implementation anchors: [bond derivation](https://github.com/Mewplane/syauth/blob/648375e/crates/syauth-core/src/bond.rs), [phone exchange wiring](https://github.com/Mewplane/syauth/blob/648375e/syauth-android/app/src/main/kotlin/com/sy/syauth/android/pair/impl/RealPairBackendWiring.kt), [Keystore key generation](https://github.com/Mewplane/syauth/blob/648375e/syauth-android/app/src/main/kotlin/com/sy/syauth/android/pair/impl/KeystoreKeyGenerator.kt).

## Discovery: prepare the channel

<div class="sy-mechanics" data-flow="discovery"></div>

1. **Load active peers.** The desktop daemon reads bond records and their application key files. Revoked records do not become active unlock peers.
2. **Advertise a rendezvous.** For each peer, the daemon derives a 16-byte session UUID using HKDF-SHA256 with the bond material and the current minute counter. It rotates the advertised UUID set at minute boundaries and also includes the pairing rendezvous derived from a zero key.
3. **Observe and connect.** Android's companion association supports background wakeups. Its scan helper computes current and previous minute UUIDs; the persistent client reconnects to the remembered desktop using explicit LE transport and `autoConnect=true`.
4. **Discover services.** The phone discovers the desktop's GATT services. A connection callback alone does not make the application channel ready.
5. **Subscribe.** Android writes the challenge characteristic's CCCD to enable notifications. After subscription, the desktop can deliver a challenge without establishing a new link for each PAM request.

The rendezvous UUID and GATT service UUID serve different purposes. Advertisements rotate; the per-bond unlock service is stable, derived at minute zero, so the phone can find its characteristics after connection.

The UUID is a matching mechanism, not proof of distance or authorization. Someone with the derivation inputs can compute it, and other Bluetooth identifiers can remain observable. Your next authentication still requires explicit approval.

When the radio disconnects, Android retries setup through service discovery and subscription. The desktop discards a closed notifier while keeping its GATT application registered for re-subscription. OS scheduling, Doze, adapter behavior, and manufacturer restrictions affect recovery; a successful radio toggle is not evidence for all range-loss cases.

Implementation anchors: [session UUID derivation](https://github.com/Mewplane/syauth/blob/648375e/crates/syauth-transport/src/bluez.rs), [phone scan slots](https://github.com/Mewplane/syauth/blob/648375e/syauth-android/app/src/main/kotlin/com/sy/syauth/android/bg/BleScanController.kt), [persistent phone connection](https://github.com/Mewplane/syauth/blob/648375e/syauth-android/app/src/main/kotlin/com/sy/syauth/android/bg/PersistentGattClient.kt), [notification lifecycle](https://github.com/Mewplane/syauth/blob/648375e/crates/syauth-transport/src/peripheral/notification.rs).

## Unlock: a fresh signature for each request

<div class="sy-mechanics" data-flow="unlock"></div>

1. **PAM asks.** A service such as sudo calls PAM. `pam_syauth.so` reads the default bond store, selects the first non-revoked peer, and sends a typed challenge request over the daemon's Unix socket.
2. **The daemon challenges.** It acquires that peer's single challenge slot and generates a random 16-byte nonce. It builds `version || nonce || payload`, with an empty payload in this path, appends a 16-byte keyed-BLAKE3 tag, and notifies the phone.
3. **The phone asks you.** The current Android callbacks strip the tag and pass the body to the approval activity. The displayed computer name comes from the saved bond. You tap **Approve**; the active path then requests `BIOMETRIC_STRONG` authentication.
4. **Keystore signs.** BiometricPrompt authorizes one operation using the stored Ed25519 key. The phone signs the challenge body, excluding its trailing tag, and writes a raw 64-byte signature to the response characteristic.
5. **The daemon verifies.** It checks the signature against the pinned phone public key and the original challenge body. After verification, it checks and updates the peer's cache of the last 64 accepted nonces.
6. **PAM returns.** The daemon sends the result over the local socket. PAM maps its reason to a return code. The full PAM stack applies the configured policy and decides whether another method can run.

A captured signature covers one particular challenge body. Changing its nonce changes the signed message, so the captured response does not verify against a fresh challenge. The recent-nonce cache provides an additional check within the running daemon; it is not persistent across restarts.

The active phone callbacks do not call the core MAC verifier before showing the prompt. The active PAM handler trusts the daemon's reason rather than verifying the response itself. These boundaries are material to the [security model](security.md), even though the common happy-path animation ends with verification success.

Implementation anchors: [PAM authentication](https://github.com/Mewplane/syauth/blob/648375e/crates/syauth-pam/src/auth.rs), [daemon state machine](https://github.com/Mewplane/syauth/blob/648375e/crates/syauth-presenced/src/orchestrator.rs), [phone callback](https://github.com/Mewplane/syauth/blob/648375e/syauth-android/app/src/main/kotlin/com/sy/syauth/android/bg/SyauthCompanionService.kt), [approval and signing](https://github.com/Mewplane/syauth/blob/648375e/syauth-android/app/src/main/kotlin/com/sy/syauth/android/bg/ChallengeApprovalActivity.kt).

## When the happy path stops

| Event | What happens |
| --- | --- |
| Daemon or socket unavailable | PAM returns authentication-information-unavailable; the service policy controls recovery |
| Phone not subscribed | The daemon cannot deliver a challenge and returns a transport failure |
| Another request owns the peer slot | The daemon waits up to one second for that slot, then returns `busy` if still occupied |
| You tap Cancel | Phone sends 64 zero bytes; daemon returns `bad-signature` |
| Response misses the deadline | The challenge times out; the configured response budget is eight seconds |
| Old or forged signature | Verification fails, or an already accepted cached nonce becomes `replay` |

There is no authenticated cancellation message to dismiss a phone prompt when a desktop request ends. An old prompt can remain visible. Its response does not become a valid signature for a different fresh nonce. Request a new authentication and dismiss the stale screen.

For exact fields and return codes, use [the protocol reference](../reference/protocol.md). For operator steps, use [troubleshooting](../how-to/troubleshoot.md).

<!-- Structure: Diátaxis explanation; original prose and animation transcripts for syauth. -->
