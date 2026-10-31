# Configuration and storage

This page describes the active daemon and PAM configuration. It does not replace the design specification or change the service's authentication policy.

The presence daemon selects BlueZ's available default Bluetooth adapter at
startup. It does not assume the controller is named `hci0`; reinitialized
controllers can appear as `hci1` or later. After controller removal, restarting
the daemon selects the currently available adapter. An RPC status of `up` alone
does not establish that the desktop is advertising or the phone is subscribed.

## Files and ownership

| Path | Owner / use |
| --- | --- |
| `/var/lib/syauth/bonds.toml` | Desktop application bond records: peer public keys, names, and status |
| `/var/lib/syauth/keys/<peer_id>.bin` | Per-peer 32-byte application bond material; current desktop path reads files |
| `/var/lib/syauth/last.log` | Authentication transaction log |
| `$XDG_RUNTIME_DIR/syauth/auth.sock` | Daemon RPC socket, mode `0600` |
| `$XDG_RUNTIME_DIR/syauth/presenced.pid` | Daemon single-instance lock |
| `$XDG_CONFIG_HOME/systemd/user/syauth-presenced.service` | Installed user unit; falls back to `~/.config/systemd/user` |
| `/etc/pam.d/<service>` and `<service>.bak` | Service policy and the installer's saved original |
| Android app-private `syauth-bond.toml` | Host metadata, application bond material, and a Keystore alias |

The intended default desktop store belongs to the desktop account running the daemon. Keep directories private (`0700`) and key files private (`0600`). The shared default path is not a separate store for each Linux account. Changing the daemon's storage flags alone does not change the PAM module's fixed bond directory.

Android's signing private key is represented by its Keystore alias. It is not a raw Ed25519 seed stored in that TOML file. See [storage boundaries](../explanation/security.md#implementation-and-design) for the difference between a Keystore signing key and the application's bond material.

## PAM socket resolution

The active parser accepts `socket=<path>`. It resolves the socket in this order:

1. An explicit `socket=` module argument.
2. `$XDG_RUNTIME_DIR/syauth/auth.sock` when that environment variable is nonempty.
3. `/run/user/<effective-uid>/syauth/auth.sock`.

PAM can run under a different account or environment from the desktop session. Inspect the actual daemon path before selecting an override. The module reads `/var/lib/syauth/bonds.toml` and chooses the first non-revoked peer in record order; it does not race all bonded phones.

The parser does not load `/etc/syauth.conf`. It ignores unknown module arguments, including `timeout=`.

## Deadlines and limits

| Setting | Active value | Effect |
| --- | --- | --- |
| Daemon challenge response deadline | 8,000 ms | Wait for the phone's response |
| PAM response read budget | 8,000 ms | Bound the blocking RPC read |
| Per-peer challenge slot | One | Serialize challenges to one phone |
| Per-peer queue wait | 1,000 ms | Return `busy` if the slot remains occupied |
| Daemon concurrent connection cap | Four | Limit simultaneous RPC handlers |
| Daemon replay cache | Last 64 accepted nonces per peer | Reject a cached nonce after signature verification |
| RPC CBOR payload cap | 65,536 bytes | Reject oversized local messages |

These limits come from source constants, not a user-editable config file. The replay cache is in memory for the daemon's lifetime. Its implementation is a bounded recent-nonce cache, not a persistent time-to-live database. The eight-second budgets are waiting limits, not a guarantee of total application authentication latency.

## PAM policy

The installer's current default line is:

```text
auth sufficient pam_syauth.so timeout=8000
```

With `sufficient`, a success can end authentication if no earlier required module has failed; its failure is normally ignored while the stack continues. With `required`, failure remains a failure even if later modules succeed. A later password module does not automatically erase that failure. Extended control expressions can define other policies. These semantics come from the [Linux-PAM control-field reference](https://github.com/linux-pam/linux-pam/blob/master/doc/man/pam.conf-syntax.xml).

SPEC §3.2 D7 specifies `auth required`, while the installer emits `sufficient`. This is an existing implementation/design mismatch. The examples document the installer, not an approval to weaken D7. An administrator must select the intended policy for the complete service stack, including earlier modules, included stacks, and recovery behavior.

The syauth module returns success, authentication error, or authentication-information-unavailable. Returning an error does not alone determine whether the whole stack permits access; see [the result mapping](protocol.md#results-returned-to-pam).

## Service installation

`install-presenced` writes a user unit before attempting binary installation. The live path copies the selected source to `/usr/local/libexec/syauth-presenced` and runs `systemctl --user daemon-reload` and `enable --now`. That copy needs permission to write the destination.

`--dry-run --from /usr/local/libexec/syauth-presenced` writes a unit pointing at the preinstalled binary and prints the systemctl commands without running them. It is not a filesystem-free preview. `--unit-dir` changes where the unit is written.

The shipped unit restarts on failure and restricts filesystem writes to its configured paths. If you override data paths, review the unit's `ReadWritePaths` too. Its user-session lifetime also matters for authentication before login: a stopped user service cannot answer requests.

Source: [PAM configuration](https://github.com/dmytrogajewski/syauth/blob/648375e/crates/syauth-pam/src/config.rs), [orchestrator limits](https://github.com/dmytrogajewski/syauth/blob/648375e/crates/syauth-presenced/src/orchestrator.rs), [user unit](https://github.com/dmytrogajewski/syauth/blob/648375e/crates/syauth-presenced/dist/syauth-presenced.service).

<!-- Structure: Diátaxis reference; original prose for syauth. -->
