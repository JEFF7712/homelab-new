# NAS Data Services Provisioning Plan

**Goal:** Bring `tank` and NAS services (NFS, snapshots, Attic, GitLab runner, 2 TB backup copy) online on `nas-01` after the base installation lands.

**Declared in this workstream (already evaluated, not yet wired):**

- `flake/hosts/nas-01/tank-config.nix`: single-disk `tank` on the observed Exos (`scsi-35000c500d91a3f4f`, `ashift=12`), datasets `media`, `photos`, `documents`, `backups`, `cluster`, `attic`, `gitlab-runner`. `photos` and `documents` use native encryption with install-time key files. The protected 2 TB disk and both system NVMes do not appear.
- `flake/modules/nas-data.nix`: NFS exports (`media`/`backups`/`cluster` to k3s nodes, `media` read-only to management), sanoid policy per the rebuild design spec, Attic on `/tank/attic:8080`, shell-executor GitLab runner, daily `photos`+`documents` copy to the 2 TB disk.
- `tests/test_nas_data_contract.py`: 5 contract tests, all passing.

**Gates (in order, all live):**

1. Exos burn-in passed: `err= 0` in `/tmp/nas-exos-burnin.log`, SMART health OK, zero grown defects, zero uncorrected errors.
2. Base `nas-01` installed and booted at `10.0.30.20` per `2026-09-01-nas-base-installation.md` Task 5.
3. Confirm the 2 TB partition identity before first boot with services: `ls /dev/disk/by-id/*ZFL60NJG*` must show the `-part1` link used by `nas-data.nix`. If the suffix differs, update the `fileSystems."/mnt/backup-2tb"` device first.

**Provisioning steps:**

1. Generate dataset keys locally (never commit):
   `openssl rand -base64 48 > /tmp/nas-01-tank-photos.key` and likewise for `documents`, mode `0600`, copy to the installer environment.
2. Wire the workstream into the host by adding `./tank-config.nix` and `../../modules/nas-data.nix` to `flake/hosts/nas-01/default.nix` imports, then `nixos-rebuild switch --flake ./flake#nas-01 --target-host rupan@10.0.30.20`.
3. Format `tank` once via disko from the installer context; afterwards the pool is managed by the host config. Mirror a second 10 TB disk later with `zpool attach tank <new-disk>`; until then `tank` is explicitly non-redundant.
4. Provision secrets on the host (mode `0600` under `/persist`): Attic `environmentFile` with signing key, GitLab runner `authentication-token` from the GitLab project runner page.
5. Verify: `zpool status tank`, `zfs list`, NFS mount from a k3s node, `sanoid --monitor-health`, Attic push/pull round-trip, one pipeline job on the NAS runner, manual `systemctl start nas-backup-2tb` plus a restore spot-check from `/mnt/backup-2tb`.
6. Acceptance per the rebuild design spec: sample NFS PVC, etcd snapshot landing in `/tank/cluster`, and a NAS dataset restore all proven before old infrastructure is removed.
