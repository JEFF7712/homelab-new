{
  imports = [
    ./disk-config.nix
    ./hardware-configuration.nix
    ../../modules/k3s-server.nix
  ];

  networking.hostName = "homelab-03";

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
    primaryInterface = "enp1s0";
    nodeIp = "10.0.30.13";
    serverAddress = "https://10.0.30.11:6443";
    tokenFile = "/persist/secrets/k3s-token";
  };

  system.stateVersion = "26.05";
}
