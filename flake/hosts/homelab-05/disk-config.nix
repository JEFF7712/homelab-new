{
  disko.devices.disk.system = {
    type = "disk";
    device = "/dev/disk/by-id/nvme-KXG70ZNV1T02_NVMe_KIOXIA_1024GB_42MFC3FQFTC5";
    content = {
      type = "gpt";
      partitions = {
        ESP = {
          size = "1G";
          type = "EF00";
          content = {
            type = "filesystem";
            format = "vfat";
            mountpoint = "/boot";
            mountOptions = [ "umask=0077" ];
          };
        };
        system = {
          size = "100%";
          content = {
            type = "btrfs";
            extraArgs = [
              "-f"
              "-L"
              "nixos"
            ];
            subvolumes = {
              "/nix" = {
                mountpoint = "/nix";
                mountOptions = [
                  "compress=zstd"
                  "noatime"
                ];
              };
              "/persist" = {
                mountpoint = "/persist";
                mountOptions = [
                  "compress=zstd"
                  "noatime"
                ];
              };
              "/log" = {
                mountpoint = "/var/log";
                mountOptions = [
                  "compress=zstd"
                  "noatime"
                ];
              };
            };
          };
        };
      };
    };
  };
}
