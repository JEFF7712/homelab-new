{
  imports = [
    ./disk-config.nix
    ./hardware-configuration.nix
    ./tank-config.nix
    ../../modules/github-runner-nixos.nix
    ../../modules/nas-base.nix
    ../../modules/nas-data.nix
    ../../modules/zot-registry.nix
  ];

  networking.hostName = "nas-01";

  services.homelab-zot-registry = {
    enable = true;
    acmeEmail = "rupanpandyan@gmail.com";
  };

  fileSystems."/" = {
    device = "none";
    fsType = "tmpfs";
    options = [
      "defaults"
      "mode=755"
      "size=4G"
    ];
  };
  fileSystems."/persist".neededForBoot = true;
  fileSystems."/var/log".neededForBoot = true;

  system.stateVersion = "26.05";
}
