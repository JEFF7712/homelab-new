{
  imports = [ ../../modules/k3s-server.nix ];

  networking.hostName = "homelab-03";

  homelab.k3s = {
    enable = true;
    nodeIp = "10.0.30.13";
    serverAddress = "https://10.0.30.11:6443";
    tokenFile = "/persist/secrets/k3s-token";
  };
}
