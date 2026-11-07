# Troubleshoot an approval

Start with the failing boundary: PAM request, daemon, BLE subscription, phone approval, or signature verification. Keep an existing administrator session open while investigating authentication problems.

## Collect the desktop state

```sh
syauth doctor
syauth list
syauth status --json
systemctl --user status syauth-presenced --no-pager
journalctl --user -u syauth-presenced -n 80 --no-pager
```

Run these in the desktop user's session. A root or SSH session can resolve a different runtime directory and socket. Logs may contain peer identifiers and challenge nonces; review them before sharing. Never share bond-key files.

## No phone request appears after sudo

Expire the sudo authorization cache with `sudo -k`, then try `sudo -v`. Check that the service file actually includes `pam_syauth.so`, that the module is in the distribution's module directory, and that the daemon socket exists at the configured path.

If the caller cannot resolve the desktop user's runtime directory, use an explicit `socket=/run/user/<desktop-uid>/syauth/auth.sock` PAM argument after checking the actual UID and path. Do not change directory permissions to make an incorrect socket path accessible.

## The phone is bonded but does not receive requests

An active bond and `STATE_CONNECTED` are not sufficient. Notification setup must complete:

```sh
adb logcat -s syauth.bg.persistent
```

Look for `descriptor write status=0` for CCCD UUID `00002902-0000-1000-8000-00805f9b34fb` on Android and `phone subscribed` on the desktop. The daemon's `last_connect_ms_ago` is based on challenge activity and does not prove that CCCD is ready.

Check Android notification permission, companion association, battery-optimization exclusion, Bluetooth state, and manufacturer background restrictions. Allow the stored client to reconnect after a radio cycle. A temporary disconnect should not require new pairing.

The current desktop keeps its GATT application registered when a notification session closes; `notification session closed; awaiting re-subscribe` is the expected recovery message. A build that repeatedly logs `rebuilding GATT application` is using the older recovery path. Update both sides before comparing behavior.

## Pairing fails while reading the host key

If Android reports `host-pubkey read failed status=1`, check that it is running the current companion. The exchange reads the host key **before** sending the phone key; sending the phone key allows the desktop to replace the transient pair service. Reusing those handles afterward can fail. Both pairing and persistent connections explicitly request LE transport; enabling a Bluetooth audio profile is not required.

If codes differ, cancel. If a picker shows stale entries, inspect the phone's companion-device associations before removing any, then retry with the desktop pairing window open.

## The biometric prompt fails

The active approval path requires `BIOMETRIC_STRONG`, with no device-PIN fallback. Confirm Android API 33 or later, a supported Ed25519 Keystore, and an enrolled strong biometric. Re-enrollment or changes to secure device settings can invalidate a key; re-pair if the stored alias no longer works.

StrongBox support for Ed25519 varies. The app retries using Android Keystore without StrongBox when that request is unsupported. This does not make every Android device compatible.

## Approval expires or fails verification

The current response budget is eight seconds. Approve a request you initiated while it is active. A desktop timeout does not send authenticated cancellation to dismiss the phone's screen; a lingering prompt can be stale. Initiate a new request and dismiss the old screen rather than repeatedly approving it.

`bad-signature` or `replay` cannot grant access through syauth. A phone-side Cancel currently sends 64 zero bytes, which the daemon classifies as `bad-signature`. The caller's PAM policy determines whether another module can authenticate afterward; consult [the result table](../reference/protocol.md#results-returned-to-pam).

## Undo a PAM installation

From the administrator session you retained:

```sh
sudo syauth uninstall-pam --service sudo
```

Use the actual service name. This restores its `.bak` snapshot, including the snapshot's older contents. Restore any intentional later edits separately.

## Report a reproducible problem

Include the CLI and APK versions, distribution, BlueZ version, phone model and Android version, the action that triggered the problem, and sanitized logs from both sides. Distinguish a radio-off/on test from physical range loss or Doze: success in one does not establish recovery in the others.

The [repository Bluetooth guide](https://github.com/Mewplane/syauth/blob/master/docs/bluetooth.md) includes the emulator harness and its qualifications. Arch Linux KDE users can also consult the optional [package update checker](https://github.com/Mewplane/syauth/blob/master/docs/arch-update-check.md).

<!-- Structure: Diátaxis troubleshooting how-to; original prose for syauth. -->

## Controller reset leaves authentication unavailable

Check `syauth status --json` and the service journal. `daemon.state: up` means
that RPC works. `daemon.transport_ready: true` means the last transport check
found a powered controller and an active advertisement. Neither confirms that
the phone is nearby.

The daemon checks transport every two seconds. Controller removal, missing
advertising, and advertisement update failures cause a failure exit. The managed
service retries every two seconds, rebuilding GATT and advertising on the
available default controller. Existing bonds stay on disk. An absent controller
does not exhaust the service restart limit.

An unanswered phone approval does not trigger transport recovery. Bring the phone
back and retry authentication. Each successful request still needs phone approval.
