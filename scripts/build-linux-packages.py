#!/usr/bin/env python3
"""Package prebuilt Linux binaries without changing authentication configuration."""

import argparse
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ARCHES = {
    "x86_64": ("amd64", "x86_64-linux-gnu"),
    "aarch64": ("arm64", "aarch64-linux-gnu"),
}
PACKAGERS = ("deb", "rpm", "archlinux")


def package_config(version, arch, kind, binaries):
    """Return nFPM metadata for one distribution's native package layout."""
    goarch, multiarch = ARCHES[arch]
    pam_dir = {"deb": f"/usr/lib/{multiarch}/security", "rpm": "/usr/lib64/security",
               "archlinux": "/usr/lib/security"}[kind]
    contents = []
    for source, dest, mode in (
        (binaries / "syauth", "/usr/bin/syauth", 0o755),
        (binaries / "syauth-presenced", "/usr/libexec/syauth-presenced", 0o755),
        (binaries / "libpam_syauth.so", f"{pam_dir}/pam_syauth.so", 0o644),
        (ROOT / "crates/syauth-presenced/dist/syauth-presenced.service",
         "/usr/lib/systemd/user/syauth-presenced.service", 0o644),
        (ROOT / "LICENSE", "/usr/share/doc/syauth/copyright" if kind == "deb"
         else "/usr/share/licenses/syauth/LICENSE", 0o644),
        (ROOT / "README.md", "/usr/share/doc/syauth/README.md", 0o644),
    ):
        contents.append({"src": str(source), "dst": dest,
                         "file_info": {"mode": mode}})
    dependencies = {
        "deb": ["libc6 (>= 2.36)", "libgcc-s1", "libdbus-1-3", "libpam0g", "bluez", "dbus", "systemd"],
        "rpm": ["glibc >= 2.36", "libgcc_s.so.1()(64bit)", "libdbus-1.so.3()(64bit)", "pam", "bluez", "/usr/bin/dbus-daemon", "systemd"],
        "archlinux": ["glibc>=2.36", "gcc-libs", "dbus", "pam", "bluez", "systemd"],
    }
    return {
        "name": "syauth", "arch": goarch, "platform": "linux", "version": version,
        "release": "4" if kind == "rpm" else "1", "section": "admin", "priority": "optional",
        "maintainer": "syauth contributors <noreply@github.com>",
        "description": "Phone-as-key PAM authenticator with a per-user presence daemon.",
        "homepage": "https://github.com/Mewplane/syauth", "license": "MIT",
        "depends": dependencies[kind], "contents": contents,
        "scripts": {"postinstall": str(ROOT / "deploy/packages/postinstall.sh")},
    }


def artifact_name(version, arch, kind):
    """Use stable release names shared with the shell installer."""
    if kind == "deb":
        return f"syauth_{version}_{ARCHES[arch][0]}.deb"
    if kind == "rpm":
        return f"syauth-{version}-4.{arch}.rpm"
    return f"syauth-{version}-1-{arch}.pkg.tar.zst"


def build(version, arch, binaries, output, nfpm):
    """Build all native formats and a relocatable inspection/source-install archive."""
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("release version must be MAJOR.MINOR.PATCH")
    for name in ("syauth", "syauth-presenced", "libpam_syauth.so"):
        if not (binaries / name).is_file():
            raise ValueError(f"missing release binary: {binaries / name}")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="syauth-package-") as temporary:
        work = Path(temporary)
        service = work / "syauth-presenced.service"
        original = ROOT / "crates/syauth-presenced/dist/syauth-presenced.service"
        service.write_text(original.read_text().replace(
            "/usr/local/libexec/syauth-presenced", "/usr/libexec/syauth-presenced"))
        for kind in PACKAGERS:
            config = package_config(version, arch, kind, binaries)
            for item in config["contents"]:
                if item["dst"].endswith("syauth-presenced.service"):
                    item["src"] = str(service)
            path = work / f"{kind}.json"
            path.write_text(json.dumps(config))
            subprocess.run([nfpm, "package", "--config", str(path), "--packager", kind,
                            "--target", str(output / artifact_name(version, arch, kind))], check=True)
        # A tar archive is an explicit manual option; the shell installer never uses it.
        config = package_config(version, arch, "archlinux", binaries)
        archive = output / f"syauth-{version}-linux-{arch}.tar.gz"
        epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "0"))
        with archive.open("wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=epoch) as zipped:
            with tarfile.open(fileobj=zipped, mode="w") as tar:
                for item in config["contents"]:
                    source = service if item["dst"].endswith(".service") else Path(item["src"])
                    info = tar.gettarinfo(str(source), arcname=item["dst"].lstrip("/"))
                    info.uid = info.gid = 0
                    info.uname = info.gname = "root"
                    info.mtime = epoch
                    info.mode = item["file_info"]["mode"]
                    with source.open("rb") as stream:
                        tar.addfile(info, stream)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--arch", choices=ARCHES, default="x86_64")
    parser.add_argument("--binaries", type=Path, default=ROOT / "target/release")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--nfpm", default=shutil.which("nfpm") or "nfpm")
    args = parser.parse_args()
    try:
        build(args.version, args.arch, args.binaries.resolve(), args.output.resolve(), args.nfpm)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Packaging failed: {error}\n")


if __name__ == "__main__":
    main()
