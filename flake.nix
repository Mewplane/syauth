{
  description = "syauth — phone-as-key unlock for Linux PAM";
  # Nix configuration: allow binary cache from nix-community to speed up builds

  nixConfig = {
    extra-substituters = [ "https://nix-community.cachix.org" ];
    extra-trusted-public-keys = [
      "nix-community.cachix.org-1:mB9FSh9qf2dCimDSUo8Zy7bkq5CX+/rkCWyvRCYg3Fs"
    ];
  };

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    fenix = {
      url = "github:nix-community/fenix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    git-hooks = {
      url = "github:cachix/git-hooks.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      fenix,
      git-hooks,
    }:
    let
      eachSystem = nixpkgs.lib.genAttrs [
        "x86_64-linux"
        "aarch64-linux"
      ];
      pkgsFor = system: nixpkgs.legacyPackages.${system};
      toolchainFor = system: fenix.packages.${system}.stable.toolchain;

      # `git-hooks.nix` installs the pre-commit configuration when the
      # development shell starts. Rust hooks use the flake's pinned toolchain
      # so local commits and `make lint` agree.
      preCommitFor =
        system:
        let
          toolchain = toolchainFor system;
        in
        git-hooks.lib.${system}.run {
          src = ./.;
          hooks = {
            check-added-large-files.enable = true;
            check-merge-conflicts.enable = true;
            deadnix.enable = true;
            nixfmt.enable = true;
            statix.enable = true;

            clippy = {
              enable = true;
              packageOverrides = {
                cargo = toolchain;
                clippy = toolchain;
              };
              settings = {
                allFeatures = true;
                denyWarnings = true;
                extraArgs = "--workspace --all-targets";
              };
            };

            rustfmt = {
              enable = true;
              packageOverrides = {
                cargo = toolchain;
                rustfmt = toolchain;
              };
              settings.check = true;
            };
          };
        };
    in
    {
      packages = eachSystem (system: rec {
        syauth = (pkgsFor system).callPackage ./nix/package.nix {
          rustToolchain = toolchainFor system;
        };
        default = syauth;
      });

      apps = eachSystem (system: rec {
        syauth = {
          type = "app";
          program = "${self.packages.${system}.syauth}/bin/syauth";
          meta.description = "Run the syauth command-line tool";
        };
        default = syauth;
      });

      devShells = eachSystem (
        system:
        let
          pkgs = pkgsFor system;
          preCommit = preCommitFor system;
        in
        {
          default = pkgs.mkShell {
            packages = [
              (toolchainFor system)
            ]
            ++ (with pkgs; [
              gnumake
              pkg-config
              dbus
              python3
              git
              cargo-audit
              cargo-deny
            ])
            ++ preCommit.enabledPackages;
            inherit (preCommit) shellHook;
          };
        }
      );

      nixosModules.default = import ./nix/modules/nixos.nix { inherit self; };

      checks = eachSystem (system: {
        package = self.packages.${system}.syauth;
        nixos-module = import ./nix/check.nix {
          inherit nixpkgs;
          pkgs = pkgsFor system;
          module = self.nixosModules.default;
        };
      });

      formatter = eachSystem (system: (pkgsFor system).nixfmt-rfc-style);
    };
}
