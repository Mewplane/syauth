# BUG-20261108-nix-pam-socket: PAM rules do not infer the desktop socket

## Summary

Enabling a NixOS PAM service without module arguments cannot reach the daemon
selected by `desktopUser` when root-run sudo has no desktop runtime environment.

## Reproduction

- Isolated NixOS KVM guest, PR #7 head `41c262e`, desktop account UID 1100.
- Start the real installed daemon with a valid synthetic signature queued.
- Enable sudo with empty `pam.moduleArgs`: PAM reports `reason=transport-error`.
- Restore `socket=/run/user/1100/syauth/auth.sock`: authentication succeeds.
- Evaluation regression: default rule arguments were `[]`, not the expected
  desktop user's socket argument (`nix/check.nix`).

## Expected Behavior

Selecting a desktop user with a declared UID and enabling PAM generates a
working socket argument. Without a declared UID, configuration requires an
explicit absolute socket. Explicit overrides remain available.

## Actual Behavior

The default argument list is empty. PAM's environment/EUID-based resolver does
not infer the module's selected desktop account and silently falls back to the
service's other authentication rules.

## Root Cause Analysis

The NixOS adapter knows `desktopUser` but does not communicate its runtime
socket to PAM. A root caller's effective UID points at `/run/user/0`, independent
of the account running the desktop daemon.

## Fix

Generate the socket from the configured UID and assert an absolute socket
argument when any PAM service is selected. Keep opt-in services and the existing
control policy. Add a booted installation regression to flake checks and CI.

## Stressors

Non-default UID; auto-allocated UID; missing desktop environment; root caller;
explicit socket override; empty override; no PAM services; required control;
daemon starts after PAM; invalid signature; second account; disable/rollback.

## Traceability

- Evaluation: `nix/check.nix`.
- Integrated runtime: `nix/tests/installation.nix`, `installation.py`, `fixture.py`.
- Implementation: `nix/modules/nixos.nix`.
- CI: `.github/workflows/ci.yml`.
