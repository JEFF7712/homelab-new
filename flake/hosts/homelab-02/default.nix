{
  imports = [
    ./disk-config.nix
    ./hardware-configuration.nix
    ../../modules/common-base.nix
    ../../modules/k3s-server.nix
  ];

  networking.hostName = "homelab-02";

  homelab.k3s = {
    enable = true;
    primaryInterface = "enp1s0";
    nodeIp = "10.0.30.12";
    serverAddress = "https://10.0.30.11:6443";
    tokenFile = "/persist/secrets/k3s-token";
  };
}
