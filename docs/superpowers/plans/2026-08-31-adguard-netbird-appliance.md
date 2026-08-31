# AdGuard and NetBird Appliance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reproducibly install the Dell Wyse 5070 Standard as the encrypted, impermanent `adguard-netbird-01` NixOS appliance.

**Architecture:** Disko formats only the observed internal `/dev/sda` as GPT, EFI, and LUKS2-backed Btrfs. A tmpfs root plus persistent Btrfs subvolumes implements impermanence. systemd-networkd gives the appliance static VLAN 30 and tagged VLAN 60 addresses, AdGuard Home is declarative, NetBird is routing-ready, and SSH is key-only. `nixos-anywhere` installs without rebooting, then the verified TPM 2.0 device is enrolled before the first boot.

**Tech Stack:** NixOS 26.05/unstable flake, Disko, impermanence, systemd-networkd, AdGuard Home, NetBird, LUKS2, systemd-cryptenroll, TPM 2.0, nixos-anywhere

---

### Task 1: Add the appliance contract

**Files:**
- Create: `tests/test_appliance_contract.py`

- [ ] **Step 1: Write failing repository tests**

Assert that `flake/flake.nix` exports `adguard-netbird-01`, imports Disko and impermanence, and that the host files declare `/dev/sda`, LUKS2, tmpfs root, persistent service state, `10.0.30.10`, VLAN 60 address `10.0.60.2`, key-only SSH, AdGuard Home, and NetBird routing-server mode.

- [ ] **Step 2: Verify RED**

Run: `nix develop ./flake -c python -m unittest tests.test_appliance_contract -v`

Expected: failures because the appliance files and flake output do not exist.

- [ ] **Step 3: Commit the failing contract**

Run: `git add tests/test_appliance_contract.py && git commit -m "test: define appliance installation contract"`

### Task 2: Add the installable NixOS target

**Files:**
- Modify: `flake/flake.nix`
- Modify: `flake/flake.lock`
- Create: `flake/hosts/adguard-netbird-01/default.nix`
- Create: `flake/hosts/adguard-netbird-01/disk-config.nix`
- Create: `flake/hosts/adguard-netbird-01/hardware-configuration.nix`

- [ ] **Step 1: Add pinned module inputs and host output**

Add Disko and impermanence inputs following `nixpkgs`, and export `nixosConfigurations.adguard-netbird-01` with both modules plus the host definition.

- [ ] **Step 2: Declare the observed hardware**

Declare UEFI/systemd-boot, Intel microcode, `ahci`, `xhci_pci`, `sd_mod`, `sdhci_pci`, `r8169`, and x86_64-linux from the live installer evidence.

- [ ] **Step 3: Declare storage**

Partition `/dev/sda` into a 1 GiB ESP and the remaining LUKS2 partition. Use `/tmp/adguard-netbird-01-luks.key` only as Disko's formatting password, configure `tpm2-device=auto` for runtime unlock, create Btrfs subvolumes for `/nix`, `/persist`, and `/var/log`, and use a 2 GiB tmpfs root.

- [ ] **Step 4: Verify GREEN**

Run: `nix develop ./flake -c python -m unittest tests.test_appliance_contract -v`

Expected: all appliance contract tests pass.

- [ ] **Step 5: Commit the install target**

Run: `git add flake tests/test_appliance_contract.py && git commit -m "feat: add encrypted Wyse appliance target"`

### Task 3: Add appliance networking and services

**Files:**
- Create: `flake/modules/adguard-netbird-appliance.nix`
- Modify: `flake/hosts/adguard-netbird-01/default.nix`
- Modify: `tests/test_appliance_contract.py`

- [ ] **Step 1: Extend the failing contract**

Require systemd-networkd static addresses `10.0.30.10/24` and `10.0.60.2/24`, default gateway `10.0.30.1`, AdGuard DNS on `10.0.30.10:53`, authenticated UI on port 3000, Quad9 DNS-over-HTTPS upstream, NetBird routing-server mode, and persisted SSH, AdGuard, NetBird, machine-id, and systemd state.

- [ ] **Step 2: Verify RED**

Run: `nix develop ./flake -c python -m unittest tests.test_appliance_contract -v`

Expected: failures for the absent role module.

- [ ] **Step 3: Implement the role**

Use the committed bcrypt hash for user `admin`, never the plaintext password. Add both published `JEFF7712` SSH keys for user `rupan`, disable root/password authentication, enable passwordless wheel sudo for automation, enable the firewall, AdGuard Home immutable settings, NetBird's hardened default client with `useRoutingFeatures = "server"`, and impermanence persistence declarations.

- [ ] **Step 4: Verify GREEN and evaluate**

Run: `nix develop ./flake -c python -m unittest discover -s tests -v`

Run: `nix build ./flake#nixosConfigurations.adguard-netbird-01.config.system.build.toplevel --no-link`

Expected: all tests pass and the host closure builds.

- [ ] **Step 5: Commit the appliance role**

Run: `git add flake tests/test_appliance_contract.py && git commit -m "feat: configure AdGuard and NetBird appliance"`

### Task 4: Install, enroll TPM, and prove the first boot

**Files:**
- Modify: `docs/network/switch-port-map.md`

- [ ] **Step 1: Run repository verification**

Run Pyright, unit tests, `nix flake check ./flake --print-build-logs`, `nixfmt --check flake`, yamllint, gitleaks, and `git diff --check`.

- [ ] **Step 2: Install without rebooting**

Run nixos-anywhere against `nixos@10.0.30.103`, build locally, pass `/home/rupan/.local/share/homelab/secrets/adguard-netbird-01-luks-recovery.key` to remote `/tmp/adguard-netbird-01-luks.key`, and stop after `kexec,disko,install` phases.

Expected: `/dev/sda` is repartitioned and the NixOS system is installed while the USB installer remains untouched.

- [ ] **Step 3: Enroll TPM and remove the transient key**

Use `systemd-cryptenroll --unlock-key-file=/tmp/adguard-netbird-01-luks.key --tpm2-device=auto` on the LUKS partition, verify a TPM2 token with `cryptsetup luksDump`, securely remove the transient remote key, and reboot.

- [ ] **Step 4: Verify live acceptance**

Verify SSH as `rupan`, hostname, static addresses, tmpfs root, encrypted Btrfs mounts, TPM token, AdGuard service and DNS answer, NetBird daemon state, default route, Internet reachability, and that no password SSH authentication is accepted.

- [ ] **Step 5: Record and commit live topology**

Update the switch port map with the appliance hostname and static addresses, then run the full repository checks and commit as `docs: record appliance deployment`.
