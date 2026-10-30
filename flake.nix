{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs?ref=nixos-unstable";
    nix-capsule.url = "github:hexrustox/nix-capsule?ref=v0.11.1";
    rust-overlay = {
      url = "github:oxalica/rust-overlay";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    { ... }@inputs:
    let
      system = "x86_64-linux";
      pkgs = import inputs.nixpkgs {
        inherit system;
        overlays = [
          inputs.rust-overlay.overlays.default
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
            "xdg_bin:/root/.local/bin"
            "-v"
            "uv_tool:/root/.local/share/uv/tools"
          ];
          wrappers = [
            "cargo"
            "nixd"
            "uv"
            "validate-skill"
          ];
        };
        container = pkgs.mkShellNoCC {
          packages = with pkgs; [
            (rust-bin.stable."1.99.1".default.override {
              extensions = [
                "rust-src"
                "rust-analyzer"
              ];
            })

            git
            nixd
            nixfmt
            skills
            uv
            python3
          ];
          shellHook = ''
            export PATH="$HOME/.local/bin:$PATH"
          '';
        };
      };

    };

}
