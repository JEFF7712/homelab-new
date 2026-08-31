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

    bootstrapCilium = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Bootstrap the pinned Cilium CNI through the k3s Helm controller.";
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
      {
        assertion = !cfg.bootstrapCilium || cfg.clusterInit;
        message = "Cilium bootstrap must run only on the cluster-init server.";
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

    services.k3s.manifests.cilium.content = lib.mkIf cfg.bootstrapCilium {
      apiVersion = "helm.cattle.io/v1";
      kind = "HelmChart";
      metadata = {
        name = "cilium";
        namespace = "kube-system";
      };
      spec = {
        bootstrap = true;
        chart = "cilium";
        createNamespace = false;
        repo = "https://helm.cilium.io";
        targetNamespace = "kube-system";
        version = "1.20.1";
        valuesContent = builtins.toJSON {
          bgpControlPlane.enabled = true;
          k8sServiceHost = "127.0.0.1";
          k8sServicePort = 6443;
          kubeProxyReplacement = true;
        };
      };
    };
  };
}
