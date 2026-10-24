{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs?ref=nixos-unstable";
    nix-capsule.url = "github:hexrustox/nix-capsule?ref=v0.11.1";
  };

  outputs =
    { ... }@inputs:
    let
      system = "x86_64-linux";
      pkgs = import inputs.nixpkgs {
        inherit system;
        overlays = [
          inputs.nix-capsule.overlays.default

        ];
      };
      capsule-lib = inputs.nix-capsule.lib { inherit pkgs; };
    in
    {
      devShells.${system} = {
        default = capsule-lib.mkShell {
          image = "alpine:latest";
          extraOptions = [
            "-e"
            "NIX_PATH"
            "-v"
            "xdg-bin:/root/.local/bin"
            "-v"
            "xdg-data:/root/.local/share"
          ];
          wrappers = [
            "nixd"
            "skillevaluator"
          ];
        };
        container = pkgs.mkShellNoCC {
          packages = with pkgs; [
            git
            nixd
            nixfmt
            skills
            uv
          ];
          shellHook = ''
            export PATH="/root/.local/bin:$PATH"
          '';
        };
      };

    };

}
