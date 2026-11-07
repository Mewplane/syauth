# Protocol reference

This reference describes the active persistent-daemon unlock path at source revision `648375e`. General frame helpers and older design diagrams do not by themselves describe every runtime message.

## BLE roles

Linux runs the GATT peripheral and advertises. Android runs the GATT central/client. A per-bond unlock service uses `session_uuid_for(bond_key, 0)` for stable GATT discovery; the advertised rendezvous UUID rotates separately. The notification characteristic carries challenges; the write characteristic carries phone responses.

| Characteristic | UUID |
| --- | --- |
| Unlock challenge | `5a4e8e3c-1c4c-4a17-9c81-d518a55a0002` |
| Unlock response | `5a4e8e3c-1c4c-4a17-9c81-d518a55a0003` |
| Pair service | `5a4e8e3c-1c4c-4a17-9c81-d518a55a0101` |
| Pair host public key | `5a4e8e3c-1c4c-4a17-9c81-d518a55a0102` |
| Pair phone public key | `5a4e8e3c-1c4c-4a17-9c81-d518a55a0103` |

## Pairing derivations

Both sides exchange 32-byte public keys. The phone reads the host key before writing its own key, because the latter write permits the desktop to replace the pair service.

```text
bond_key = HKDF-SHA256(
    salt = absent,
    input = host_public_key || phone_public_key,
    info = "syauth-bond-v1",
    length = 32
)
```

The application code is derived from this material for comparison on both devices. This derivation uses public inputs; it is not a confidential key agreement. LESC and public-key pinning have distinct roles, explained in [security](../explanation/security.md).

## Advertised session UUID

```text
minute = floor(unix_seconds / 60)
session_uuid = HKDF-SHA256(
    salt = absent,
    input = bond_key,
    info = "syauth-session-v1" || signed_64_bit_big_endian(minute),
    length = 16
)
```

The daemon replaces the advertised UUID set at minute boundaries. It includes each active peer's UUID and a pairing rendezvous UUID derived with an all-zero bond key. Phone scan helpers accept the current and previous minute. The advertised rotating value is not the stable per-bond GATT service UUID.

## Desktop challenge

| Field | Bytes | Contents |
| --- | --- | --- |
| Version | 1 | `0x01` |
| Nonce | 16 | Fresh daemon-generated random bytes |
| Payload | 0–4,096 | Empty for the active unlock challenge |
| Tag | 16 | First 16 bytes of keyed BLAKE3 over the body |

```text
body = version || nonce || payload
tag = BLAKE3_keyed_hash(bond_key, body)[0:16]
wire = body || tag
```

An empty-payload challenge is 33 bytes. The core frame decoder validates version and size. In the active Android callbacks, however, the final 16 bytes are removed and the remaining body is passed to the approval activity; those callbacks do not call the core MAC verifier. Do not infer runtime verification from the existence of that helper.

## Phone response

On approval, Android Keystore produces a **raw 64-byte Ed25519 signature over `body`**. The persistent-daemon response is not another version/nonce/payload/tag frame. Cancel sends 64 zero bytes, which fails signature verification and becomes `bad-signature`.

The daemon verifies using the phone public key pinned in the bond record and the original challenge body. It then rejects a nonce already in its per-peer cache and caches an accepted nonce. A prior signature does not verify against a different fresh challenge body.

## Local PAM RPC

The Unix socket carries typed CBOR with a four-byte unsigned big-endian payload length prefix and a 65,536-byte payload cap. Request kinds are `challenge`, `reload`, and `status`. A challenge request includes `peer_id` and `nonce`; its response includes `ok`, optional `signature`, and `reason`.

Two details matter when integrating:

- The current dispatcher ignores the request's nonce and asks the orchestrator to generate a new one for BLE.
- The active PAM handler maps the response's `reason` to a PAM code. It does not independently verify the signature, nor does it validate `ok` or signature presence before mapping `reason="ok"` to success. The daemon and local socket are part of the trusted authentication boundary.

## Results returned to PAM

| Daemon reason | Module result |
| --- | --- |
| `ok` | `PAM_SUCCESS` |
| `denied`, `bad-signature`, `replay` | `PAM_AUTH_ERR` |
| `offline`, `busy`, `response-timeout`, `unknown-peer`, `transport-error`, `adapter-missing` | `PAM_AUTHINFO_UNAVAIL` |
| Unrecognized reason | `PAM_AUTH_ERR` |

`denied` exists in the RPC taxonomy; the current phone Cancel wire value follows the `bad-signature` path. Socket or decoding failure also maps to unavailable. The surrounding PAM stack controls fallback and final access.

Source: [UUIDs and session derivation](https://github.com/Mewplane/syauth/blob/648375e/crates/syauth-transport/src/bluez.rs), [frame layout](https://github.com/Mewplane/syauth/blob/648375e/crates/syauth-core/src/frame.rs), [challenge state machine](https://github.com/Mewplane/syauth/blob/648375e/crates/syauth-presenced/src/orchestrator.rs), [RPC types](https://github.com/Mewplane/syauth/blob/648375e/crates/syauth-presenced/src/rpc.rs), [PAM mapping](https://github.com/Mewplane/syauth/blob/648375e/crates/syauth-pam/src/auth.rs).

<!-- Structure: Diátaxis reference; original prose for syauth. -->
