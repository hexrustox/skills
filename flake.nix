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
          image = "ubuntu:latest";
          extraOptions = [
            "-e"
            "NIX_PATH"
            "-v"
            "xdg_bin:/root/.local/bin"
            "-v"
            "uv_data:/root/.local/share/uv"
          ];
          wrappers = [
            "description-trigger"

            "nixd"
            "skills"
            "uv"
          ];
        };
        container = pkgs.mkShellNoCC {
          packages = with pkgs; [
            cacert
            git
            nixd
            nixfmt
            skills
            uv
          ];
          shellHook = ''
            export PATH="$HOME/.local/bin:$PATH"
          '';
        };
      };

    };

}
