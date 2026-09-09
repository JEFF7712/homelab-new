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
      self,
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
      nixosConfigurations.nas-01 = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        modules = [
          disko.nixosModules.disko
          impermanence.nixosModules.impermanence
          ./hosts/nas-01
        ];
      };
      nixosConfigurations.homelab-01 = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        modules = [
          disko.nixosModules.disko
          impermanence.nixosModules.impermanence
          ./hosts/homelab-01
        ];
      };
      nixosConfigurations.homelab-02 = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        modules = [
          disko.nixosModules.disko
          impermanence.nixosModules.impermanence
          ./hosts/homelab-02
        ];
      };
      nixosConfigurations.homelab-03 = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        modules = [
          disko.nixosModules.disko
          impermanence.nixosModules.impermanence
          ./hosts/homelab-03
        ];
      };
      nixosConfigurations.homelab-01-registry = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        modules = [
          disko.nixosModules.disko
          impermanence.nixosModules.impermanence
          ./hosts/homelab-01
          ./modules/k3s-registry-client.nix
        ];
      };
      nixosConfigurations.homelab-02-registry = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        modules = [
          disko.nixosModules.disko
          impermanence.nixosModules.impermanence
          ./hosts/homelab-02
          ./modules/k3s-registry-client.nix
        ];
      };
      nixosConfigurations.homelab-03-registry = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        modules = [
          disko.nixosModules.disko
          impermanence.nixosModules.impermanence
          ./hosts/homelab-03
          ./modules/k3s-registry-client.nix
        ];
      };
    }
    // flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python313.withPackages (pythonPackages: [ pythonPackages.pyyaml ]);
      in
      {
        formatter = pkgs.nixfmt;

        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            age
            apacheHttpd
            attic-client
            cosign
            curl
            dnsutils
            git
            gitleaks
            glab
            just
            kubeconform
            kubectl
            kubernetes-helm
            nixfmt
            opentofu
            oras
            patchelf
            pyright
            python
            ruff
            shellcheck
            skopeo
            sops
            yamllint
          ];
        };

        checks.repository-contract =
          pkgs.runCommand "repository-contract"
            {
              nativeBuildInputs = [
                pkgs.bash
                pkgs.coreutils
                pkgs.git
                pkgs.jq
                pkgs.just
                pkgs.kubectl
                pkgs.patchelf
                python
              ];
            }
            ''
              cd ${../.}
              python -m unittest discover -s tests
              touch $out
            '';

        checks.zot-registry = self.nixosConfigurations.nas-01.config.services.homelab-zot-registry.package;
      }
    );
}
