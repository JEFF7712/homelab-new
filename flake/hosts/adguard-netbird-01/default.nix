{
  imports = [
    ./disk-config.nix
    ./hardware-configuration.nix
    ../../modules/adguard-netbird-appliance.nix
  ];

  networking.hostName = "adguard-netbird-01";

  fileSystems."/" = {
    device = "none";
    fsType = "tmpfs";
    options = [
      "defaults"
      "mode=755"
      "size=2G"
    ];
  };
  fileSystems."/persist".neededForBoot = true;

  system.stateVersion = "26.05";
}
