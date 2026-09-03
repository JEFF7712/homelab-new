{ pkgs, ... }:
{
  networking.firewall.allowedTCPPorts = [
    2049
    8080
  ];

  fileSystems."/mnt/backup-2tb" = {
    device = "/dev/disk/by-id/ata-ST2000DM008-2FR102_ZFL60NJG-part1";
    fsType = "xfs";
    options = [
      "nofail"
      "x-systemd.device-timeout=30s"
    ];
  };

  services.nfs.server = {
    enable = true;
    exports = ''
      /tank/media     10.0.30.0/24(rw,sync,no_subtree_check) 10.0.10.0/24(ro,sync,no_subtree_check)
      /tank/backups   10.0.30.0/24(rw,sync,no_subtree_check)
      /tank/cluster   10.0.30.0/24(rw,sync,no_subtree_check)
    '';
  };

  services.sanoid = {
    enable = true;
    templates.personal = {
      hourly = 48;
      daily = 30;
      monthly = 12;
      autosnap = true;
      autoprune = true;
    };
    templates.operational = {
      daily = 30;
      autosnap = true;
      autoprune = true;
    };
    templates.weekly = {
      daily = 7;
      autosnap = true;
      autoprune = true;
    };
    datasets = {
      "tank/photos".useTemplate = [ "personal" ];
      "tank/documents".useTemplate = [ "personal" ];
      "tank/backups".useTemplate = [ "operational" ];
      "tank/cluster".useTemplate = [ "operational" ];
      "tank/media".useTemplate = [ "weekly" ];
      "tank/attic".useTemplate = [ "weekly" ];
      "tank/gitlab-runner".useTemplate = [ "weekly" ];
    };
  };

  services.atticd = {
    enable = true;
    environmentFile = "/persist/attic/env";
    settings = {
      listen = "[::]:8080";
      storage = {
        type = "local";
        path = "/tank/attic";
      };
    };
  };

  services.gitlab-runner = {
    enable = true;
    services.nas = {
      executor = "shell";
      authenticationTokenConfigFile = "/persist/gitlab-runner/authentication-token";
    };
  };

  systemd.services.nas-backup-2tb = {
    description = "Copy photos and documents to the independent 2 TB disk";
    after = [ "mnt-backup\\x2d2tb.mount" ];
    requires = [ "mnt-backup\\x2d2tb.mount" ];
    serviceConfig = {
      Type = "oneshot";
      ExecStart = pkgs.writeShellScript "nas-backup-2tb" ''
        set -eu
        ${pkgs.rsync}/bin/rsync -a --delete /tank/photos/ /mnt/backup-2tb/photos/
        ${pkgs.rsync}/bin/rsync -a --delete /tank/documents/ /mnt/backup-2tb/documents/
      '';
    };
  };
  systemd.timers.nas-backup-2tb = {
    description = "Daily copy of photos and documents to the 2 TB disk";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnCalendar = "daily";
      Persistent = true;
    };
  };

  systemd.tmpfiles.rules = [
    "d /persist/attic 0700 root root -"
    "d /persist/gitlab-runner 0700 root root -"
    "d /persist/keys 0700 root root -"
    "d /mnt/backup-2tb/photos 0755 root root -"
    "d /mnt/backup-2tb/documents 0755 root root -"
  ];

  environment.persistence."/persist".directories = [
    "/var/lib/nfs"
    "/var/lib/gitlab-runner"
  ];

  environment.systemPackages = with pkgs; [ rsync ];
}
