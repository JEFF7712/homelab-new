{
  description = "NixOS homelab development and validation tools";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    { nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        formatter = pkgs.nixfmt;

        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            age
            git
            gitleaks
            kubeconform
            kubectl
            kubernetes-helm
            nixfmt
            opentofu
            pyright
            python313
            ruff
            sops
            yamllint
          ];
        };

        checks.repository-contract = pkgs.runCommand "repository-contract" {
          nativeBuildInputs = [ pkgs.python313 ];
        } "touch $out";
      }
    );
}
