{
  disko.devices.disk.system = {
    type = "disk";
    device = "/dev/disk/by-id/ata-FORESEE_64GB_SSD_0000007798__FMA39721";
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
