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
            "xdg-bin:/root/.local/bin"
            "-v"
            "xdg-data:/root/.local/share"
          ];
          wrappers = [
            "cargo"
            "jq"
            "nixd"
            "skillevaluator"
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
            jq
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
