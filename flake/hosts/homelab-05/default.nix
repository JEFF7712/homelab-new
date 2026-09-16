{
  imports = [
    ./disk-config.nix
    ./hardware-configuration.nix
    ../../modules/common-base.nix
    ../../modules/k3s-server.nix
    ../../modules/nvidia.nix
    ../../modules/kiosk.nix
  ];

  networking.hostName = "homelab-05";

  homelab.k3s = {
    enable = true;
    role = "agent";
    primaryInterface = "enp0s31f6";
    nodeIp = "10.0.30.15";
    serverAddress = "https://10.0.30.11:6443";
    tokenFile = "/persist/secrets/k3s-token";
  };

  homelab.kiosk = {
    enable = true;
    url = "http://10.0.40.12/d/e1RXnCbVz/kubernetes-dashboard?kiosk&refresh=30s&theme=dark";
    drmDevice = "/dev/dri/card1";
  };
}
