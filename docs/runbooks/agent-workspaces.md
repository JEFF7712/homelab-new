# Agent workspace operations

The versioned inventory is `config/agent-workspaces/workspaces.json`. An enabled entry must contain real enrollment identities, keys, collision-checked addresses, pinned image metadata, and paths below its workspace-specific storage and credential roots. Host limits are hard manifest validation limits, not evidence that the host can safely sustain them.

Run `just workspace-validate` before rendering or inspecting anything. `just workspace-plan` is offline and deterministic. `just workspace-status <id>` reads libvirt and disk/receipt state without changing it.

Provisioning is an authorized host operation:

```sh
just workspace-provision <id> --authorized
```

It must run as root on the manifest-selected host. It verifies storage ancestry, ownership and modes, refuses unknown domains/disks/receipts, checks that nftables and the dedicated bridge are active, downloads the pinned guest image with SHA-256 verification, creates separate system/data disks and a cloud-init seed, then defines and starts the domain. A crash that leaves assets without a receipt fails closed and requires inspection. It never adopts an unknown domain or disk.

Deprovisioning requires the same explicit flag:

```sh
just workspace-deprovision <id> --authorized
```

It accepts only a domain whose UUID, manifest hash, receipt, and disks agree. It destroys and undefines the domain but preserves both disks, seed material, domain XML, and receipt. Re-provisioning a matching deprovisioned workspace reuses those verified assets.

`flake/modules/agent-workspace-network.nix` derives one host-owned bridge and one interface-bound nftables policy per enabled workspace. The host must use systemd-networkd. Libvirt requires nftables and networkd. Guest IPv6, spoofed IPv4, other workspace segments, host input, private/special destinations, and unsolicited ingress are denied. Explicit HA capability API, DNS, NTP, public Internet egress, and declared SSH/HTTPS ingress sources are allowed. Filtering occurs before Internet masquerade. Stopping nftables first lowers each workspace tap interface, then destroys a running domain before removing policy.

The host modules are enabled on `homelab-01`. Kubernetes reserves 2 CPUs and 10 GiB of memory for the host and cluster. The workspace slice limits all workspace VMs together to 200 percent CPU, uses a 9 GiB memory pressure threshold, and has a 10 GiB hard memory limit. The versioned inventory remains empty, so no user is enrolled and no persistent workspace VM is defined.

The first disposable guest acceptance is recorded in [the 2026-09-13 evidence record](../agent-tasks/agent-workspace-live-acceptance.md). It proves boot, whole-domain CPU limiting, guest memory enforcement, public and container egress, selected deny rules, active and persistent XML verification, and bounded fail-closed firewall shutdown behavior at deployed revision `914629e8ffd1df8516c9661c6f12476fcb288e53`. It does not complete the enrollment gate.

Before enrollment, complete and record these checks against one deployed revision:

1. Run two disposable guests simultaneously. Prove guest-to-guest and cross-workspace denial under CPU, disk, and network pressure. Measure etcd, PostgreSQL, and Home Assistant before, during, and after load. Stop load immediately when a health gate fails.
2. Enroll the actual pilot identities only after their collision-checked addresses and credentials are available. Prove LAN SSH and HTTPS with NetBird stopped, remote access from an external network through NetBird, and cross-user login denial.
3. Prove authenticated browser access, each user's own agent provider credentials, session continuity after disconnect and reboot, and restore of a quiesced encrypted backup into an isolated VM with networking disabled.
4. Deploy and accept the HA capability API and trusted deployment worker before granting a guest automation deployment access. Guests must never receive the HA administrator credential, repository writer credential, infrastructure kubeconfig, or privileged runner access.

Retain separate evidence for spoofing, tagged frames, IPv6, DNS rebinding, alternate private paths, firewall reload/reboot behavior, host-service denial, and measured throughput. Libvirt I/O weight is relative priority, not a throughput cap.

Bedroom isolation is a separate milestone. Do not claim it from workspace isolation, HA entity visibility, or dashboard permissions. It remains unverified until the private control boundary and physical device denial tests pass.

Emergency isolation stops the workspace domain before removing or changing its deny policy. Preserve its disks and receipt. Never disable the firewall while a guest interface remains active.
