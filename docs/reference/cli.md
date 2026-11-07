# Command reference

The desktop provides `syauth` for administration and `syauth-presenced` for the persistent BLE channel. Use `syauth <command> --help` for the full option list supplied by your installed version.

## Everyday commands

| Command | Purpose | Useful options |
| --- | --- | --- |
| `syauth pair` | Start numeric-comparison and application-code pairing | `--adapter hci0`, `--waybar`, `--force`, `--peer <name-substring>`, `--bond-dir <path>` |
| `syauth list` | Print bond records as TSV, including revoked records | `--bond-dir <path>` |
| `syauth revoke --id <peer_id>` | Mark a record revoked, retaining its history | `--reason <text>`, `--bond-dir <path>` |
| `syauth status` | Inspect desktop state and query the daemon | `--json`, `--watch`, `--socket <path>`, `--bond-dir <path>`, `--adapter hci0` |
| `syauth doctor` | Probe daemon, storage, permissions, BlueZ, and unit state | `--json`, `--socket <path>`, `--bonds-file <path>`, `--keys-dir <path>`, `--audit-log <path>` |

`pair --force` replaces the application's existing peer record; it does not reset the Bluetooth system bond. `pair --yes` skips interactive confirmation and is intended for controlled test rigs. `--waybar` and `--yes` are mutually exclusive.

`status --json` reports the daemon section in machine-readable form. A peer's `last_connect_ms_ago` is currently stamped by challenge activity, not a GATT connection event. `daemon.transport_ready` reports controller and advertisement health, sampled every two seconds. A missing or null value means the daemon cannot report transport health. This field does not report phone presence. Use notification subscription logs and an approved challenge to verify the phone connection.

`doctor --skip-bluez`, `--skip-systemctl`, and `--skip-daemon` explicitly omit those probes for restricted environments. A skipped probe does not establish that its component works.

## Installation commands

| Command | Purpose | Defaults and behavior |
| --- | --- | --- |
| `syauth install-presenced` | Write the systemd user unit, copy the binary, enable and start the service | Source binary defaults to a sibling of `syauth`; use `--from <path>` to choose it |
| `syauth install-presenced --dry-run` | Write the unit and print the systemctl commands | Still writes a file; skips copying the binary and running systemctl |
| `syauth install-pam --service <name>` | Insert the module in one PAM service and save a `.bak` | `/etc/pam.d`, `pam_syauth.so`, `--control sufficient`, `--module-args timeout=8000`, `--with-presenced=true` |
| `syauth uninstall-pam --service <name>` | Restore that service from its backup | Removes the backup after restoration |

`install-pam --with-presenced=false` edits only PAM. `--pam-dir <path>` selects an alternative service directory. `--so-path <name-or-path>` selects the module library. `--control <value>` selects the PAM control field. `--with-u2f-fallback` adds a `pam_u2f.so` line if one is absent; it does not install or enroll a U2F authenticator.

`--module-args` writes text into the PAM line. The active PAM parser recognizes `socket=<path>` only; changing the written `timeout=` text does not change its deadline. See [configuration](configuration.md#deadlines-and-limits).

There is no `install-presenced --live` option. Its live path is the default and attempts a copy into `/usr/local/libexec`. For a separate privileged binary installation and user-owned unit, follow [the install guide](../how-to/install.md#prepare-storage-and-the-user-service).

## Daemon options

```text
syauth-presenced [--socket PATH] [--bonds-file PATH]
                 [--keys-dir PATH] [--audit-log PATH]
                 [--log-level FILTER]
```

| Option | Default |
| --- | --- |
| `--socket` | `$XDG_RUNTIME_DIR/syauth/auth.sock`, otherwise `/run/user/<uid>/syauth/auth.sock` |
| `--bonds-file` | `/var/lib/syauth/bonds.toml` |
| `--keys-dir` | `/var/lib/syauth/keys` |
| `--audit-log` | `/var/lib/syauth/last.log` |
| `--log-level` | `info` |

Examples of read-only diagnostics:

```sh
syauth status --json
syauth doctor --json
systemctl --user status syauth-presenced --no-pager
```

Source: [CLI dispatch](https://github.com/dmytrogajewski/syauth/blob/648375e/crates/syauth-cli/src/main.rs), [PAM installer](https://github.com/dmytrogajewski/syauth/blob/648375e/crates/syauth-cli/src/install_pam.rs), [daemon options](https://github.com/dmytrogajewski/syauth/blob/648375e/crates/syauth-presenced/src/main.rs).

<!-- Structure: Diátaxis reference; original prose for syauth. -->
