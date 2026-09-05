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
    nftables.enable = true;
    firewall = {
      enable = true;
      allowedUDPPorts = [ 51820 ];
      extraInputRules = ''
        ip saddr 10.0.10.0/24 tcp dport { 22, 3000 } accept
        ip saddr 10.0.10.0/24 tcp dport 53 accept
        ip saddr 10.0.10.0/24 udp dport 53 accept
        ip saddr 10.0.30.0/24 tcp dport 53 accept
        ip saddr 10.0.30.0/24 udp dport 53 accept
        iifname "wt0" tcp dport { 22, 53, 3000 } accept
        iifname "wt0" udp dport 53 accept
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
          password = "$2b$10$EY4fb1ANVYrI8ud2FQnJFOrnx5coVM3wwvZau1SOKoKNKdb9snryi";
        }
      ];
      dns = {
        bind_hosts = [ "10.0.30.10" ];
        port = 53;
        bootstrap_dns = [
          "9.9.9.9"
          "149.112.112.112"
        ];
        upstream_dns = [
          "[/homelab/]10.0.30.1"
          "https://dns.quad9.net/dns-query"
        ];
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
        {
          enabled = true;
          id = 2;
          name = "OISD Big";
          url = "https://big.oisd.nl";
        }
        {
          enabled = true;
          id = 3;
          name = "AdGuard Mobile Ads filter";
          url = "https://adguardteam.github.io/HostlistsRegistry/assets/filter_11.txt";
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

  systemd.services = {
    adguardhome = {
      after = [ "network-online.target" ];
      wants = [ "network-online.target" ];
      serviceConfig.StateDirectoryMode = "0700";
    };
    netbird = {
      after = [ "network-online.target" ];
      wants = [ "network-online.target" ];
    };
  };

  systemd.tmpfiles.rules = [
    "d /var/lib/private 0700 root root -"
    "d /persist/etc/ssh 0700 root root -"
    "d /persist/var/lib/private 0700 root root -"
    "d /persist/var/lib/private/AdGuardHome 0700 nobody nogroup -"
  ];

  environment.persistence."/persist" = {
    hideMounts = true;
    directories = [
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
