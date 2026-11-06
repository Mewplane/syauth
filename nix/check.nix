# Journey: specs/journeys/JOURNEY-S-023-nix-modules.md
{
  nixpkgs,
  pkgs,
  module,
}:
let
  inherit (pkgs) lib;
  user = "fixture";
  socket = "socket=/run/user/1000/syauth/auth.sock";
  evaluate =
    modules:
    (nixpkgs.lib.nixosSystem {
      system = pkgs.stdenv.hostPlatform.system;
      modules = [
        {
          system.stateVersion = "25.11";
          users.users.${user} = {
            isNormalUser = true;
            uid = 1000;
          };
          security.sudo.enable = false;
          security.sudo-rs.enable = true;
          services.displayManager.plasma-login-manager.enable = true;
          services.desktopManager.plasma6.enable = true;
        }
      ]
      ++ modules;
    }).config;
  baseline = evaluate [ ];
  setup.services.syauth = {
    enable = true;
    desktopUser = user;
  };
  noPam = evaluate [
    module
    setup
  ];
  services = [
    "sudo"
    "sudo-i"
    "kde"
    "plasmalogin"
  ];
  enabled = evaluate [
    module
    setup
    {
      services.syauth.pam = {
        inherit services;
        moduleArgs = [ socket ];
      };
    }
  ];
  override = evaluate [
    module
    setup
    {
      services.syauth.pam = {
        services = [ "sudo" ];
        control = "required";
      };
    }
  ];
  textOverride = evaluate [
    module
    setup
    {
      services.syauth.pam.services = [ "sudo" ];
      security.pam.services.sudo.text = "# pam_syauth.so\nauth required pam_unix.so\n";
    }
  ];
  pamFailures =
    config:
    builtins.filter (a: !a.assertion && lib.hasInfix "lacks an auth rule" a.message) config.assertions;
  pam = config: name: config.security.pam.services.${name};
  unit = enabled.systemd.user.services.syauth-presenced;
  hasRule =
    name:
    let
      service = pam enabled name;
      anchor = if name == "plasmalogin" then "login" else "unix";
    in
    service.rules.auth.syauth.order < service.rules.auth.${anchor}.order
    && lib.hasInfix (builtins.unsafeDiscardStringContext "auth sufficient ${enabled.services.syauth.package}/lib/security/pam_syauth.so ${socket}") service.text;
in
assert noPam.security.pam.services.sudo.text == baseline.security.pam.services.sudo.text;
assert unit.unitConfig.ConditionUser == user && builtins.elem "default.target" unit.wantedBy;
assert builtins.elem "d /var/lib/syauth 0700 ${user} users -" enabled.systemd.tmpfiles.rules;
assert lib.all hasRule services;
assert pamFailures enabled == [ ] && builtins.length (pamFailures textOverride) == 1;
assert (pam override "sudo").rules.auth.syauth.control == "required";
pkgs.runCommand "syauth-nixos-module-check" { } "touch $out"
