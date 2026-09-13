# Repository and runtime findings

Observed 2026-09-12, approximately 13:50 UTC. Repository revision at inspection: `d3f6e50531b5fe475b39d0da0332376cc5cf861a`. Initial worktree was clean. All runtime operations were read-only.

## Capacity snapshot

| Host | CPU | RAM total / available (MiB) | Free `/persist` | KVM device |
| --- | --- | --- | --- | --- |
| homelab-01 | i5-6500T, 4 logical CPUs | 15871 / 12934 | 912 GiB, local NVMe | Present |
| homelab-02 | V1605B, 8 logical CPUs | 14931 / 10207 | 38 GiB, local SSD | Absent in probe |
| homelab-03 | V1605B, 8 logical CPUs | 14931 / 8150 | 39 GiB, local SSD | Absent in probe |
| nas-01 | Ryzen 5600G, 12 logical CPUs | 15352 / 1947 | 192 GiB available in ZFS dataset | Absent in probe |

Evidence: authenticated SSH `hostname`, `uptime`, `free -m`, `df -h /persist`, `/dev/kvm` existence and `lscpu`; no module loading or configuration changes. Absence of `/dev/kvm` is not proof the hardware cannot virtualize. NAS used about 1216 MiB of zram swap. A follow-up ARC probe reported about 10.1 GiB of ZFS ARC, so its low Linux MemAvailable is not proof of irreclaimable memory pressure or lack of all VM capacity. ZFS dataset free space is shared-pool capacity, not a reserved VM allocation.

`kubectl top nodes` reported approximately 3239, 4960, and 7412 MiB used on homelab-01/02/03. These are one-time observations, not sustained capacity measurements. All three nodes are embedded-etcd control-plane nodes. Kubernetes currently advertises essentially all node memory as allocatable; the inspected k3s module has no workspace memory reservation. Host-level VM consumption must be reflected in scheduler reservations before co-location.

The existing hardware supports investigating a bounded two-VM pilot on homelab-01. It does not justify promising four unrestricted simultaneous builds. A dedicated virtualization host would reduce contention and the security blast radius of co-location. No hardware purchase or host repurposing is authorized by this research.

## Cluster and HA

`just status cluster` reported nodes Ready and Flux Kustomizations/HelmReleases Ready at the inspected revision. It also printed an Error pod, `home-assistant/test-pull`, while labeling the workload probe pass. Do not describe this result as all workloads healthy or rely only on the command exit status. No remediation was attempted.

HA, HA PostgreSQL, and Immich PostgreSQL were running on homelab-01. HA deployment has one replica and `hostNetwork: true`; HA's ordinary pod-network policy must not be assumed to govern its host-network egress. The installed image is digest-pinned; application version and guest account roles were not queried. Source includes HomeKit light bridging, which is another bedroom control path to inspect.

`.gitlab-ci.yml:588-639` uses a manual HA deployment job, `nas-privileged`, a shared resource group, an administrator kubeconfig fetched through host SSH, and an HA token. Independent guest deployment therefore requires an explicit bounded automation path; changing every HA deployment to automatic would widen scope incorrectly.

`scripts/home_assistant/source.py` loads a flat `home-assistant/automations/*.yaml` directory. Use a reserved filename/id prefix for guest-managed resources, or deliberately extend and test loading before proposing nested guest directories. Existing automation validation checks structure, not permissions. Live UI writes bypass the cooperative deployment lock.

## Bedroom controller

`docs/runbooks/roku-bridge-architecture.md` identifies three bedroom lights behind the custom Roku MQTT bridge on adguard-netbird-01. Shared HA currently has `roku/#` MQTT rights. Strong bedroom separation requires changing those rights and discovery, not only removing dashboard cards. MQTT states are optimistic; actual physical behavior or bridge command evidence is needed to test isolation. Existing HomeKit exposure and mixed bedroom/shared automations also require migration.

## Codex and VM components

Official [Codex headless authentication](https://learn.chatgpt.com/docs/auth#login-on-headless-devices) documents device authentication and an SSH-forwarded localhost callback fallback. Use per-user login inside each VM, never a shared auth cache. Code-server terminals provide the baseline browser path; no proprietary extension support is assumed.

The locally evaluated pinned nixpkgs tree includes `nixos/modules/virtualisation/libvirtd.nix`, including QEMU unprivileged execution configuration. No nix-agent or mcp-nixos tools were exposed in this session, so source inspection was used instead. Implementation must evaluate actual options against the flake pin and build them; this research did not build a virtualization host.

Official [libvirt networking](https://libvirt.org/formatnetwork.html) documents that default NAT permits outbound access and communication among guests on the same virtual network. Select host-owned bridges/firewall rules explicitly. [Ubuntu Noble cloud images](https://cloud-images.ubuntu.com/noble/current/) provide a practical conventional Linux guest base; resolve a dated image and verify its signed checksums during implementation instead of deploying a moving `current` URL.

## Remaining observations required

Sustained resource use, actual NetBird groups/grants, public service authorization, IPv6 routing, exact VM IP reservations, guest identities/keys, HA nonadmin service behavior, authentication refresh, and denied-path tests remain implementation preflight work. No live firewall rules, secrets, accounts, VMs, or HA resources were changed.
