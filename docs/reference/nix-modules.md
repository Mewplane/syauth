# NixOS module options

Import `nixosModules.default` to configure syauth for one desktop account.
See the [NixOS setup example](../how-to/install.md#configure-nixos).

The user service restarts after transport failure without a start-rate limit,
matching the upstream service's recovery policy when a controller disappears.

| Option under `services.syauth` | Default | Purpose |
| --- | --- | --- |
| `enable` | `false` | Install syauth and declare the user service. |
| `desktopUser` | Required when enabled | Owns `/var/lib/syauth`, runs the daemon, and pairs phones. |
| `package` | Flake's syauth package | Supplies the CLI, daemon and PAM module. |
| `installCli` | `true` | Put syauth on the system PATH. |
| `pam.services` | `[ ]` | PAM services to change. |
| `pam.control` | `"sufficient"` | Control field applied to each injected PAM rule. |
| `pam.moduleArgs` | Socket for the declared desktop UID | Arguments passed to each rule; requires an absolute `socket=` path when PAM is enabled. |

When `users.users.<desktopUser>.uid` is explicitly declared, the default argument
is `socket=/run/user/<uid>/syauth/auth.sock`. This works for root-run PAM callers
without relying on their environment. If NixOS allocates the UID at activation,
set `pam.moduleArgs` explicitly using the account's actual runtime socket path.
An empty argument list with PAM enabled is rejected during configuration checks.
Explicit arguments replace the generated default, so retain `socket=` when
adding other arguments.

The module inserts its rule before the service's enabled Unix password rule.
For a stack such as `plasmalogin`, it inserts the rule before the first
enabled authentication rule. If you override a service's PAM text directly,
that text must include the syauth authentication rule.

With the default `sufficient` control, successful phone approval can end
authentication. On failure PAM continues with the service's other rules.
See [PAM policy](configuration.md#pam-policy) before changing the control.

## Automated validation

`nix flake check` builds the package, checks generated rules and invalid
configurations, and boots a NixOS integration VM. The VM exercises installed
PAM and the daemon with deterministic public signing fixtures, including
PAM-before-daemon audit ownership, valid and invalid signatures, password
fallback, two-account isolation, sudo and sudo-rs, profile removal, and
disable/rollback preserving bonds. It uses no physical Bluetooth adapter or
Android phone and does not establish radio or biometric behavior.

Run on a Linux machine with writable `/dev/kvm`. GitHub CI enables KVM through
the Nix installation action and runs the same flake checks with sandboxing.
