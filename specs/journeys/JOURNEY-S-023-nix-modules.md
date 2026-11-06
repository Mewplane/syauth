# JOURNEY-S-023: Configure syauth for a NixOS desktop account

## Roadmap Link

[Step S-023](../syauth/ROADMAP.md#step-s-023-nixos-module)

## 1. Journey

A NixOS user enables syauth for their desktop account and lists the PAM
services where they want phone authentication. They pair from that account
and use the phone or the service's existing authentication path.

## 2. CJM

| Phase | User action | Expected result |
| --- | --- | --- |
| Configure | Import the NixOS module and name the desktop account and PAM services. | The configuration owns the CLI, private store and user unit. |
| Pair | Run `syauth pair` from the desktop account. | The daemon can read the resulting bond. |
| Authenticate | Use an enabled service and approve on the phone. | The selected PAM policy handles approval and fallback. |

## 3. UX Implementation and Assessment

One account owns the store and runs the user unit. PAM changes are opt-in by
service. The administrator can override the control and specify the daemon
socket for callers outside the user session.

## 4. Tests

The flake check evaluates a NixOS configuration and checks the user unit,
directory ownership, inert PAM defaults, and rules for the sudo-rs and Plasma
services. It checks that an explicit PAM control reaches the generated rule.
The Rust workspace still exercises the daemon binary against a fake radio.

## Implementation

- `nix/modules/nixos.nix` declares the installation, user service and PAM rules.
- `nix/check.nix` is the NixOS evaluation check.
- The [installation guide](../../docs/how-to/install.md#configure-nixos) documents the flake input, module import, and settings.

## Traceability

[Step S-023](../syauth/ROADMAP.md#step-s-023-nixos-module)
