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
      # OpenCode 1.19.5 predates the opencode-go provider in its bundled
      # models.dev data, so declare it explicitly. The key comes from the
      # OPENCODE_API_KEY the host shell forwards into the container.
      opencodeEvalConfig = pkgs.writeText "opencode-eval.json" (
        builtins.toJSON {
          "$schema" = "https://opencode.ai/config.json";
          provider = {
            "opencode-go" = {
              name = "OpenCode Go";
              npm = "@ai-sdk/openai-compatible";
              options = {
                baseURL = "https://opencode.ai/inference/go/openai/v1";
                apiKey = "{env:OPENCODE_API_KEY}";
              };
              models = {
                "deepseek-v4.1-flash" = {
                  name = "DeepSeek V4.1 Flash";
                };
              };
            };
          };
        }
      );
    in
    {
      devShells.${system} = {
        default = capsule-lib.mkShell {
          image = "ubuntu:latest";
          envForward = [
            "OPENCODE_API_KEY"
          ];
          extraOptions = [
            "-e"
            "NIX_PATH"
            "-v"
            "xdg_bin:/root/.local/bin"
            "-v"
            "uv_tool:/root/.local/share/uv/tools"
            "-v"
            "npm_prefix:/root/.local/share/npm"
            "-v"
            "${opencodeEvalConfig}:/root/.config/opencode/opencode.json:ro"
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

            cacert
            git
            nixd
            nixfmt
            nodejs_24
            skills
            uv
            python3
          ];
          shellHook = ''
            export PATH="$HOME/.local/bin:$HOME/.local/share/npm/bin:$PATH"
            export NPM_CONFIG_PREFIX="$HOME/.local/share/npm"
          '';
        };
      };

    };

}
