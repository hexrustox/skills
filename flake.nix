{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-26.05";
    flake-parts.url = "github:hercules-ci/flake-parts";
    nix-capsule.url = "gitlab:codnixus/nix-capsule?ref=v0.8.0";
  };

  outputs =
    { flake-parts, ... }@inputs:
    flake-parts.lib.mkFlake { inherit inputs; } {
      perSystem =
        {
          system,
          ...
        }:
        let
          pkgs = import inputs.nixpkgs {
            inherit system;
            overlays = [
              inputs.nix-capsule.overlays.default
            ];
          };
          capsule-lib = inputs.nix-capsule.lib { inherit pkgs; };
        in
        {
          apps.default = capsule-lib.app;
          devShells = {
            default = capsule-lib.mkShell {
              image = "alpine:latest";
              devShell = "container";
              socketPath = "/tmp/skills/ncap-socket";
              containerName = "skills";
              extraOptions = [
              ];
              wrappers = [
                "skills"
              ];
            };

            container =
              pkgs.mkShellNoCC {
                packages = with pkgs; [
                  skills
                  git
                ];
              };
          };
        };

      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
    };
}

