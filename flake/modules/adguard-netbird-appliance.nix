{ pkgs, ... }:
{
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
    firewall = {
      enable = true;
      allowedUDPPorts = [ 51820 ];
      extraInputRules = ''
        ip saddr 10.0.10.0/24 tcp dport { 22, 3000 } accept
        ip saddr 10.0.30.0/24 tcp dport 53 accept
        ip saddr 10.0.30.0/24 udp dport 53 accept
        iifname "wt0" tcp dport 22 accept
      '';
    };
  };

  systemd.network = {
    enable = true;
    netdevs."20-netbird-vlan".netdevConfig = {
      Kind = "vlan";
      Name = "netbird-vlan";
    };
    netdevs."20-netbird-vlan".vlanConfig.Id = 60;
    networks = {
      "30-infrastructure" = {
        matchConfig.Name = "enp1s0";
        networkConfig = {
          Address = "10.0.30.10/24";
          DNS = "10.0.30.1";
          Gateway = "10.0.30.1";
          VLAN = "netbird-vlan";
        };
        linkConfig.RequiredForOnline = "routable";
      };
      "60-netbird-policy" = {
        matchConfig.Name = "netbird-vlan";
        networkConfig.Address = "10.0.60.2/24";
      };
    };
  };

  services.openssh = {
    enable = true;
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
      extraGroups = [
        "netbird"
        "wheel"
      ];
      openssh.authorizedKeys.keys = [
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILW7MVmIGzW4Eq1NJm4+gsGwQ+iL44bIfyAa/wdQ1srQ"
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFTXsL6q+O1d29vTd3TtK2F0MYPggS5KSHryvlIFBS1K"
      ];
    };
  };
  security.sudo.wheelNeedsPassword = false;

  services.adguardhome = {
    enable = true;
    host = "10.0.30.10";
    port = 3000;
    mutableSettings = false;
    settings = {
      users = [
        {
          name = "admin";
          password = "$2b$05$3OSxlPpIaeb7MFHKiRnMpeYYtOptanouC.abJWRC/axkq/n7AlrGW";
        }
      ];
      dns = {
        bind_hosts = [ "10.0.30.10" ];
        port = 53;
        bootstrap_dns = [
          "9.9.9.9"
          "149.112.112.112"
        ];
        upstream_dns = [ "https://dns.quad9.net/dns-query" ];
        fallback_dns = [ "1.1.1.1" ];
        protection_enabled = true;
      };
      dhcp.enabled = false;
      filtering = {
        enabled = true;
        filtering_enabled = true;
        filters_update_interval = 24;
      };
      filters = [
        {
          enabled = true;
          id = 1;
          name = "AdGuard DNS filter";
          url = "https://adguardteam.github.io/HostlistsRegistry/assets/filter_1.txt";
        }
      ];
    };
  };

  services.netbird = {
    useRoutingFeatures = "server";
    clients.default = {
      port = 51820;
      name = "netbird";
      interface = "wt0";
      hardened = true;
      autoStart = true;
      login.enable = false;
    };
  };

  environment.persistence."/persist" = {
    hideMounts = true;
    directories = [
      "/etc/ssh"
      "/var/lib/netbird"
      "/var/lib/nixos"
      "/var/lib/private/AdGuardHome"
      "/var/lib/systemd"
    ];
    files = [ "/etc/machine-id" ];
  };

  environment.systemPackages = with pkgs; [
    btrfs-progs
    cryptsetup
    curl
    ethtool
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
}
