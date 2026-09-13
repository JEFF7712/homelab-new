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
            cloud-utils
            curl
            dnsutils
            git
            gitleaks
            glab
            just
            kubeconform
            kubectl
            kubernetes-helm
            libvirt
            nixfmt
            nodejs
            opentofu
            oras
            patchelf
            pyright
            qemu_kvm
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
                pkgs.libvirt
                pkgs.nodejs
                pkgs.patchelf
                python
              ];
            }
            ''
              cd ${../.}
              python -m unittest discover -s tests
              touch $out
            '';

        checks.agent-workspace-network =
          let
            evaluated = nixpkgs.lib.nixosSystem {
              inherit system;
              modules = [
                ./modules/agent-workspace-network.nix
                {
                  system.stateVersion = "26.05";
                  networking.hostName = "homelab-01";
                  networking.useNetworkd = true;
                  services.agent-workspace-network.enable = true;
                }
              ];
            };
          in
          pkgs.runCommand "agent-workspace-network-evaluation" { } ''
            test ${nixpkgs.lib.escapeShellArg (builtins.toJSON (builtins.attrNames evaluated.config.networking.nftables.tables))} = '["agent-workspaces"]'
            touch $out
          '';

        checks.agent-workspace-packet-flow = import ./tests/agent-workspace-packet-flow.nix {
          inherit nixpkgs system;
        };

        checks.agent-workspace-host-reservations =
          let
            host = self.nixosConfigurations.homelab-01.config;
          in
          pkgs.runCommand "agent-workspace-host-reservations" { } ''
            test ${nixpkgs.lib.escapeShellArg (builtins.toJSON host.services.k3s.extraFlags)} = ${
              nixpkgs.lib.escapeShellArg (
                builtins.toJSON [
                  "--node-ip=10.0.30.11"
                  "--advertise-address=10.0.30.11"
                  "--flannel-backend=none"
                  "--disable-network-policy"
                  "--cluster-cidr=10.42.0.0/16"
                  "--service-cidr=10.43.0.0/16"
                  "--disable-kube-proxy"
                  "--disable=servicelb"
                  "--disable=traefik"
                  "--disable=local-storage"
                  "--kubelet-arg=system-reserved=cpu=2,memory=10Gi"
                ]
              )
            }
            test ${
              nixpkgs.lib.escapeShellArg host.systemd.slices."machine-agent\\x2dworkspaces".sliceConfig.CPUQuota
            } = 200%
            test ${
              nixpkgs.lib.escapeShellArg host.systemd.slices."machine-agent\\x2dworkspaces".sliceConfig.MemoryMax
            } = 10240M
            touch $out
          '';

        checks.agent-workspace-libvirt-normalization =
          import ./tests/agent-workspace-libvirt-normalization.nix
            {
              inherit nixpkgs system;
            };

        checks.zot-registry = self.nixosConfigurations.nas-01.config.services.homelab-zot-registry.package;
      }
    );
}
