{
  config,
  lib,
  pkgs,
  ...
}:
{
  # The OPNsense API cert only carries DNS:OPNsense.internal (no IP SANs), so
  # CI jobs on this host must resolve that name to reach the firewall by TLS.
  networking.hosts = {
    "192.168.1.1" = [ "OPNsense.internal" ];
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
      MemoryMax = "12G";
      CPUQuota = "800%";
      CPUWeight = 50;
    };
  };

  services.gitlab-runner = {
    enable = true;
    settings.concurrent = 6;
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
            openssh
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
      limit = 5;
      requestConcurrency = 5;
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
            openssh
          ]
        );
        GIT_SSL_CAINFO = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
        CURL_CA_BUNDLE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
        NIX_SSL_CERT_FILE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
      };
    };
  };

  systemd.tmpfiles.rules = [
    "d /persist/gitlab-runner 0700 root root -"
  ];
}
