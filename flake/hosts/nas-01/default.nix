{
  imports = [
    ./disk-config.nix
    ./hardware-configuration.nix
    ../../modules/nas-base.nix
  ];

  networking.hostName = "nas-01";

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
