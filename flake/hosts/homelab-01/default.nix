{
  imports = [
    ./disk-config.nix
    ./hardware-configuration.nix
    ../../modules/k3s-server.nix
  ];

  networking.hostName = "homelab-01";

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

  homelab.k3s = {
    enable = true;
    primaryInterface = "eno1";
    nodeIp = "10.0.30.11";
    clusterInit = true;
    bootstrapCilium = true;
  };

  system.stateVersion = "26.05";
}
