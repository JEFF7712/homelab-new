{ config, lib, ... }:
let
  cfg = config.homelab.k3s;
in
{
  options.homelab.k3s = {
    enable = lib.mkEnableOption "the homelab k3s server role";

    nodeIp = lib.mkOption {
      type = lib.types.str;
      description = "Stable VLAN 30 address used by this k3s server.";
    };

    clusterInit = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Initialize the embedded-etcd k3s cluster on this server.";
    };

    serverAddress = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      description = "Existing k3s API endpoint for joining this server.";
    };

    tokenFile = lib.mkOption {
      type = lib.types.nullOr lib.types.path;
      default = null;
      description = "Runtime-provisioned file containing the k3s cluster token.";
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = cfg.clusterInit || (cfg.serverAddress != null && cfg.tokenFile != null);
        message = "Joining k3s servers require serverAddress and tokenFile.";
      }
      {
        assertion = !(cfg.clusterInit && cfg.serverAddress != null);
        message = "The k3s cluster-init server must not join another server.";
      }
    ];

    services.k3s = {
      enable = true;
      role = "server";
      inherit (cfg) clusterInit tokenFile;
      serverAddr = lib.mkIf (cfg.serverAddress != null) cfg.serverAddress;
      extraFlags = [
        "--node-ip=${cfg.nodeIp}"
        "--advertise-address=${cfg.nodeIp}"
        "--flannel-backend=none"
        "--disable-network-policy"
      ];
    };
  };
}
