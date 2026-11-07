# BUG-20261108-audit-ownership: PAM-first audit files block the user daemon

## Summary

Root-run PAM can create the shared audit file before the desktop user's daemon,
leaving the daemon unable to append transaction records.

## Reproduction

- Method: isolated NixOS KVM guest, PR #7 head `41c262e`.
- Run sudo while Bluetooth is unavailable, then start the installed daemon with
  a synthetic signed phone response.
- Evidence: `last.log` becomes `644 root users`; the daemon logs
  `audit log open failed; orchestrator will run without audit appends` with
  `Permission denied (os error 13)`. Authentication succeeds without its detailed
  audit record. Correcting ownership in the guest restores logging.
- Automated regressions: `auth::tests::last_log_append_writes_one_line` and
  `crates/syauth-pam/tests/pam_audit_ownership.rs`.

## Expected Behavior

A new PAM audit file is private and owned by the bond-store account, allowing
the desktop daemon to append regardless of startup order. Existing records
survive subsequent PAM calls.

## Actual Behavior

The file inherits the root caller's ownership and the default creation mode.
The later unprivileged daemon cannot open it for append.

## Root Cause Analysis

PAM and the user daemon both append to `last.log`. PAM uses plain `O_CREAT`
without specifying its mode or assigning the bond-store account ownership.
The daemon's mode-on-create cannot change an already existing root-owned file.

## Fix

Create the PAM log exclusively with mode 0600, then assign the newly created
file descriptor the parent directory's UID and GID before writing. Open an
existing file for append without changing its ownership or truncating it.
Reject a final-component symbolic link, including during concurrent creation.
Authentication outcomes and PAM control policy remain unchanged.

## Stressors

PAM starts first; daemon starts first; simultaneous file creation; restrictive
umask; existing records; non-root PAM caller; a different desktop UID; a
symbolic-link destination; missing directory; unwritable directory; ownership
assignment failure; repeated authentication.

## Traceability

- Failing test: `last_log_append_writes_one_line` checks mode 0600.
- Privileged regression: `pam_first_log_is_owned_by_store_account` checks a
  disposable account's UID/GID and subsequent appends.
- Fixed in: `crates/syauth-pam/src/auth.rs`.
- No authentication-policy or protocol changes.
