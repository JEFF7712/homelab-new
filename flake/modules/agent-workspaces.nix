{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.agent-workspaces;
in
{
  options.services.agent-workspaces = {
    enable = lib.mkEnableOption "host support for isolated personal agent workspace VMs";
    storageRoot = lib.mkOption {
      type = lib.types.path;
      default = "/persist/agent-workspaces";
      description = "Host-owned persistent storage root for workspace VM disks.";
    };
    aggregateCpuPercent = lib.mkOption {
      type = lib.types.ints.positive;
      default = 200;
      description = "Hard CPU quota for all agent workspace domains combined.";
    };
    aggregateMemoryMaxMiB = lib.mkOption {
      type = lib.types.ints.positive;
      default = 10240;
      description = "Hard memory limit for all agent workspace domains including QEMU overhead.";
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = lib.hasPrefix "/persist/" (toString cfg.storageRoot);
        message = "services.agent-workspaces.storageRoot must be under /persist";
      }
      {
        assertion = cfg.aggregateMemoryMaxMiB > 1024;
        message = "services.agent-workspaces.aggregateMemoryMaxMiB must leave room for a memory pressure threshold";
      }
    ];

    virtualisation.libvirtd = {
      enable = true;
      onBoot = "ignore";
      onShutdown = "shutdown";
      qemu = {
        runAsRoot = false;
        swtpm.enable = false;
      };
    };
    virtualisation.spiceUSBRedirection.enable = false;
    systemd.oomd.enable = true;
    systemd.slices."machine-agent\\x2dworkspaces".sliceConfig = {
      CPUAccounting = true;
      CPUQuota = "${toString cfg.aggregateCpuPercent}%";
      MemoryAccounting = true;
      MemoryHigh = "${toString (cfg.aggregateMemoryMaxMiB - 1024)}M";
      MemoryMax = "${toString cfg.aggregateMemoryMaxMiB}M";
      ManagedOOMMemoryPressure = "kill";
      ManagedOOMMemoryPressureLimit = "70%";
    };
    users.groups.agent-workspace-storage = { };
    users.users.qemu-libvirtd.extraGroups = [ "agent-workspace-storage" ];
    environment.systemPackages = [
      pkgs.cloud-utils
      pkgs.qemu_kvm
    ];
    systemd.tmpfiles.rules = [
      "d ${cfg.storageRoot} 0710 root agent-workspace-storage - -"
    ];
  };
}
