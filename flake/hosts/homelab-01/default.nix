{
  imports = [ ../../modules/k3s-server.nix ];

  networking.hostName = "homelab-01";

  homelab.k3s = {
    enable = true;
    nodeIp = "10.0.30.11";
    clusterInit = true;
    bootstrapCilium = true;
  };
}
