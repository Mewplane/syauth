#!/usr/bin/env python3
"""Validate a complete release and write source metadata and SHA-256 checksums."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def required_artifacts(version):
    """Return the complete public artifact contract for a release."""
    names = {"install.sh", "android-signing-certificate.pem", "android-signing-certificate.txt",
             f"syauth-{version}-android.apk", f"syauth-{version}-source.tar.gz"}
    for arch, deb_arch in (("x86_64", "amd64"), ("aarch64", "arm64")):
        names.update((f"syauth_{version}_{deb_arch}.deb", f"syauth-{version}-4.{arch}.rpm",
                      f"syauth-{version}-1-{arch}.pkg.tar.zst", f"syauth-{version}-linux-{arch}.tar.gz"))
    return names


def prepare(directory, version, revision):
    """Reject incomplete inputs before producing a publication manifest."""
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("version must be MAJOR.MINOR.PATCH")
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("source revision must be a full Git commit SHA")
    missing = required_artifacts(version) - {p.name for p in directory.iterdir() if p.is_file()}
    if missing:
        raise ValueError("missing release artifacts: " + ", ".join(sorted(missing)))
    artifacts = []
    for path in sorted(directory.iterdir()):
        if path.name in ("release.json", "SHA256SUMS"):
            continue
        if path.is_symlink() or not path.is_file() or not re.fullmatch(r"[A-Za-z0-9_.-]+", path.name):
            raise ValueError(f"invalid artifact: {path.name}")
        artifacts.append({"name": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                          "size": path.stat().st_size})
    manifest = {"version": version, "tag": "v" + version, "source_revision": revision,
                "repository": "Mewplane/syauth", "linux_glibc_minimum": "2.36",
                "artifacts": artifacts}
    (directory / "release.json").write_text(json.dumps(manifest, indent=2) + "\n")
    artifacts.append({"name": "release.json", "sha256": hashlib.sha256((directory / "release.json").read_bytes()).hexdigest()})
    (directory / "SHA256SUMS").write_text("".join(f"{item['sha256']}  {item['name']}\n" for item in artifacts))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    try:
        prepare(args.directory, args.version, args.revision)
    except (ValueError, OSError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
