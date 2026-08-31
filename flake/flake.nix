{
  description = "NixOS homelab development and validation tools";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    disko = {
      url = "github:nix-community/disko";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    impermanence.url = "github:nix-community/impermanence";
  };

  outputs =
    {
      nixpkgs,
      flake-utils,
      disko,
      impermanence,
      ...
    }:
    {
      nixosConfigurations.adguard-netbird-01 = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        modules = [
          disko.nixosModules.disko
          impermanence.nixosModules.impermanence
          ./hosts/adguard-netbird-01
        ];
      };
    }
    // flake-utils.lib.eachDefaultSystem (
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

        checks.repository-contract =
          pkgs.runCommand "repository-contract"
            {
              nativeBuildInputs = [ pkgs.python313 ];
            }
            ''
              cd ${../.}
              python -m unittest discover -s tests
              touch $out
            '';
      }
    );
}
