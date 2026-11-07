#!/bin/sh
# Download a version-pinned native package and verify its release checksum.
set -eu

fail() { printf 'syauth installer: %s\n' "$*" >&2; exit 1; }
usage() { printf '%s\n' 'Usage: install.sh [--version X.Y.Z] [--dry-run]' 'Supports Debian/Ubuntu, Fedora, openSUSE, and Arch Linux on x86_64/aarch64.'; }
version=
version_supplied=false
dry_run=false
while [ "$#" -gt 0 ]; do
    case "$1" in
        --version) [ "$#" -ge 2 ] || fail '--version needs X.Y.Z'; version=${2#v}; version_supplied=true; shift 2;;
        --dry-run) dry_run=true; shift;;
        --help|-h) usage; exit 0;;
        *) fail "Unknown argument: $1";;
    esac
done
if [ "$version_supplied" = true ]; then
    printf '%s\n' "$version" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' || fail 'Version must be X.Y.Z'
fi
for tool in curl sha256sum mktemp uname getconf awk sed grep; do
    command -v "$tool" >/dev/null 2>&1 || fail "Required command missing: $tool"
done
arch=$(uname -m)
case "$arch" in
    x86_64) deb_arch=amd64;;
    aarch64|arm64) arch=aarch64; deb_arch=arm64;;
    *) fail "Unsupported architecture: $arch";;
esac
libc=$(getconf GNU_LIBC_VERSION 2>/dev/null) || fail 'A glibc-based Linux distribution is required'
printf '%s\n' "$libc" | awk '$1 == "glibc" {split($2,v,"."); if(v[1]>2 || (v[1]==2 && v[2]>=36)) ok=1} END {exit !ok}' || fail 'glibc 2.36 or newer is required'
os_release=${SYAUTH_OS_RELEASE:-/etc/os-release}
[ -r "$os_release" ] || fail 'Cannot read /etc/os-release'
distro=$(sed -n 's/^ID=//p' "$os_release" | tr -d '"' | tr -d "'")
case "$distro" in
    debian|ubuntu|linuxmint|pop|elementary|zorin) manager=apt-get; format=deb;;
    fedora) manager=dnf; format=rpm;;
    opensuse-tumbleweed|opensuse-leap|opensuse) manager=zypper; format=rpm;;
    arch|endeavouros|manjaro) manager=pacman; format=arch;;
    *) fail "Unsupported distribution: $distro. See https://mewplane.github.io/syauth/how-to/install/";;
esac
command -v "$manager" >/dev/null 2>&1 || fail "Native package manager missing: $manager"
work=$(mktemp -d "${TMPDIR:-/tmp}/syauth-install.XXXXXXXX")
trap 'rm -rf "$work"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
fetch() { curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' --connect-timeout 15 --max-time 180 --retry 3 --output "$2" "$1"; }
repo=https://github.com/Mewplane/syauth
api=https://api.github.com/repos/Mewplane/syauth/releases
if [ -n "$version" ]; then
    endpoint=$api/tags/v$version
else
    endpoint=$api/latest
fi
fetch "$endpoint" "$work/release.json"
tag=$(sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\(v[0-9][0-9.]*\)".*/\1/p' "$work/release.json")
printf '%s\n' "$tag" | grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$' || fail 'Release API returned an invalid or missing tag'
[ -z "$version" ] || [ "$tag" = "v$version" ] || fail 'Release tag does not match requested version'
version=${tag#v}
case "$format" in
    deb) asset=syauth_${version}_${deb_arch}.deb;;
    rpm) asset=syauth-${version}-4.${arch}.rpm;;
    arch) asset=syauth-${version}-1-${arch}.pkg.tar.zst;;
esac
base=$repo/releases/download/$tag
printf 'Downloading syauth %s for %s/%s\n' "$version" "$distro" "$arch"
fetch "$base/SHA256SUMS" "$work/SHA256SUMS"
fetch "$base/$asset" "$work/$asset"
# Select exactly one complete manifest entry; reject duplicates and malformed hashes.
awk -v name="$asset" '$2==name {if(length($1)!=64 || $1 ~ /[^0-9a-f]/) exit 1; print $1 "  " name; count++} END {if(count!=1) exit 1}' "$work/SHA256SUMS" > "$work/selected.sha256" || fail 'Missing, duplicated, or malformed package checksum'
(cd "$work" && sha256sum --check selected.sha256) || fail 'Checksum verification failed; refusing installation'
if [ "$dry_run" = true ]; then
    printf 'Verified %s; would install with %s. No changes made.\n' "$asset" "$manager"
    exit 0
fi
# Package installation may elevate; network downloads never run through sudo.
run_root() {
    if [ "$(id -u)" = 0 ]; then "$@"; else
        command -v sudo >/dev/null 2>&1 || fail 'sudo is required; alternatively run the downloaded script as root'
        sudo "$@"
    fi
}
case "$manager" in
    apt-get) run_root apt-get update -q; run_root apt-get install -y "$work/$asset";;
    dnf) run_root dnf install -y "$work/$asset";;
    zypper) run_root zypper --non-interactive install --allow-unsigned-rpm "$work/$asset";;
    pacman) run_root pacman -U --noconfirm "$work/$asset";;
esac
printf '%s\n' 'Installed. PAM configuration is unchanged. Follow https://mewplane.github.io/syauth/tutorials/first-unlock/ to pair your phone and enable the user service.'
