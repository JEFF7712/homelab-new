{ pkgs, ... }:
{
  boot = {
    initrd.systemd.enable = true;
    loader = {
      efi.canTouchEfiVariables = true;
      grub = {
        enable = true;
        efiSupport = true;
        devices = [ "nodev" ];
        mirroredBoots = [
          {
            path = "/boot";
            devices = [ "/dev/disk/by-id/nvme-WDC_PC_SN520_SDAPNUW-256G-1006_2022C1800396" ];
            efiBootloaderId = "NixOS-a";
          }
          {
            path = "/boot-fallback";
            devices = [ "/dev/disk/by-id/nvme-WDC_PC_SN520_SDAPNUW-256G-1006_2022BA804857" ];
            efiBootloaderId = "NixOS-b";
          }
        ];
      };
    };
    supportedFilesystems = [ "zfs" ];
    zfs.forceImportRoot = false;
  };

  hardware.enableRedistributableFirmware = true;
  time.timeZone = "America/Chicago";
  networking.hostId = "31eabe12";

  networking = {
    useDHCP = false;
    useNetworkd = true;
    nftables.enable = true;
    firewall = {
      enable = true;
      extraInputRules = ''
        ip saddr 10.0.10.0/24 tcp dport 22 accept
        ip saddr 10.0.30.0/24 tcp dport 22 accept
        ip saddr 100.64.0.0/10 tcp dport 22 accept
      '';
    };
  };

  systemd.network = {
    enable = true;
    networks."30-infrastructure" = {
      matchConfig.Name = "enp5s0";
      networkConfig = {
        Address = "10.0.30.20/24";
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
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFWt07ttKX2X+E5CbwL4To1AuwuwuIaKWUePIrAwGrK0 homelab-nas-deploy"
      ];
    };
  };
  security.sudo.wheelNeedsPassword = false;

  services.smartd = {
    enable = true;
    autodetect = true;
  };
  services.zfs.autoScrub = {
    enable = true;
    interval = "weekly";
  };
  services.zfs.trim = {
    enable = true;
    interval = "weekly";
  };

  systemd.tmpfiles.rules = [
    "d /persist/etc/ssh 0700 root root -"
    "d /persist/var/lib/smartmontools 0755 root root -"
  ];

  environment.persistence."/persist" = {
    hideMounts = true;
    directories = [
      "/var/lib/nixos"
      "/var/lib/smartmontools"
      "/var/lib/systemd"
    ];
    files = [ "/etc/machine-id" ];
  };

  environment.systemPackages = with pkgs; [
    cryptsetup
    curl
    dmidecode
    ethtool
    lm_sensors
    nvme-cli
    pciutils
    smartmontools
    tcpdump
    zfs
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
