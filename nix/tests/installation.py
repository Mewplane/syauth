# Regression: test installed PAM and daemon together in a disposable VM.
import json, shlex
start_all()
machine.wait_for_unit("multi-user.target")
base = machine.succeed("readlink -f /run/current-system").strip()
package = "@syauth@"
def alice(command, ok=True):
    run = "su - alice -c " + shlex.quote(command)
    return (machine.succeed if ok else machine.fail)(run)
def bob(command, ok=True):
    run = "su - bob -c " + shlex.quote(command)
    return (machine.succeed if ok else machine.fail)(run)
def sudo(password, ok=True):
    return alice("printf '%s\\n' " + shlex.quote(password) + " | sudo -k -S -p '' true", ok)
def switch(name=None):
    path = base if name is None else base + "/specialisation/" + name
    machine.succeed(path + "/bin/switch-to-configuration test")
def userctl(command, ok=True):
    return alice("XDG_RUNTIME_DIR=/run/user/1100 systemctl --user " + command, ok)
def ready():
    machine.wait_until_succeeds("su - alice -c 'XDG_RUNTIME_DIR=/run/user/1100 syauth status --json' | grep -q '\"transport_ready\": true'", timeout=60)
with subtest("installed binaries and PAM loader closure"):
    assert machine.succeed("syauth --version").strip() == "syauth @version@"
    machine.succeed(package + "/bin/syauth-presenced --help | grep -- --socket")
    machine.succeed("ldd " + package + "/lib/security/pam_syauth.so | tee /root/pam-loader.txt; ! grep -q 'not found' /root/pam-loader.txt")
    machine.succeed("test -f " + package + "/lib/security/pam_syauth.so")
    machine.succeed("grep -F 'auth sufficient " + package + "/lib/security/pam_syauth.so socket=/run/user/1100/syauth/auth.sock' /etc/pam.d/sudo")
with subtest("private storage and per-user service isolation"):
    assert machine.succeed("stat -c '%a %U %G' /var/lib/syauth").strip() == "700 alice users"
    machine.succeed("loginctl enable-linger alice; loginctl enable-linger bob")
    machine.wait_for_unit("user@1100.service")
    machine.wait_for_unit("user@1101.service")
    assert userctl("show syauth-presenced -p StartLimitIntervalUSec --value").strip() == "0"
    machine.wait_until_succeeds("test $(su - alice -c 'XDG_RUNTIME_DIR=/run/user/1100 systemctl --user show syauth-presenced -p NRestarts --value') -ge 3", timeout=60)
    machine.succeed("journalctl _UID=1100 --no-pager | grep -q 'Bluetooth transport unavailable'")
    assert bob("XDG_RUNTIME_DIR=/run/user/1101 systemctl --user show syauth-presenced -p ConditionResult --value").strip() == "no"
    assert bob("XDG_RUNTIME_DIR=/run/user/1101 systemctl --user show syauth-presenced -p MainPID --value").strip() == "0"
    bob("test -r /var/lib/syauth/bonds.toml", False)
with subtest("missing phone still requires a valid Unix password"):
    sudo("wrong-password", False)
    sudo("vm-alice-test")
    assert machine.succeed("stat -c '%a %U %G' /var/lib/syauth/last.log").strip() == "600 alice users"
with subtest("synthetic signed response traverses real daemon and installed PAM"):
    userctl("stop syauth-presenced")
    machine.succeed("@python@/bin/python @fixture@")
    data = json.loads(machine.succeed("cat /root/fixture.json"))
    daemon = package + "/bin/syauth-presenced --peripheral fake --test-fixed-nonce " + data["nonce"] + " --inject-response " + data["peer"] + ":" + data["signature"]
    def inject(command):
        unit = "[Service]\\nExecStart=\\nExecStart=" + command + "\\n"
        alice("mkdir -p ~/.config/systemd/user/syauth-presenced.service.d; printf '%b' " + shlex.quote(unit) + " > ~/.config/systemd/user/syauth-presenced.service.d/vm-fixture.conf")
        userctl("daemon-reload")
        userctl("restart syauth-presenced")
        ready()
    inject(daemon)
    sudo("wrong-password")
    machine.succeed("grep -q ',ok,' /var/lib/syauth/last.log")
    assert machine.succeed("stat -c '%a %U %G' /var/lib/syauth/last.log").strip() == "600 alice users"
    machine.fail("journalctl _UID=1100 --no-pager | grep -q 'audit log open failed'")
    assert json.loads(alice("XDG_RUNTIME_DIR=/run/user/1100 syauth status --json"))["daemon"]["transport_ready"] is True
    bob("cat /var/lib/syauth/bonds.toml", False)
    bob("cat /var/lib/syauth/keys/" + data["peer"] + ".bin", False)
with subtest("bad signature is rejected before password fallback"):
    inject(package + "/bin/syauth-presenced --peripheral fake --test-fixed-nonce " + data["nonce"] + " --inject-response " + data["peer"] + ":" + "00" * 64)
    sudo("wrong-password", False)
    machine.succeed("grep -q 'bad-signature' /var/lib/syauth/last.log")
    sudo("vm-alice-test")
with subtest("explicit socket override and automatic default both authenticate"):
    inject(daemon)
    switch("explicitArgs")
    ready()
    sudo("wrong-password")
    switch()
    userctl("restart syauth-presenced")
    ready()
    sudo("wrong-password")
with subtest("required control retains failure despite a correct password"):
    userctl("stop syauth-presenced")
    switch("required")
    userctl("stop syauth-presenced")
    machine.succeed("grep -F 'auth required ' /etc/pam.d/sudo | grep pam_syauth")
    sudo("vm-alice-test", False)
    switch()
with subtest("sudo-rs consumes the generated PAM rules"):
    switch("sudoRs")
    userctl("stop syauth-presenced")
    sudo("wrong-password", False)
    sudo("vm-alice-test")
    switch()
with subtest("profile install and removal is independent of module activation"):
    bob("nix profile install " + package)
    assert bob("~/.nix-profile/bin/syauth --version").strip() == "syauth @version@"
    bob("test -f ~/.nix-profile/lib/security/pam_syauth.so")
    profile = json.loads(bob("nix profile list --json"))
    entry = next(iter(profile["elements"]))
    bob("nix profile remove " + shlex.quote(entry))
    bob("test -e ~/.nix-profile/bin/syauth", False)
with subtest("disable and rollback preserve the existing bond store"):
    alice("rm ~/.config/systemd/user/syauth-presenced.service.d/vm-fixture.conf")
    userctl("daemon-reload")
    before = machine.succeed("find /var/lib/syauth -type f -exec sha256sum {} + | sort")
    switch("noPam")
    machine.fail("grep -q pam_syauth /etc/pam.d/sudo")
    sudo("vm-alice-test")
    switch("disabled")
    machine.fail("command -v syauth")
    machine.fail("grep -q pam_syauth /etc/pam.d/sudo")
    assert machine.succeed("find /var/lib/syauth -type f -exec sha256sum {} + | sort") == before
    switch()
    machine.succeed("command -v syauth")
    assert machine.succeed("stat -c '%a %U %G' /var/lib/syauth").strip() == "700 alice users"
    assert machine.succeed("find /var/lib/syauth -type f -exec sha256sum {} + | sort") == before
machine.succeed("journalctl --no-pager > /root/syauth-vm-journal.txt")

print("SYAUTH_NIXOS_VM_CHECKS_PASSED")
