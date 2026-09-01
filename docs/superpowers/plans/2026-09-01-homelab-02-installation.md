# Homelab 02 Installation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Talos on CLI ar9070 unit 1 with a reproducible NixOS k3s server at `10.0.30.12`.

**Architecture:** Disko targets only the observed FORESEE SSD by stable ATA identifier and creates a UEFI ESP plus unencrypted Btrfs persistence beneath a tmpfs root. Unencrypted storage is intentional because this hardware exposes no TPM and the node must recover unattended after a power loss. The reusable k3s module owns systemd-networkd, SSH, firewall policy, persistence, and a token-gated join service; the host profile owns its exact hardware, disk, interface, and address.

**Tech Stack:** NixOS 26.05/unstable flake, Disko, Btrfs, impermanence, systemd-boot, systemd-networkd, k3s, Cilium bootstrap, nixos-anywhere

---

### Task 1: Define the installation contract

**Files:**
- Create: `tests/test_k3s_node_installation_contract.py`

- [ ] **Step 1: Write the failing contract test**

Create tests that require `homelab-02` to be exported through Disko and impermanence, require the exact observed SSD `/dev/disk/by-id/ata-FORESEE_64GB_SSD_0000007520__FMA39721`, reject `/dev/sdb` and LUKS, require Btrfs mount points for `/nix`, `/persist`, and `/var/log`, require UEFI systemd-boot, and require the observed `ahci`, `r8169`, and AMD CPU hardware modules.

Require the reusable node role to declare `enp1s0`, `10.0.30.12/24`, gateway `10.0.30.1`, DNS `10.0.30.10`, key-only SSH, persistent host identity, persistent k3s state, and a `ConditionPathExists` gate for a joining node's token file.

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
python -m unittest tests.test_k3s_node_installation_contract -v
```

Expected: failure because the installable host files and flake export do not exist.

- [ ] **Step 3: Commit the failing contract**

```bash
git add tests/test_k3s_node_installation_contract.py
git commit -m "test: define k3s node installation contract"
```

### Task 2: Implement the reusable k3s node base

**Files:**
- Modify: `flake/modules/k3s-server.nix`

- [ ] **Step 1: Add host-level inputs**

Add required `primaryInterface` and optional `tokenFile` inputs to the existing role. Configure systemd-boot for UEFI, redistributable firmware, the Chicago timezone, systemd-networkd, and static addressing from `nodeIp`.

- [ ] **Step 2: Add host security and persistence**

Configure nftables, allow SSH only from VLAN 10, allow the k3s, etcd, kubelet, Cilium, and BGP node-plane ports only from VLAN 30, and persist SSH host keys, `/etc/machine-id`, `/var/lib/nixos`, `/var/lib/rancher/k3s`, and `/var/lib/systemd` under `/persist`.

Joining nodes must add `ConditionPathExists` for their token file so a freshly installed host boots cleanly before the runtime secret is provisioned. Cluster-init nodes must not receive that condition.

- [ ] **Step 3: Keep the role operationally small**

Enable SMART monitoring, weekly Nix garbage collection, store optimization, zram, and the existing k3s custom-CNI flags. Do not add workloads, GitOps resources, or cluster secrets.

- [ ] **Step 4: Run the contract and verify remaining failures are host-specific**

Run:

```bash
python -m unittest tests.test_k3s_node_installation_contract -v
```

Expected: role assertions pass while the missing host disk, hardware, and flake export assertions still fail.

### Task 3: Make homelab-02 installable

**Files:**
- Modify: `flake/hosts/homelab-02/default.nix`
- Create: `flake/hosts/homelab-02/disk-config.nix`
- Create: `flake/hosts/homelab-02/hardware-configuration.nix`
- Modify: `flake/flake.nix`

- [ ] **Step 1: Declare exact storage**

Create one GPT disk at `/dev/disk/by-id/ata-FORESEE_64GB_SSD_0000007520__FMA39721`. Create a 1 GiB EF00 ESP mounted at `/boot` with `umask=0077`; format the remainder as Btrfs with subvolumes mounted at `/nix`, `/persist`, and `/var/log`, using `compress=zstd` and `noatime`. Do not configure encryption.

- [ ] **Step 2: Capture observed hardware**

Declare `xhci_pci`, `ahci`, `usbhid`, and `sd_mod` as initrd-available modules, `r8169` and `kvm-amd` as boot modules, the `x86_64-linux` platform, and AMD microcode updates.

- [ ] **Step 3: Complete the host profile**

Import the disk, hardware, k3s role, and impermanence-compatible tmpfs root. Set `primaryInterface = "enp1s0"`, `nodeIp = "10.0.30.12"`, `serverAddress = "https://10.0.30.11:6443"`, and `tokenFile = "/persist/secrets/k3s-token"`. Mark `/persist` as needed for boot and set state version `26.05`.

- [ ] **Step 4: Export the host**

Add `nixosConfigurations.homelab-02` to `flake/flake.nix` with the Disko and impermanence modules plus `./hosts/homelab-02`.

- [ ] **Step 5: Verify GREEN**

Run:

```bash
python -m unittest tests.test_k3s_node_installation_contract -v
nix flake check ./flake
nix build ./flake#nixosConfigurations.homelab-02.config.system.build.toplevel
gitleaks detect --source . --redact --no-banner
```

Expected: all commands succeed.

- [ ] **Step 6: Commit the implementation**

```bash
git add flake/flake.nix flake/modules/k3s-server.nix flake/hosts/homelab-02/default.nix flake/hosts/homelab-02/disk-config.nix flake/hosts/homelab-02/hardware-configuration.nix
git commit -m "feat: add installable k3s node"
```

### Task 4: Install and verify homelab-02

**Files:**
- No repository changes

- [ ] **Step 1: Preflight the destructive target**

Over SSH to `nixos@10.0.30.123`, verify the internal target is exactly `ata-FORESEE_64GB_SSD_0000007520__FMA39721`, the installer is the removable USB, the active NIC is `enp1s0` with MAC `00:50:ac:93:01:b0`, and `/sys/firmware/efi` reports `boot_mode=uefi`.

- [ ] **Step 2: Install with nixos-anywhere**

Run from the repository root:

```bash
nix run github:nix-community/nixos-anywhere -- \
  --flake ./flake#homelab-02 \
  --target-host nixos@10.0.30.123 \
  --build-on local
```

Expected: Disko formats only the exact FORESEE SSD, NixOS installs, and the host reboots.

- [ ] **Step 3: Verify the live installed system**

Verify `homelab-02` answers at `10.0.30.12`, SSH accepts keys and rejects passwords, `/` is tmpfs, `/nix`, `/persist`, and `/var/log` are Btrfs, systemd-boot is active, SMART is healthy, and k3s is inactive only because `/persist/secrets/k3s-token` is intentionally absent.

- [ ] **Step 4: Preserve evidence**

Record the realized NixOS closure, installed disk identifier, live address, boot mode, filesystem layout, SSH posture, SMART result, and token-gated k3s state in the execution report before moving the installer USB to unit 2.
