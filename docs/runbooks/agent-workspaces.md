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

Do not enable the host modules or enroll a user until the selected addresses, ingress identities, HA endpoint, image digest, and client keys are real. Before enrollment, run live acceptance with root in a disposable guest: verify cgroup CPU/memory behavior, disk and network pressure, spoofing, tagged frames, IPv6, DNS rebinding, alternate private paths, firewall reload/reboot behavior, guest-to-guest denial, host-service denial, and recovery access. Record actual throughput limits separately because libvirt I/O weight is relative priority, not a throughput cap.

Emergency isolation stops the workspace domain before removing or changing its deny policy. Preserve its disks and receipt. Never disable the firewall while a guest interface remains active.
