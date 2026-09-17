# Agent workspace live acceptance record

Date: 2026-09-13
Deployed revision: `914629e8ffd1df8516c9661c6f12476fcb288e53`
Host: `homelab-01`

## Result

The host foundation is deployed and enabled. No user is enrolled: the versioned workspace inventory is empty and no persistent workspace domain exists. One disposable Ubuntu 24.04 guest was booted and exercised, then its domain, disks, runtime policy, key material, and temporary network objects were removed after inspection.

This evidence accepts the single-guest foundation and the two-guest isolation and resource-pressure gate. It does not accept production enrollment, real LAN and NetBird identities, browser authentication, agent credentials, backup recovery, HA automation deployment, or bedroom isolation.

## Desired and deployed state

| Area | Evidence | Status |
| --- | --- | --- |
| Repository | `homelab-01` imports and enables both workspace modules at revision `914629e8ffd1df8516c9661c6f12476fcb288e53` | Deployed |
| Kubernetes reservation | K3s uses `system-reserved=cpu=2,memory=10Gi`; observed allocatable capacity was 2 CPUs and `5766296Ki` memory | Deployed |
| Aggregate VM limit | `machine-agent\\x2dworkspaces.slice` reported a 2 CPU quota, 9 GiB `MemoryHigh`, 10 GiB `MemoryMax`, and systemd-oomd pressure action | Deployed |
| Host services | `k3s`, `libvirtd`, `nftables`, and `systemd-oomd` were active after deployment | Accepted |
| Enrollment | Inventory empty, `virsh list --all` empty after cleanup, and nftables retained only the base workspace chains | Blocked by remaining gates |

GitLab pipeline `2844789379` passed repository validation and the fixed-host dry-run job `16471112589`. The first deployment job stopped at the Kubernetes drain gate because stale terminating PostgreSQL API objects remained after replacement containers were running. Those stale objects were inspected and removed. Retry job `16471147477` completed deployment at `2026-09-13T16:19:00Z`, including node readiness, PostgreSQL rollout checks, and Cilium BGP checks.

## Single-guest live evidence

The disposable guest used the official Ubuntu 24.04 cloud image with SHA-256 `612b2c0cc1bc413a6cb8c38fd611794caf0f2b436c50013d8b3794db12ad7354`. Its acceptance-only configuration allocated 2 vCPUs, 2048 MiB RAM, a 100 percent whole-domain CPU limit, separate sparse system and data disks, and `172.31.255.0/30`.

| Check | Observed result | Status |
| --- | --- | --- |
| Provision and boot | Cloud-init completed and SSH returned hostname `agent-live-acceptance` | Accepted |
| Domain identity | Receipt, deterministic UUID, active XML, and persistent XML agreed | Accepted |
| CPU limit | Two busy processes consumed about 12.4 CPU seconds over 12 seconds; libvirt child cgroup reported `cpu.max=100000 100000` and schedinfo reported matching global quota and period | Accepted |
| Guest memory | A 3 GiB allocation in the 2 GiB guest failed with `MemoryError` | Accepted |
| Disk policy | Libvirt reported I/O weight 100 | Configuration verified only |
| Guest Internet | Public HTTPS succeeded | Accepted |
| Container Internet | Rootless Podman pulled `alpine:3.20`; HTTPS from the container succeeded | Accepted |
| Private and host denial | Private LAN, metadata `169.254.169.254`, and new host service connections failed | Accepted for tested paths |
| MAC anti-spoof | A wrong-source-MAC probe incremented the live nftables drop counter | Accepted |
| IPv6 denial | An IPv6 probe incremented the live host-input drop counter | Accepted |
| Firewall shutdown | With libvirtd unavailable, nftables shutdown lowered the guest tap and completed after its 10 second destroy timeout; the VM process survived disconnected | Accepted as fail-closed isolation, guest termination not guaranteed |
| Cleanup | Domain, storage, runtime drop-in, bridge, namespace, temporary key, and guest nftables rules were absent after cleanup | Accepted |

The workspace scope itself reported an unlimited CPU setting because libvirt applies the domain limit in its child cgroup. Verification therefore inspected both the libvirt scheduler values and the child cgroup. I/O weight was not treated as a throughput cap.

Tagged-frame and alternate-source-IP probes were attempted, but their live nftables counters were not conclusively observed. The NixOS integration test covers the intended policy behavior; live acceptance remains open. During the K3s restart, etcd logged transient `too many requests` warnings at `2026-09-13T10:55:34-05:00` and then recovered. No sustained failure was observed, but this single-guest run did not measure etcd, PostgreSQL, or Home Assistant under guest load.

## Remaining enrollment gates

| Gate | Required evidence | Status |
| --- | --- | --- |
| Two simultaneous guests | The hardened runner at merge `256bf578c82fc5385470cdb8d44ce4ebaf6fff1b` ran two 2-vCPU, 2 GiB guests for 60 seconds against deployed workspace revision `914629e8ffd1df8516c9661c6f12476fcb288e53`. It measured 123.43 aggregate CPU seconds, 1 GiB written per guest, 342,202,643 and 319,747,209 bytes received, verified SSH listeners, and observed three firewall drops in each peer direction. Before, after, and all 11 in-load samples retained three Ready nodes, three etcd voters, PostgreSQL `SELECT 1`, HA HTTP 200, and no pressure conditions. Maximum observed latencies were 0.297 seconds for node status, 0.209 seconds for etcd readiness, 0.336 seconds for PostgreSQL, and 0.031 seconds for HA. The [raw evidence](evidence/agent-workspace-two-guest-hardened-2026-09-14.json) records the accepted run. Both domains, disk trees, bridges, and temporary policy were absent after cleanup; nftables and HA remained healthy. | Accepted |
| Real access identities | Local LAN positive authentication, cross-user SSH authentication denial, unauthorized key rejection, password authentication denial, and peer-to-peer firewall timeout denial were verified against live guests `agent-rupan` and `agent-sam` on 2026-09-16. Cluster health before and after confirmed all 5 nodes ready, 3 etcd voters, healthy PostgreSQL query, and Home Assistant 200 OK ([raw evidence](evidence/agent-workspace-real-access-2026-09-16.json)). Remote NetBird access was verified via enrolled device `100.94.115.203` reaching `172.31.10.6/32` through routing peer `adguard-netbird-01` (`100.94.249.145`) with NetBird access policy scoping, established conntrack state on `homelab-01`, and nftables drop enforcement for non-permitted destinations. | Accepted |
| Browser and agent use | `code-server` web IDE verified on port 443 with TLS and mandatory password authentication (unauthorized redirects to login; valid auth yields session cookie). `tmux` terminal persistence verified across SSH disconnect with systemd user linger active. Dedicated 64 GiB ext4 data disk `/dev/vdb` mounted at `/home/developer/workspace` verified persistent across a full guest VM reboot. Rootless Podman container execution (`alpine:latest`) verified inside guest. | Accepted |
| Backup recovery | Quiesced encrypted backup restored to a separate isolated domain; content and boot verified before any network attachment | Not run |
| HA capability deployment | Capability API and trusted worker policy rejection, bounded accepted change, exact-resource Git transaction, protected CI, and authenticated live readback | Not implemented |
| Bedroom isolation | Separate controller/authentication/MQTT boundary and physical denial tests | Separate unverified milestone |

Do not add enabled inventory entries or distribute ingress credentials until the real-access, browser-and-agent, backup-recovery, and HA-capability gates are accepted against the same deployed revision or explicitly revalidated after a newer deployment. Bedroom isolation remains a separate milestone.

## Recovery

Emergency isolation lowers the workspace tap before changing or removing its firewall policy. Destroy the domain when libvirt is available, preserve its disks and receipt for inspection, and revoke ingress, NetBird, browser, agent-provider, and deployment credentials independently. A VM may remain running but disconnected when libvirt is unavailable, so tap state is the authoritative immediate containment check.
