{
  imports = [ ../../modules/k3s-server.nix ];

  networking.hostName = "homelab-02";

  homelab.k3s = {
    enable = true;
    nodeIp = "10.0.30.12";
    serverAddress = "https://10.0.30.11:6443";
    tokenFile = "/run/secrets/k3s-token";
  };
}
