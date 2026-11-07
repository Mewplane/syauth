{ self }:
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.syauth;
  store = "/var/lib/syauth";
  account = config.users.users.${cfg.desktopUser} or { };
  pamModule = "${cfg.package}/lib/security/pam_syauth.so";
  desktopUid = account.uid or null;

  anchorOrder =
    name:
    let
      # Exclude the injected rule because its order depends on this lookup.
      rules = removeAttrs config.security.pam.services.${name}.rules.auth [ "syauth" ];
      orders = lib.mapAttrsToList (_: rule: rule.order) (lib.filterAttrs (_: rule: rule.enable) rules);
    in
    if rules.unix.enable or false then
      rules.unix.order
    else if orders != [ ] then
      lib.head (lib.sort builtins.lessThan orders)
    else
      throw "services.syauth.pam.services: ${name} has no enabled auth rule to anchor syauth to.";

  hasSyauthRule =
    text:
    lib.any (
      line:
      builtins.match "[[:blank:]]*auth[[:blank:]]+([[][^]]+[]]|[^[:blank:]]+)[[:blank:]]+([^[:blank:]]*/)?pam_syauth[.]so([[:blank:]].*)?" line
      != null
    ) (lib.splitString "\n" text);
in
{
  options.services.syauth = {
    enable = lib.mkEnableOption "syauth for one desktop account";

    desktopUser = lib.mkOption {
      type = lib.types.str;
      example = "alice";
      description = "Account that pairs phones, owns the bond store, and runs the user service.";
    };

    package = lib.mkOption {
      type = lib.types.package;
      default = self.packages.${pkgs.stdenv.hostPlatform.system}.syauth;
      defaultText = lib.literalExpression "self.packages.\${system}.syauth";
      description = "Package providing the CLI, daemon, and PAM module.";
    };

    installCli = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = "Add the syauth package to the system PATH.";
    };

    pam = {
      services = lib.mkOption {
        type = lib.types.listOf lib.types.str;
        default = [ ];
        example = [
          "sudo"
          "sudo-i"
        ];
        description = "PAM services to configure for phone authentication.";
      };

      control = lib.mkOption {
        type = lib.types.str;
        default = "sufficient";
        description = "PAM control field used for the syauth rule in the selected services.";
      };

      moduleArgs = lib.mkOption {
        type = lib.types.listOf lib.types.str;
        default = lib.optional (
          desktopUid != null
        ) "socket=/run/user/${toString desktopUid}/syauth/auth.sock";
        defaultText = lib.literalExpression ''[ "socket=/run/user/<desktopUser UID>/syauth/auth.sock" ] when the UID is declared, otherwise [ ]'';
        example = [ "socket=/run/user/1000/syauth/auth.sock" ];
        description = "Arguments passed to pam_syauth.so in each selected service.";
      };
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = config.users.users ? ${cfg.desktopUser};
        message = "services.syauth.desktopUser must name an account declared in users.users.";
      }
      {
        assertion = cfg.pam.services == [ ] || lib.any (lib.hasPrefix "socket=/") cfg.pam.moduleArgs;
        message = "services.syauth.pam.moduleArgs requires an absolute socket= path when PAM is enabled. Declare users.users.<desktopUser>.uid or set pam.moduleArgs explicitly.";
      }
    ]
    ++ map (name: {
      assertion = hasSyauthRule config.security.pam.services.${name}.text;
      message = "PAM service ${name} lacks an auth rule for pam_syauth.so. Check security.pam.services.${name}.text.";
    }) cfg.pam.services;

    systemd.tmpfiles.rules = [ "d ${store} 0700 ${cfg.desktopUser} ${account.group or "-"} -" ];
    environment.systemPackages = lib.optional cfg.installCli cfg.package;

    systemd.user.services.syauth-presenced = {
      description = "syauth phone-as-key presence daemon";
      wantedBy = [ "default.target" ];
      unitConfig = {
        ConditionUser = cfg.desktopUser;
        ConditionPathIsDirectory = "%t";
        StartLimitIntervalSec = 0;
      };
      serviceConfig = {
        ExecStart = "${cfg.package}/bin/syauth-presenced";
        Restart = "on-failure";
        RestartSec = 2;
        TimeoutStopSec = 5;
        NoNewPrivileges = true;
        ProtectSystem = "strict";
        ProtectHome = "read-only";
        ReadWritePaths = [
          store
          "%t"
        ];
      };
    };

    security.pam.services = lib.genAttrs cfg.pam.services (name: {
      rules.auth.syauth = {
        inherit (cfg.pam) control;
        modulePath = pamModule;
        order = anchorOrder name - 10;
        args = cfg.pam.moduleArgs;
      };
    });
  };
}
