# GitHub Actions self-hosted runners for the nixos-config repo CI.
#
# Two ephemeral runners on nas-01 so check.yml's validate/profiles jobs run
# concurrently. Ephemeral means every job starts from a clean work dir and
# re-registers; with `replace` a reboot reuses the same runner names instead
# of orphaning entries in the GitHub UI.
#
# Why a NixOS host instead of the k8s actions-runner pods: CI is Nix
# evaluation and builds. Here the daemon, a warm /nix/store on NVMe, and the
# LAN Attic cache are already present, so jobs start in seconds with no Nix
# installer step. Resource caps keep two concurrent jobs from crowding out
# storage duties on this 6C/12T, 16G box.
#
# Provision once (classic PAT with `repo` scope on JEFF7712/nixos-config, or a
# fine-grained PAT with Administration read/write on that repo; the file must
# hold exactly the token, no trailing newline):
#   install -d -m 0750 -o root -g github-runner-nixos /persist/github-runner-nixos
#   printf '%s' "$TOKEN" > /persist/github-runner-nixos/token
#   chmod 600 /persist/github-runner-nixos/token
{ pkgs, lib, ... }:
let
  user = "github-runner-nixos";
  baseDir = "/persist/github-runner-nixos";
  mkRunner = n: {
    enable = true;
    url = "https://github.com/JEFF7712/nixos-config";
    name = "homelab-nixos-${toString n}";
    tokenFile = "${baseDir}/token";
    extraLabels = [
      "homelab"
      "nixos"
    ];
    ephemeral = true;
    replace = true;
    inherit user;
    group = user;
    # Distinct work dirs: the module cleans workDir on every service start,
    # so the two instances must not share one.
    workDir = "${baseDir}/work-${toString n}";
    # git/nix/bash/coreutils/tar come from the module defaults; these are the
    # CI-specific extras (attic for the ISO push step).
    extraPackages = with pkgs; [
      attic-client
      jq
      just
    ];
    serviceOverrides = {
      MemoryMax = "8G";
      CPUQuota = "300%";
    };
  };
in
{
  users.users.${user} = {
    isSystemUser = true;
    group = user;
    description = "nixos-config CI runner";
  };
  users.groups.${user} = { };

  systemd.tmpfiles.rules = [
    "d ${baseDir} 0750 root ${user} -"
    "d ${baseDir}/work-1 0750 ${user} ${user} -"
    "d ${baseDir}/work-2 0750 ${user} ${user} -"
  ];

  services.github-runners = {
    nixos-ci-1 = mkRunner 1;
    nixos-ci-2 = mkRunner 2;
  };
}
