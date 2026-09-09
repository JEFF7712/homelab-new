{ pkgs, lib, ... }:
{
  networking.firewall.allowedTCPPorts = [
    2049
    8080
  ];

  # The OPNsense API cert only carries DNS:OPNsense.internal (no IP SANs), so
  # CI jobs on this host must resolve that name to reach the firewall by TLS.
  networking.hosts = {
    "192.168.1.1" = [ "OPNsense.internal" ];
  };

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
      /tank/cluster   10.0.30.0/24(rw,sync,no_subtree_check,no_root_squash)
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
      "tank/registry".useTemplate = [ "operational" ];
    };
  };

  users.users.atticd = {
    isSystemUser = true;
    group = "atticd";
  };
  users.groups.atticd = { };

  systemd.services.atticd = {
    after = [ "network-online.target" ];
    wants = [ "network-online.target" ];
    serviceConfig = {
      DynamicUser = lib.mkForce false;
      User = "atticd";
      Group = "atticd";
      ReadWritePaths = [ "/persist/attic" ];
      ExecStartPre = [
        "+${pkgs.writeShellScript "ensure-attic-storage-permissions" ''
          set -eu
          ${pkgs.coreutils}/bin/install -d -m 0750 -o atticd -g atticd /tank/attic
          ${pkgs.coreutils}/bin/chown -R atticd:atticd /tank/attic
          ${pkgs.coreutils}/bin/install -d -m 0700 -o atticd -g atticd /persist/attic
          if [ -f /persist/attic/server.db ]; then
            ${pkgs.coreutils}/bin/chown atticd:atticd /persist/attic/server.db
            ${pkgs.coreutils}/bin/chmod 0600 /persist/attic/server.db
          fi
        ''}"
      ];
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
      database = {
        url = "sqlite:///persist/attic/server.db?mode=rwc";
      };
    };
  };

  # The runner executes downloaded binaries (tofu providers) from its builds
  # dir, so DynamicUser is a poor fit: its state mount is noexec and its
  # recycled UID leaves job files owned by an unresolvable nobody alias.
  # A static service user keeps ownership stable across restarts.
  users.users.gitlab-runner = {
    isSystemUser = true;
    group = "gitlab-runner";
  };
  users.groups.gitlab-runner = { };

  systemd.services.gitlab-runner = {
    after = [ "network-online.target" ];
    wants = [ "network-online.target" ];
    serviceConfig = {
      DynamicUser = lib.mkForce false;
      User = "gitlab-runner";
      Group = "gitlab-runner";
      Restart = "on-failure";
      RestartSec = "30s";
    };
  };

  services.gitlab-runner = {
    enable = true;
    settings.concurrent = 2;
    services.nas = {
      executor = "shell";
      authenticationTokenConfigFile = "/persist/gitlab-runner/authentication-token";
      limit = 1;
      requestConcurrency = 1;
      # Builds must live outside the DynamicUser state dir: systemd mounts it
      # noexec, which breaks any tool that executes downloaded binaries there
      # (e.g. tofu provider plugins). /tmp is exec-capable and writable.
      # NOTE: applied at registration time; re-register the runner after changing this.
      buildsDir = "/tmp/gitlab-runner-builds";
      # Shell jobs do not inherit the daemon PATH, so pin the tools CI jobs need
      # (checkout via git, then `nix develop`) into the build environment.
      # NOTE: applied at registration time; re-register the runner after changing this.
      environmentVariables = {
        PATH = lib.makeBinPath (
          with pkgs;
          [
            attic-client
            bash
            coreutils
            findutils
            gawk
            git
            gnugrep
            gnused
            gnutar
            gzip
            inetutils
            iproute2
            iputils
            jq
            nix
          ]
        );
        GIT_SSL_CAINFO = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
        CURL_CA_BUNDLE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
        NIX_SSL_CERT_FILE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
      };
    };
    services.nas-ci = {
      executor = "shell";
      authenticationTokenConfigFile = "/persist/gitlab-runner/ci-authentication-token";
      buildsDir = "/tmp/gitlab-runner-ci-builds";
      limit = 1;
      requestConcurrency = 1;
      environmentVariables = {
        PATH = lib.makeBinPath (
          with pkgs;
          [
            attic-client
            bash
            coreutils
            findutils
            gawk
            git
            gnugrep
            gnused
            gnutar
            gzip
            inetutils
            iproute2
            iputils
            jq
            nix
          ]
        );
        GIT_SSL_CAINFO = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
        CURL_CA_BUNDLE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
        NIX_SSL_CERT_FILE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
      };
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

  systemd.services.registry-backup = {
    description = "Encrypted backup of the local container registry";
    after = [
      "tank-registry.mount"
      "mnt-backup\\x2d2tb.mount"
    ];
    requires = [
      "tank-registry.mount"
      "mnt-backup\\x2d2tb.mount"
    ];
    unitConfig.ConditionPathExists = "/persist/zot/restic-password";
    serviceConfig = {
      Type = "oneshot";
      User = "root";
      Group = "root";
      PrivateTmp = true;
      ProtectSystem = "strict";
      ReadWritePaths = [
        "/mnt/backup-2tb/registry-restic"
        "/persist/zot/status"
      ];
    };
    path = [ pkgs.restic ];
    script = ''
      export RESTIC_REPOSITORY=/mnt/backup-2tb/registry-restic
      export RESTIC_PASSWORD_FILE=/persist/zot/restic-password
      if [ ! -f "$RESTIC_REPOSITORY/config" ]; then
        restic init
      fi
      restic snapshots >/dev/null
      restic backup --exclude=/persist/zot/restic-password /tank/registry /persist/zot /var/lib/acme
      restic check --read-data-subset=1/20
      date +%s > /persist/zot/status/backup-last-success.tmp
      sync -f /persist/zot/status/backup-last-success.tmp
      mv /persist/zot/status/backup-last-success.tmp /persist/zot/status/backup-last-success
      sync -f /persist/zot/status
    '';
  };
  systemd.timers.registry-backup = {
    description = "Daily encrypted registry backup";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnCalendar = "daily";
      Persistent = true;
      RandomizedDelaySec = "30m";
    };
  };

  systemd.tmpfiles.rules = [
    "d /persist/attic 0700 root root -"
    "d /persist/gitlab-runner 0700 root root -"
    "d /persist/keys 0700 root root -"
    "d /mnt/backup-2tb/registry-restic 0700 zot zot -"
    "d /mnt/backup-2tb/photos 0755 root root -"
    "d /mnt/backup-2tb/documents 0755 root root -"
  ];

  environment.persistence."/persist".directories = [
    "/var/lib/nfs"
  ];

  environment.systemPackages = with pkgs; [
    restic
    rsync
  ];
}
