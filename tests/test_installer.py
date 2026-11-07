"""Run the installer through mocked network/native-manager boundaries.

Journey: specs/journeys/JOURNEY-release-publication.md
"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.requests = self.root / "requests"
        self.calls = self.root / "calls"
        self.os_release = self.root / "os-release"
        self.os_release.write_text('ID=debian\nVERSION_ID="12"\n')
        self.payload = b"verified package content"
        self.asset = "syauth_0.1.1_amd64.deb"
        self.env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}",
                        SYAUTH_OS_RELEASE=str(self.os_release), TMPDIR=str(self.root))
        self.command("uname", "echo x86_64")
        self.command("id", "echo 0")
        self.command("getconf", "echo 'glibc 2.36'")
        for name in ("apt-get", "dnf", "zypper", "pacman"):
            self.command(name, f'printf "%s\\n" "$*" >> "{self.calls}"')
        self.prepare_network()

    def command(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/sh\n" + body + "\n")
        path.chmod(0o755)

    def prepare_network(self, checksum=None):
        digest = checksum or hashlib.sha256(self.payload).hexdigest()
        (self.root / "payload").write_bytes(self.payload)
        (self.root / "sums").write_text(f"{digest}  {self.asset}\n")
        (self.root / "release").write_text(json.dumps({"tag_name": "v0.1.1"}))
        self.command("curl", f'''set -eu
out=
while [ "$#" -gt 0 ]; do
    case "$1" in -o|--output) out=$2; shift 2;; *) url=$1; shift;; esac
done
printf '%s\\n' "$url" >> '{self.requests}'
case "$url" in
    */releases/latest|*/releases/tags/v*) source='{self.root}/release';;
    */SHA256SUMS) source='{self.root}/sums';;
    */{self.asset}) source='{self.root}/payload';;
    *) exit 22;;
esac
cp "$source" "$out"
''')

    def run_installer(self, *args):
        return subprocess.run(["sh", str(REPO / "scripts/install.sh"), *args],
                              env=self.env, text=True, capture_output=True)

    def test_downloads_and_guidance_use_the_current_repository_owner(self):
        result = self.run_installer("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        urls = self.requests.read_text().splitlines()
        self.assertEqual(urls[0], "https://api.github.com/repos/Mewplane/syauth/releases/latest")
        self.assertTrue(all(url.startswith("https://github.com/Mewplane/syauth/") for url in urls[1:]))
        result = self.run_installer()
        self.assertIn("https://mewplane.github.io/syauth/tutorials/first-unlock/", result.stdout)

    def test_latest_is_resolved_once_and_verified_before_apt(self):
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("install -y", self.calls.read_text())
        self.assertTrue(self.calls.read_text().startswith("update -q\n"))
        urls = self.requests.read_text().splitlines()
        self.assertEqual(sum(url.endswith("/releases/latest") for url in urls), 1)
        self.assertTrue(all("/download/v0.1.1/" in url for url in urls[1:]))
        self.assertEqual(list(self.root.glob("syauth-install.*")), [])

    def test_checksum_tampering_refuses_privileged_install_and_cleans(self):
        self.prepare_network(checksum="0" * 64)
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Checksum verification failed", result.stderr)
        self.assertFalse(self.calls.exists())
        self.assertEqual(list(self.root.glob("syauth-install.*")), [])

    def test_duplicate_manifest_entry_is_rejected(self):
        sums = self.root / "sums"
        sums.write_text(sums.read_text() * 2)
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.calls.exists())

    def test_missing_exact_entry_cannot_match_filename_prefix(self):
        sums = self.root / "sums"
        sums.write_text(sums.read_text().replace(self.asset, self.asset + ".malicious"))
        self.assertNotEqual(self.run_installer().returncode, 0)
        self.assertFalse(self.calls.exists())

    def test_dry_run_verifies_download_without_manager(self):
        result = self.run_installer("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Verified", result.stdout)
        self.assertFalse(self.calls.exists())

    def test_explicit_version_uses_tag_api(self):
        result = self.run_installer("--version", "v0.1.1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("/releases/tags/v0.1.1", self.requests.read_text())
        self.assertNotIn("/latest", self.requests.read_text())

    def test_api_tag_must_match_requested_version(self):
        self.assertNotEqual(self.run_installer("--version", "0.1.2").returncode, 0)
        self.assertFalse(self.calls.exists())

    def test_invalid_version_is_rejected_before_network(self):
        for version in ("../../evil", "0.1", "1.2.3;id", ""):
            with self.subTest(version=version):
                self.assertNotEqual(self.run_installer("--version", version).returncode, 0)
        self.assertFalse(self.requests.exists())

    def test_unsupported_platforms_fail_before_network(self):
        for distro in ("alpine", "nixos", "unknown"):
            with self.subTest(distro=distro):
                self.os_release.write_text(f"ID={distro}\n")
                self.assertNotEqual(self.run_installer().returncode, 0)
        self.assertFalse(self.requests.exists())

    def test_old_glibc_is_rejected_before_network(self):
        for version in ("2.31", "2.35"):
            self.command("getconf", f"echo 'glibc {version}'")
            self.assertNotEqual(self.run_installer().returncode, 0)
        self.assertFalse(self.requests.exists())

    def test_unsupported_architecture_is_rejected_before_network(self):
        self.command("uname", "echo riscv64")
        self.assertNotEqual(self.run_installer().returncode, 0)
        self.assertFalse(self.requests.exists())

    def test_nonroot_elevates_only_verified_native_install(self):
        self.command("id", "echo 1000")
        sudo_calls = self.root / "sudo-calls"
        self.command("sudo", f'printf "%s\\n" "$*" > "{sudo_calls}"\n"$@"')
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(sudo_calls.read_text().startswith("apt-get install -y "))
        self.assertNotIn("curl", sudo_calls.read_text())

    def test_manager_failure_propagates_and_cleans(self):
        self.command("apt-get", "exit 42")
        self.assertEqual(self.run_installer().returncode, 42)
        self.assertEqual(list(self.root.glob("syauth-install.*")), [])

    def test_invalid_checksum_hash_is_rejected(self):
        for digest in ("a" * 63, "g" * 64):
            self.prepare_network(checksum=digest)
            self.assertNotEqual(self.run_installer().returncode, 0)
        self.assertFalse(self.calls.exists())

    def test_invalid_api_tag_is_rejected(self):
        for tag in ("../escape", "v1.2", "v1.2.3;id", ""):
            (self.root / "release").write_text(json.dumps({"tag_name": tag}))
            self.assertNotEqual(self.run_installer().returncode, 0)
        self.assertFalse(self.calls.exists())

    def test_network_failure_never_installs_and_cleans(self):
        self.command("curl", "exit 22")
        self.assertNotEqual(self.run_installer().returncode, 0)
        self.assertFalse(self.calls.exists())
        self.assertEqual(list(self.root.glob("syauth-install.*")), [])

    def test_native_managers_and_arm_architecture_selection(self):
        for distro, manager, suffix in (
            ("fedora", "dnf", "syauth-0.1.1-4.aarch64.rpm"),
            ("opensuse-tumbleweed", "zypper", "syauth-0.1.1-4.aarch64.rpm"),
            ("arch", "pacman", "syauth-0.1.1-1-aarch64.pkg.tar.zst"),
            ("ubuntu", "apt-get", "syauth_0.1.1_arm64.deb"),
        ):
            with self.subTest(distro=distro):
                self.command("uname", "echo aarch64")
                self.os_release.write_text(f"ID={distro}\n")
                self.asset = suffix
                self.prepare_network()
                self.command(manager, f'printf "{manager} %s\\n" "$*" > "{self.calls}"')
                result = self.run_installer()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(self.calls.read_text().startswith(manager + " "))
                self.assertIn(suffix, self.calls.read_text())


if __name__ == "__main__":
    unittest.main()
