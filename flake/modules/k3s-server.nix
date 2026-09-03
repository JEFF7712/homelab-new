{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.homelab.k3s;
in
{
  options.homelab.k3s = {
    enable = lib.mkEnableOption "the homelab k3s server role";

    primaryInterface = lib.mkOption {
      type = lib.types.str;
      description = "Physical interface attached to infrastructure VLAN 30.";
    };

    nodeIp = lib.mkOption {
      type = lib.types.str;
      description = "Stable VLAN 30 address used by this k3s server.";
    };

    clusterInit = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Initialize the embedded-etcd k3s cluster on this server.";
    };

    serverAddress = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      description = "Existing k3s API endpoint for joining this server.";
    };

    tokenFile = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      description = "Runtime-provisioned file containing the k3s cluster token.";
    };

    bootstrapCilium = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Bootstrap the pinned Cilium CNI through the k3s Helm controller.";
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = cfg.clusterInit || (cfg.serverAddress != null && cfg.tokenFile != null);
        message = "Joining k3s servers require serverAddress and tokenFile.";
      }
      {
        assertion = !(cfg.clusterInit && cfg.serverAddress != null);
        message = "The k3s cluster-init server must not join another server.";
      }
      {
        assertion = !cfg.bootstrapCilium || cfg.clusterInit;
        message = "Cilium bootstrap must run only on the cluster-init server.";
      }
    ];

    boot = {
      initrd.systemd.enable = true;
      loader = {
        efi.canTouchEfiVariables = true;
        systemd-boot.enable = true;
      };
    };

    hardware.enableRedistributableFirmware = true;
    time.timeZone = "America/Chicago";

    networking = {
      useDHCP = false;
      useNetworkd = true;
      nftables.enable = true;
      firewall = {
        enable = true;
        extraReversePathFilterRules = "ip saddr 10.42.0.0/16 accept";
        extraInputRules = ''
          ip saddr 10.0.10.0/24 tcp dport 22 accept
          ip saddr 10.0.30.0/24 tcp dport { 22, 179, 2379, 2380, 6443, 6444, 10250, 4240 } accept
          ip saddr 10.0.30.0/24 udp dport 8472 accept
          ip saddr 10.42.0.0/16 tcp dport { 6443, 10250 } accept
        '';
      };
    };

    systemd.network = {
      enable = true;
      networks."30-infrastructure" = {
        matchConfig.Name = cfg.primaryInterface;
        networkConfig = {
          Address = "${cfg.nodeIp}/24";
          DNS = "10.0.30.10";
          Gateway = "10.0.30.1";
        };
        linkConfig.RequiredForOnline = "routable";
      };
    };

    services.openssh = {
      enable = true;
      openFirewall = false;
      hostKeys = [
        {
          path = "/persist/etc/ssh/ssh_host_ed25519_key";
          type = "ed25519";
        }
        {
          bits = 4096;
          path = "/persist/etc/ssh/ssh_host_rsa_key";
          type = "rsa";
        }
      ];
      settings = {
        KbdInteractiveAuthentication = false;
        PasswordAuthentication = false;
        PermitRootLogin = "no";
      };
    };

    users = {
      mutableUsers = false;
      users.rupan = {
        isNormalUser = true;
        extraGroups = [ "wheel" ];
        openssh.authorizedKeys.keys = [
          "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILW7MVmIGzW4Eq1NJm4+gsGwQ+iL44bIfyAa/wdQ1srQ"
          "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFTXsL6q+O1d29vTd3TtK2F0MYPggS5KSHryvlIFBS1K"
        ];
      };
    };
    security.sudo.wheelNeedsPassword = false;

    services.smartd = {
      enable = true;
      autodetect = true;
    };

    services.k3s = {
      enable = true;
      role = "server";
      inherit (cfg) clusterInit tokenFile;
      serverAddr = lib.mkIf (cfg.serverAddress != null) cfg.serverAddress;
      extraFlags = [
        "--node-ip=${cfg.nodeIp}"
        "--advertise-address=${cfg.nodeIp}"
        "--flannel-backend=none"
        "--disable-network-policy"
        "--cluster-cidr=10.42.0.0/16"
        "--service-cidr=10.43.0.0/16"
        "--disable-kube-proxy"
        "--disable=servicelb"
        "--disable=traefik"
        "--disable=local-storage"
      ];
    };

    systemd.services.k3s = lib.mkIf (!cfg.clusterInit) {
      unitConfig.ConditionPathExists = cfg.tokenFile;
    };

    services.k3s.manifests = lib.mkIf cfg.bootstrapCilium {
      cilium.content = {
        apiVersion = "helm.cattle.io/v1";
        kind = "HelmChart";
        metadata = {
          name = "cilium";
          namespace = "kube-system";
        };
        spec = {
          bootstrap = true;
          chart = "cilium";
          createNamespace = false;
          repo = "https://helm.cilium.io";
          targetNamespace = "kube-system";
          version = "1.20.1";
          valuesContent = builtins.toJSON {
            bgpControlPlane.enabled = true;
            ipam.operator.clusterPoolIPv4PodCIDRList = [ "10.42.0.0/16" ];
            ipv4NativeRoutingCIDR = "10.42.0.0/16";
            k8sServiceHost = "127.0.0.1";
            k8sServicePort = 6443;
            kubeProxyReplacement = true;
            operator.replicas = 2;
          };
        };
      };
    };

    systemd.tmpfiles.rules = [
      "d /persist/etc/ssh 0700 root root -"
      "d /persist/secrets 0700 root root -"
    ];

    environment.persistence."/persist" = {
      hideMounts = true;
      directories = [
        "/var/lib/nixos"
        "/var/lib/rancher/k3s"
        "/var/lib/systemd"
      ];
      files = [ "/etc/machine-id" ];
    };

    environment.systemPackages = with pkgs; [
      btrfs-progs
      curl
      ethtool
      kubectl
      tcpdump
    ];

    nix = {
      gc = {
        automatic = true;
        dates = "weekly";
        options = "--delete-older-than 30d";
      };
      settings = {
        auto-optimise-store = true;
        experimental-features = [
          "nix-command"
          "flakes"
        ];
      };
    };

    zramSwap = {
      enable = true;
      memoryPercent = 25;
    };
  };
}
