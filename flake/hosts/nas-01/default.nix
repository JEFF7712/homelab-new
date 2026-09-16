{
  imports = [
    ./disk-config.nix
    ./hardware-configuration.nix
    ./tank-config.nix
    ../../modules/common-base.nix
    ../../modules/nas-base.nix
    ../../modules/nas-data.nix
    ../../modules/zot-registry.nix
  ];

  networking.hostName = "nas-01";

  services.homelab-zot-registry = {
    enable = true;
    acmeEmail = "rupanpandyan@gmail.com";
  };

  fileSystems."/var/log".neededForBoot = true;
}
