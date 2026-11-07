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
| `pam.moduleArgs` | `[ ]` | Arguments passed to each rule, such as `socket=`. |

The module inserts its rule before the service's enabled Unix password rule.
For a stack such as `plasmalogin`, it inserts the rule before the first
enabled authentication rule. If you override a service's PAM text directly,
that text must include the syauth authentication rule.

With the default `sufficient` control, successful phone approval can end
authentication. On failure PAM continues with the service's other rules.
See [PAM policy](configuration.md#pam-policy) before changing the control.
