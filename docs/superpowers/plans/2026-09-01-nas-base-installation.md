# NAS Base Installation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reproducibly install the Jonsbo N2 as `nas-01` on a TPM-unlocked encrypted mirrored NVMe ZFS system pool without touching the existing 2 TB XFS disk or the 10 TB Exos data disk.

**Architecture:** Disko formats only the two observed WD SN520 NVMes, gives each an EFI system partition and a LUKS2 container, and builds a mirrored `zroot` from the decrypted devices. A tmpfs root plus ZFS datasets for `/nix`, `/persist`, and `/var/log` provides impermanence. GRUB is installed to both EFI partitions, systemd-networkd gives the NAS static address `10.0.30.20`, and SSH, SMART, ZFS scrub, and ZFS trim form the base operating contract. Data-pool creation and NAS services remain a separate workstream after the Exos burn-in passes.

**Tech Stack:** NixOS 26.05/unstable flake, Disko, ZFS, LUKS2, impermanence, GRUB UEFI mirrored boots, systemd-networkd, TPM 2.0, nixos-anywhere

---

### Task 1: Define the NAS base contract

**Files:**
- Create: `tests/test_nas_contract.py`

- [ ] **Step 1: Write the failing contract test**

```python
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class NasContractTests(unittest.TestCase):
    def test_flake_exports_installable_nas(self) -> None:
        flake = (ROOT / "flake/flake.nix").read_text()

        self.assertIn("nixosConfigurations.nas-01", flake)
        self.assertIn("./hosts/nas-01", flake)
        self.assertIn("disko.nixosModules.disko", flake)
        self.assertIn("impermanence.nixosModules.impermanence", flake)

    def test_system_pool_uses_exact_encrypted_mirrored_nvmes(self) -> None:
        disk = (ROOT / "flake/hosts/nas-01/disk-config.nix").read_text()

        for value in (
            "/dev/disk/by-id/nvme-WDC_PC_SN520_SDAPNUW-256G-1006_2022C1800396",
            "/dev/disk/by-id/nvme-WDC_PC_SN520_SDAPNUW-256G-1006_2022BA804857",
            'name = "nas-system-a"',
            'name = "nas-system-b"',
            'passwordFile = "/tmp/nas-01-system.key"',
            'pool = "zroot"',
            'mode = "mirror"',
            'mountpoint = "/boot"',
            'mountpoint = "/boot-fallback"',
            'mountpoint = "/nix"',
            'mountpoint = "/persist"',
            'mountpoint = "/var/log"',
        ):
            with self.subTest(value=value):
                self.assertIn(value, disk)

        self.assertNotIn("ST2000DM008", disk)
        self.assertNotIn("ST10000NM002G", disk)
        self.assertNotIn("/dev/sdb", disk)
        self.assertNotIn("/dev/sdc", disk)

    def test_host_declares_observed_hardware_and_static_network(self) -> None:
        hardware = (ROOT / "flake/hosts/nas-01/hardware-configuration.nix").read_text()
        role = (ROOT / "flake/modules/nas-base.nix").read_text()

        for module in ("mpt3sas", "nvme", "r8169", "kvm-amd"):
            with self.subTest(module=module):
                self.assertIn(module, hardware)

        for value in (
            'Address = "10.0.30.20/24"',
            'DNS = "10.0.30.10"',
            'Gateway = "10.0.30.1"',
            'matchConfig.Name = "enp5s0"',
            'networking.hostId = "31eabe12"',
            "services.smartd",
            "services.zfs.autoScrub",
            "services.zfs.trim",
            'path = "/boot"',
            'path = "/boot-fallback"',
        ):
            with self.subTest(value=value):
                self.assertIn(value, role)

    def test_host_uses_ephemeral_root_and_persists_identity(self) -> None:
        host = (ROOT / "flake/hosts/nas-01/default.nix").read_text()
        role = (ROOT / "flake/modules/nas-base.nix").read_text()

        self.assertIn('fsType = "tmpfs"', host)
        self.assertIn('fileSystems."/persist".neededForBoot = true', host)
        self.assertIn('environment.persistence."/persist"', role)
        self.assertIn('files = [ "/etc/machine-id" ]', role)
        self.assertIn("PasswordAuthentication = false", role)
        self.assertIn('PermitRootLogin = "no"', role)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `nix develop ./flake -c python -m unittest tests.test_nas_contract -v`

Expected: FAIL because `flake/hosts/nas-01` and `flake/modules/nas-base.nix` do not exist and the flake does not export `nas-01`.

- [ ] **Step 3: Commit the failing contract**

```bash
git add tests/test_nas_contract.py
git commit -m "test: define NAS base contract"
```

### Task 2: Add the exact hardware and disk layout

**Files:**
- Create: `flake/hosts/nas-01/hardware-configuration.nix`
- Create: `flake/hosts/nas-01/disk-config.nix`

- [ ] **Step 1: Add the observed hardware configuration**

```nix
{
  config,
  lib,
  modulesPath,
  ...
}:
{
  imports = [ (modulesPath + "/installer/scan/not-detected.nix") ];

  boot.initrd.availableKernelModules = [
    "mpt3sas"
    "xhci_pci"
    "ahci"
    "nvme"
    "usbhid"
    "usb_storage"
    "sd_mod"
    "r8169"
  ];
  boot.kernelModules = [ "kvm-amd" ];

  nixpkgs.hostPlatform = lib.mkDefault "x86_64-linux";
  hardware.cpu.amd.updateMicrocode = lib.mkDefault config.hardware.enableRedistributableFirmware;
}
```

- [ ] **Step 2: Add the mirrored encrypted system-disk declaration**

```nix
{
  disko.devices = {
    disk = {
      system-a = {
        type = "disk";
        device = "/dev/disk/by-id/nvme-WDC_PC_SN520_SDAPNUW-256G-1006_2022C1800396";
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
            luks = {
              size = "100%";
              content = {
                type = "luks";
                name = "nas-system-a";
                passwordFile = "/tmp/nas-01-system.key";
                settings = {
                  allowDiscards = true;
                  crypttabExtraOpts = [ "tpm2-device=auto" ];
                };
                content = {
                  type = "zfs";
                  pool = "zroot";
                };
              };
            };
          };
        };
      };
      system-b = {
        type = "disk";
        device = "/dev/disk/by-id/nvme-WDC_PC_SN520_SDAPNUW-256G-1006_2022BA804857";
        content = {
          type = "gpt";
          partitions = {
            ESP = {
              size = "1G";
              type = "EF00";
              content = {
                type = "filesystem";
                format = "vfat";
                mountpoint = "/boot-fallback";
                mountOptions = [ "umask=0077" ];
              };
            };
            luks = {
              size = "100%";
              content = {
                type = "luks";
                name = "nas-system-b";
                passwordFile = "/tmp/nas-01-system.key";
                settings = {
                  allowDiscards = true;
                  crypttabExtraOpts = [ "tpm2-device=auto" ];
                };
                content = {
                  type = "zfs";
                  pool = "zroot";
                };
              };
            };
          };
        };
      };
    };
    zpool.zroot = {
      type = "zpool";
      mode = "mirror";
      options = {
        ashift = "12";
        autotrim = "on";
      };
      rootFsOptions = {
        acltype = "posixacl";
        atime = "off";
        compression = "zstd";
        mountpoint = "none";
        xattr = "sa";
      };
      datasets = {
        nix = {
          type = "zfs_fs";
          mountpoint = "/nix";
          options.mountpoint = "legacy";
        };
        persist = {
          type = "zfs_fs";
          mountpoint = "/persist";
          options.mountpoint = "legacy";
        };
        log = {
          type = "zfs_fs";
          mountpoint = "/var/log";
          options.mountpoint = "legacy";
        };
      };
    };
  };
}
```

- [ ] **Step 3: Run the NAS contract**

Run: `nix develop ./flake -c python -m unittest tests.test_nas_contract -v`

Expected: the disk assertions pass; remaining assertions fail because the host and role are not implemented.

- [ ] **Step 4: Commit the hardware and disk declaration**

```bash
git add flake/hosts/nas-01/hardware-configuration.nix flake/hosts/nas-01/disk-config.nix
git commit -m "feat: declare NAS system storage"
```

### Task 3: Add the hardened NAS base role

**Files:**
- Create: `flake/modules/nas-base.nix`
- Create: `flake/hosts/nas-01/default.nix`

- [ ] **Step 1: Add the NAS base module**

```nix
{ pkgs, ... }:
{
  boot = {
    initrd.systemd.enable = true;
    loader = {
      efi.canTouchEfiVariables = true;
      grub = {
        enable = true;
        efiSupport = true;
        mirroredBoots = [
          {
            path = "/boot";
            devices = [ "/dev/disk/by-id/nvme-WDC_PC_SN520_SDAPNUW-256G-1006_2022C1800396" ];
            efiBootloaderId = "NixOS-a";
          }
          {
            path = "/boot-fallback";
            devices = [ "/dev/disk/by-id/nvme-WDC_PC_SN520_SDAPNUW-256G-1006_2022BA804857" ];
            efiBootloaderId = "NixOS-b";
          }
        ];
      };
    };
    supportedFilesystems = [ "zfs" ];
    zfs.forceImportRoot = false;
  };

  hardware.enableRedistributableFirmware = true;
  time.timeZone = "America/Chicago";
  networking.hostId = "31eabe12";

  networking = {
    useDHCP = false;
    useNetworkd = true;
    nftables.enable = true;
    firewall = {
      enable = true;
      extraInputRules = ''
        ip saddr 10.0.10.0/24 tcp dport 22 accept
        ip saddr 100.64.0.0/10 tcp dport 22 accept
      '';
    };
  };

  systemd.network = {
    enable = true;
    networks."30-infrastructure" = {
      matchConfig.Name = "enp5s0";
      networkConfig = {
        Address = "10.0.30.20/24";
        DNS = "10.0.30.10";
        Gateway = "10.0.30.1";
      };
      linkConfig.RequiredForOnline = "routable";
    };
  };

  services.openssh = {
    enable = true;
    openFirewall = false;
    hostKeys = [
      {
        path = "/persist/etc/ssh/ssh_host_ed25519_key";
        type = "ed25519";
      }
      {
        bits = 4096;
        path = "/persist/etc/ssh/ssh_host_rsa_key";
        type = "rsa";
      }
    ];
    settings = {
      KbdInteractiveAuthentication = false;
      PasswordAuthentication = false;
      PermitRootLogin = "no";
    };
  };

  users = {
    mutableUsers = false;
    users.rupan = {
      isNormalUser = true;
      extraGroups = [ "wheel" ];
      openssh.authorizedKeys.keys = [
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILW7MVmIGzW4Eq1NJm4+gsGwQ+iL44bIfyAa/wdQ1srQ"
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFTXsL6q+O1d29vTd3TtK2F0MYPggS5KSHryvlIFBS1K"
      ];
    };
  };
  security.sudo.wheelNeedsPassword = false;

  services.smartd = {
    enable = true;
    autodetect = true;
  };
  services.zfs = {
    autoScrub = {
      enable = true;
      interval = "weekly";
    };
    trim = {
      enable = true;
      interval = "weekly";
    };
  };

  systemd.tmpfiles.rules = [
    "d /persist/etc/ssh 0700 root root -"
    "d /persist/var/lib/smartmontools 0755 root root -"
  ];

  environment.persistence."/persist" = {
    hideMounts = true;
    directories = [
      "/var/lib/nixos"
      "/var/lib/smartmontools"
      "/var/lib/systemd"
    ];
    files = [ "/etc/machine-id" ];
  };

  environment.systemPackages = with pkgs; [
    cryptsetup
    curl
    dmidecode
    ethtool
    lm_sensors
    nvme-cli
    pciutils
    smartmontools
    tcpdump
    zfs
  ];

  nix = {
    gc = {
      automatic = true;
      dates = "weekly";
      options = "--delete-older-than 30d";
    };
    settings = {
      auto-optimise-store = true;
      experimental-features = [
        "nix-command"
        "flakes"
      ];
    };
  };

  zramSwap = {
    enable = true;
    memoryPercent = 25;
  };
}
```

- [ ] **Step 2: Add the host composition**

```nix
{
  imports = [
    ./disk-config.nix
    ./hardware-configuration.nix
    ../../modules/nas-base.nix
  ];

  networking.hostName = "nas-01";

  fileSystems."/" = {
    device = "none";
    fsType = "tmpfs";
    options = [
      "defaults"
      "mode=755"
      "size=4G"
    ];
  };
  fileSystems."/persist".neededForBoot = true;
  fileSystems."/var/log".neededForBoot = true;

  system.stateVersion = "26.05";
}
```

- [ ] **Step 3: Run the NAS contract**

Run: `nix develop ./flake -c python -m unittest tests.test_nas_contract -v`

Expected: only the flake export test still fails.

- [ ] **Step 4: Commit the base role**

```bash
git add flake/modules/nas-base.nix flake/hosts/nas-01/default.nix
git commit -m "feat: add hardened NAS base role"
```

### Task 4: Export and evaluate the installable host

**Files:**
- Modify: `flake/flake.nix`

- [ ] **Step 1: Export `nas-01`**

Add this sibling of `nixosConfigurations.adguard-netbird-01`:

```nix
nixosConfigurations.nas-01 = nixpkgs.lib.nixosSystem {
  system = "x86_64-linux";
  modules = [
    disko.nixosModules.disko
    impermanence.nixosModules.impermanence
    ./hosts/nas-01
  ];
};
```

- [ ] **Step 2: Run focused validation**

```bash
nix develop ./flake -c python -m unittest tests.test_nas_contract -v
nix eval ./flake#nixosConfigurations.nas-01.config.system.build.toplevel.drvPath
nix build ./flake#nixosConfigurations.nas-01.config.system.build.toplevel --dry-run
```

Expected: all NAS contracts pass, evaluation succeeds, and the dry run resolves a complete system closure.

- [ ] **Step 3: Run full repository validation**

```bash
nix fmt ./flake
git diff --check
nix flake check ./flake
nix develop ./flake -c gitleaks detect --source . --redact --no-banner
```

Expected: formatting is stable, all repository contracts pass, and gitleaks reports no leaks.

- [ ] **Step 4: Commit the installable host**

```bash
git add flake/flake.nix
git commit -m "feat: export installable NAS host"
```

### Task 5: Install only after the burn-in gate passes

**Files:**
- No repository changes

- [ ] **Step 1: Verify the Exos burn-in completed successfully**

Run remotely against the installer:

```bash
systemctl is-failed nas-exos-burnin.service
tail -80 /tmp/nas-exos-burnin.log
smartctl -x /dev/disk/by-id/scsi-35000c500d91a3f4f
```

Expected: fio reports `err=0`, verification completes without a mismatch, SMART health is `OK`, grown defects remain zero, and uncorrected errors remain zero.

- [ ] **Step 2: Generate the system recovery key locally**

```bash
install -d -m 0700 /home/rupan/.local/share/homelab/secrets
openssl rand -base64 48 > /home/rupan/.local/share/homelab/secrets/nas-01-system-recovery.key
chmod 0600 /home/rupan/.local/share/homelab/secrets/nas-01-system-recovery.key
```

Expected: the key exists only in the local secret directory with mode `0600`.

- [ ] **Step 3: Install without rebooting**

Run `nixos-anywhere` against `nixos@10.0.30.158`, build locally, pass `/home/rupan/.local/share/homelab/secrets/nas-01-system-recovery.key` to remote `/tmp/nas-01-system.key`, and stop after the kexec, Disko, and install phases.

Expected: only the two exact NVMe devices are repartitioned; the 2 TB XFS disk and 10 TB Exos remain absent from the Disko plan.

- [ ] **Step 4: Enroll both system LUKS containers into TPM 2.0**

```bash
systemd-cryptenroll --tpm2-device=auto --unlock-key-file=/tmp/nas-01-system.key /dev/disk/by-partlabel/disk-system-a-luks
systemd-cryptenroll --tpm2-device=auto --unlock-key-file=/tmp/nas-01-system.key /dev/disk/by-partlabel/disk-system-b-luks
```

Expected: each LUKS2 header contains a TPM2 token and still accepts the recovery key.

- [ ] **Step 5: Reboot and verify the installed base**

After removing the installer USB, reboot and verify:

```bash
hostnamectl
zpool status zroot
findmnt / /nix /persist /var/log /boot /boot-fallback
systemctl is-active sshd smartd zfs-scrub.timer zpool-trim.timer
ip -brief address show enp5s0
```

Expected: `nas-01` boots unattended at `10.0.30.20`, `zroot` is an online two-device mirror, both EFI partitions are mounted, persistent paths are ZFS-backed, and SSH plus disk-health services are active.
