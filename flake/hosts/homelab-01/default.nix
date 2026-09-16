{
  imports = [
    ./disk-config.nix
    ./hardware-configuration.nix
    ../../modules/common-base.nix
    ../../modules/k3s-server.nix
    ../../modules/agent-workspaces.nix
    ../../modules/agent-workspace-network.nix
  ];

  networking.hostName = "homelab-01";

  homelab.k3s = {
    enable = true;
    primaryInterface = "eno1";
    nodeIp = "10.0.30.11";
    clusterInit = true;
    bootstrapCilium = true;
  };

  services.k3s.extraFlags = [
    "--kubelet-arg=system-reserved=cpu=2,memory=10Gi"
  ];

  services.agent-workspaces.enable = true;
  services.agent-workspace-network.enable = true;
}
