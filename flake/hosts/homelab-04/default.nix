{
  imports = [
    ./disk-config.nix
    ./hardware-configuration.nix
    ../../modules/k3s-server.nix
    ../../modules/nvidia.nix
    ../../modules/github-runner-nixos.nix
    ../../modules/gitlab-runner.nix
  ];

  networking.hostName = "homelab-04";

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
    role = "agent";
    primaryInterface = "enp0s31f6";
    nodeIp = "10.0.30.14";
    serverAddress = "https://10.0.30.11:6443";
    tokenFile = "/persist/secrets/k3s-token";
  };

  system.stateVersion = "26.05";
}
