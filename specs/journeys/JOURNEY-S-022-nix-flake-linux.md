# JOURNEY-S-022: Build, run and develop with Nix

## Roadmap Link

[Step S-022](../syauth/ROADMAP.md#step-s-022-nix-flake)

## 1. Journey

A Linux user builds syauth or runs the CLI from a checkout. A contributor can
enter the same pinned Rust environment to work on the code.

## 2. CJM

| Phase | User action | Expected result |
| --- | --- | --- |
| Build | `nix build .` | The result includes the CLI, daemon and PAM module. |
| Run | `nix run . -- --version` | The CLI reports its version. |
| Develop | `nix develop .` | Cargo and the lint tools are available. |

## 3. UX Implementation and Assessment

The package and shell are available on x86-64 and ARM64 Linux. The default
flake outputs give the common commands a short entry point.

## 4. Tests

`nix flake check` covers the package and NixOS module. The package build
runs the Rust workspace suite.

## Implementation

`flake.nix`, `flake.lock` (which pins the fenix stable toolchain),
`nix/package.nix` and [the Nix build instructions](../../docs/how-to/install.md#with-nix).

## Traceability

[Step S-022](../syauth/ROADMAP.md#step-s-022-nix-flake)
