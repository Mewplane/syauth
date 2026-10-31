# Fedora RPM spec for syauth v0.1.0 (roadmap item S-021).
#
# This spec ships the Linux desktop side of syauth — the PAM cdylib
# under %%{_libdir}/security/pam_syauth.so (mode 0644 per SPEC §6 +
# specs/threat/THREAT-2026-05-15.md), the `syauth` CLI under
# %%{_bindir}/syauth (mode 0755), the manpage under
# %%{_mandir}/man8/syauth.8.gz, and the doc set. The %post scriptlet
# creates /var/lib/syauth/ with mode 0700 (the bond-store dir; bond
# records inside it land at 0600 via the `syauth pair` CLI from S-005).
# %preun deliberately does nothing because the bond store is persisted
# user state — uninstalling the package does NOT revoke any paired
# phone. Built under `mock -r fedora-%%{fedora}-x86_64 deploy/fedora/syauth.spec`
# or via `make rpm` (which gates on `which mock`).

%global package_version 0.1.0
%global rpm_release 5
%global debug_package %{nil}
%global min_fedora 39

Name:           syauth
Version:        %{package_version}
Release:        %{rpm_release}%{?dist}
Summary:        Phone-as-key PAM authenticator for Linux

License:        MIT
URL:            https://github.com/sy/syauth
Source0:        %{name}-%{version}.tar.gz

# Cross-reference: deploy/version.env, /Cargo.toml [workspace.package].
# A bump here without a matching bump there is a release-engineering
# bug; see specs/journeys/JOURNEY-S-021-v0_1_release.md.

ExclusiveArch:  x86_64 aarch64

# Build-time toolchain. cargo + rust are bumped to 1.85 to match the
# workspace's `rust-version`. pam-devel is required for the PAM header
# bindings; bluez-libs-devel for the BlueZ DBus interface that bluer
# wraps; openssl-devel
# for the rustls/ring transitive crypto. systemd-rpm-macros provides
# %%{_unitdir} (unused in v0.1, declared for forward compatibility).
BuildRequires:  cargo >= 1.85
BuildRequires:  rust >= 1.85
BuildRequires:  pam-devel
BuildRequires:  pkgconf-pkg-config
BuildRequires:  bluez-libs-devel
BuildRequires:  systemd-rpm-macros
BuildRequires:  openssl-devel
BuildRequires:  gzip

# Runtime closure. pam 1.5+ for the modern conv pointer ABI; bluez
# 5.66+ for LE Secure Connections numeric comparison; dbus for the
# BlueZ system bus; libsecret for the keyring fallback (kernel
# keyutils is in glibc and needs no Requires:).
Requires:       pam >= 1.5
Requires:       bluez >= 5.66
Requires:       dbus
Requires:       libsecret
Requires:       systemd

# Mark Fedora 39 as the floor. Older Fedora may build but is not on
# the supported matrix (see specs/syauth/SPEC.md §3.3).
Requires:       fedora-release >= %{min_fedora}

%description
syauth replaces typing a password for PAM-gated actions (sudo, login,
lockscreen) with an approve-tap on a paired Android phone. The phone's
signing key is unlocked by a fresh biometric per unlock, defeating the
NCC link-layer relay class of attacks that broke every prior passive
BLE PAM module. On phone-absent or phone-deny, the module returns
PAM_AUTHINFO_UNAVAIL and the configured fallback (typically pam_unix)
runs, so a dead phone never locks the user out. See README.md for the
quick start and docs/security.md for the threat model.

%prep
%autosetup -n %{name}-%{version}

%build
if [ -n "${CARGO_TARGET_DIR:-}" ]; then
    mkdir -p "$CARGO_TARGET_DIR"
    ln -s "$CARGO_TARGET_DIR" target
fi
# Build the PAM module, CLI, and desktop presence daemon together.
cargo build --release --locked \
    --package syauth-pam \
    --package syauth-cli \
    --package syauth-presenced

# Manpage. The source crate exposes its `--help` output; the manpage
# below points at `--help` and the
# README — the help text itself is the source of truth, so a richer
# manpage would duplicate effort. Closure plan documented in
# docs/release-process.md.
mkdir -p target/man
cat > target/man/syauth.8 <<'MAN'
.TH SYAUTH 8 "2026-05-15" "syauth %{version}" "System Administration"
.SH NAME
syauth \- phone-as-key PAM authenticator for Linux
.SH SYNOPSIS
.B syauth
[\fIsubcommand\fR] [\fIoptions\fR]
.SH DESCRIPTION
.B syauth
ships a PAM module (\fIpam_syauth.so\fR) and a control CLI that
brokers unlocks between a Linux desktop and a paired Android phone.
See \fBsyauth --help\fR for the full subcommand list and the project
README at \fI/usr/share/doc/syauth/README.md\fR for the quick start.
.SH SEE ALSO
\fBpam(8)\fR, \fBpam.conf(5)\fR, \fBpam_unix(8)\fR.
.SH AUTHORS
syauth contributors.
MAN
gzip -9f target/man/syauth.8

%check
target/release/syauth --help | grep -q pair
target/release/syauth-presenced --help | grep -q -- '--socket'

%install
install -D -m 0755 target/release/syauth-presenced \
    %{buildroot}%{_libexecdir}/syauth-presenced
install -D -m 0644 crates/syauth-presenced/dist/syauth-presenced.service \
    %{buildroot}%{_userunitdir}/syauth-presenced.service
sed -i 's|/usr/local/libexec/syauth-presenced|%{_libexecdir}/syauth-presenced|g' \
    %{buildroot}%{_userunitdir}/syauth-presenced.service
# PAM cdylib — mode 0644 (world-readable, root-writable). The mode is
# pinned by specs/threat/THREAT-2026-05-15.md Finding F-002 and by
# SPEC §6.
install -D -m 0644 target/release/libpam_syauth.so \
    %{buildroot}%{_libdir}/security/pam_syauth.so

# CLI — mode 0755.
install -D -m 0755 target/release/syauth \
    %{buildroot}%{_bindir}/syauth

# Manpage.
install -D -m 0644 target/man/syauth.8.gz \
    %{buildroot}%{_mandir}/man8/syauth.8.gz

# Bond state is not owned by RPM metadata: upgrades must preserve
# the existing per-user daemon's directory ownership.

%post
# Idempotent bond-store directory creation. The mode 0700 is pinned by
# specs/threat/THREAT-2026-05-15.md Finding F-001 (root-only access).
# Existing directories retain their configured owner and permissions.
if [ ! -e /var/lib/syauth ]; then
    install -d -m 0700 -o root -g root /var/lib/syauth
fi

%preun
# Deliberately empty. The bond store is persisted user state; an
# uninstall must NOT delete /var/lib/syauth/bonds.toml. To remove
# bonds, run `syauth revoke <peer>` BEFORE uninstalling.
:

%files
%license LICENSE
%doc README.md docs/security.md docs/android-setup.md
%{_libdir}/security/pam_syauth.so
%{_bindir}/syauth
%{_libexecdir}/syauth-presenced
%{_userunitdir}/syauth-presenced.service
%{_mandir}/man8/syauth.8.gz

%changelog
* Sat Oct 31 2026 syauth contributors <maintainers@example.invalid> - 0.1.0-5
- Select the available BlueZ default adapter when starting the presence daemon.

* Tue Oct 20 2026 syauth contributors <maintainers@example.invalid> - 0.1.0-4
- Publish native Linux packages, a signed Android APK, and release checksums.
- Add package-manager installation and published documentation.

* Sun Oct 18 2026 syauth contributors <maintainers@example.invalid> - 0.1.0-3
- Use standard BlueZ notifications across phone reconnection.
- Correct the user unit's documentation URL.

* Sun Oct 18 2026 syauth contributors <maintainers@example.invalid> - 0.1.0-2
- Ship the presence daemon and user unit with pairing and recovery repairs.
- Preserve existing bond-directory ownership during upgrades.

* Fri May 15 2026 syauth contributors <noreply@anthropic.com> - 0.1.0-1
- Initial release. PAM module (pam_syauth.so), CLI (syauth) with
  pair/list/revoke/status subcommands, Android companion shipped
  separately as a signed APK from the same GitHub release. See
  specs/syauth/SPEC.md and specs/threat/THREAT-2026-05-15.md for
  the protocol and threat model.
