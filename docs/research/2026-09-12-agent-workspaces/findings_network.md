# Agent workspace network boundary findings

Date: 2026-09-12. Read-only source review and official documentation research. No live NetBird account, firewall, or VM runtime verified.

## Recommended boundary

Use one root-capable KVM VM per person, with independent disks and host-enforced CPU, memory, disk and process/IO budgets. No host directory shares, host Docker/libvirt sockets, privileged host services, infrastructure secrets or management credentials in guest VMs. Rupan's VM is a separate trust class. Do not select a host until current capacity and virtualization support have been measured.

Network enforcement belongs on the trusted virtualization host or an external firewall, never solely in a guest whose user has root. Give each VM an isolated virtual L2 segment or equivalently verified tap-level isolation. Bind permissions to host-controlled tap/interface identity, and enforce permitted MAC/IP sources. A guest changing its IP, MAC, routes, firewall, Docker network, or VLAN tags must not gain another user's permissions. Drop guest VLAN-tagged traffic. Avoid bridging guests onto infrastructure VLAN 30 or trusted-client VLAN 20.

Libvirt supports per-interface traffic filters and anti-spoofing filters. These are building blocks, not a completed security policy. [Libvirt network filters](https://libvirt.org/formatnwfilter.html)

Default NAT networks allow outbound LAN access; NAT does not implement the intended private-network denial. Explicitly enforce host INPUT and forwarded traffic, including traffic between guests. Libvirt creates its own firewall rules, so inspect effective combined rules and reboot behavior rather than trusting one configuration file. [Libvirt firewall behavior](https://libvirt.org/firewall.html)

Guest egress policy: allow return traffic, narrow DNS/NTP endpoints, the HA capability gateway on its exact address and port, then Internet destinations after private/special/overlay/cluster/host destinations are excluded. Inventory actual homelab prefixes, global IPv6 prefixes, service VIPs, pod/service networks, link-local and overlay ranges. Either disable IPv6 externally at guest taps or apply an equivalent IPv6 policy, including RA/ND and link-local paths. An IPv4-only denylist is insufficient. Deny hypervisor control, router UI/API, Kubernetes, storage, MQTT, other VM endpoints and metadata services. Treat guest-accessible DNS as a resolver only, with its administration ports denied.

## LAN and remote ingress

LAN clients need no NetBird: offer authenticated HTTPS browser access and SSH through narrowly exposed workspace endpoints. Browser identities and SSH keys map to one workspace. Authentication remains required on LAN. Generic local LAN source-IP rules cannot identify which human owns a device, so authorize at the entry service or each VM. App previews and SSH tunnels must end inside the same restricted VM; do not expose a generic proxy into the trusted host network.

For remote access, install NetBird on users' client devices and terminate homelab routing on trusted infrastructure outside their VMs. Publish only the workspace entry endpoints as narrow Networks resources, preferably per-workspace IP resources and TCP ports. Guest users must not administer NetBird policies, setup keys, group membership or routing peers. Use separate Rupan and invited-user device groups. Preserve an explicit Rupan management path before removing overly broad defaults.

NetBird policies are additive grants. Its automatically created All-to-All policy defeats restrictive additions and must be audited along with every existing policy and group. Deny-by-default only applies when no broad grant remains. [NetBird access control](https://docs.netbird.io/manage/access-control)

Networks resource policies govern traffic forwarded through routing peers. Access to services on a routing peer itself needs peer-to-peer input policies. Masquerading can collapse identities at the downstream firewall, so downstream source addresses alone cannot replace NetBird authorization. A dedicated guest routing peer/segment is an optional stronger boundary if the existing routing peer has broad management access. [NetBird routing peers](https://docs.netbird.io/manage/networks/how-routing-peers-work)

Do not enroll root-owned guest VMs into a broadly privileged personal NetBird group. A guest can install arbitrary VPN software using Internet access, but that must grant no homelab access absent an independently authorized identity and remote endpoint. Guest group grants must remain narrow even if their personal NetBird credential is imported into a VM.

## Repository facts

- `docs/network/switch-port-map.md:3`: OPNsense owns inter-VLAN routing/firewall. Ports and VLANs are desired/documented state, not runtime proof.
- `docs/network/switch-port-map.md:15`: the existing OPNsense trunk carries VLANs 10, 20, 30, 40, 50, 60. No dedicated coding-workspace VLAN exists in that map.
- `docs/network/switch-port-map.md:17`: the cluster access switch is unmanaged and attached as VLAN 30; a new trunk to cluster hardware cannot be assumed.
- `flake/modules/adguard-netbird-appliance.nix:224`: appliance infrastructure address is `10.0.30.10/24`, with a VLAN 60 interface at `10.0.60.2/24`.
- `flake/modules/adguard-netbird-appliance.nix:341`: the NetBird client uses routing server features and `wt0`.
- `flake/modules/adguard-netbird-appliance.nix:210`: appliance input permits SSH, DNS and port 3000 from `wt0`, making effective NetBird peer input policy material.
- `tofu/opnsense/homelab.auto.tfvars:403`: `netbird-allow-private` permits VLAN60 `10.0.60.0/24` to all `10.0.0.0/8`. This is not a guest-safe downstream policy by itself.
- `tofu/opnsense/homelab.auto.tfvars:371`: existing guest/IoT private block covers IPv4 `10.0.0.0/8`; do not copy it as a complete workspace exclusion policy.

Implementation must use the repo's owning Nix/Tofu/reconciler sources and authorized deployment paths. A host-local isolated VM network is possible without assuming a new physical VLAN, but its routing/address ownership and OPNsense interaction must be explicitly designed. NetBird live policies currently have no verified source-of-truth mapping in this review.

## Limits that the final plan must state

Unrestricted Internet plus public homelab endpoints means a strict claim that guests cannot contact any other homelab service is false. They can reach public reverse proxies, Cloudflare Tunnel hostnames or external relay paths. IP/FQDN blocks, DNS filtering and SNI checks cannot close all paths while arbitrary outbound tunneling remains allowed. Enforce authentication and authorization at every public service; audit public/alternate origins and disable unintended anonymous or guest grants. Do not give the entire homelab an IP-based trusted exemption merely because guest traffic exits the home WAN.

Personal devices already on the LAN may independently reach homelab services. VM isolation does not change that. If the requirement includes all access by these people, audit and segment their LAN devices separately, and scope their NetBird identities accordingly.

An existing personal service token, an intentionally delegated Rupan credential, SSH agent forwarding, or Rupan connecting to a malicious guest-controlled service can bypass intended identity separation. Prevent unattended broad credential forwarding and do not claim VM controls revoke rights held elsewhere. HA's gateway must itself prevent arbitrary outbound requests/commands and privileged configuration changes; a network exception to an unrestricted proxy is not a boundary.

KVM provides a strong practical isolation boundary, not an absolute guarantee against hypervisor/kernel vulnerabilities or side channels. Patching and host resource reservations are required. Root users sharing physical hardware can still compete for finite CPU/IO and link bandwidth within their budgets.

## Acceptance evidence required

1. From a root shell and a root-owned container in every guest, verify permitted Internet, DNS, HA gateway and own workspace access.
2. Verify denial of representative management, router, Kubernetes, storage, MQTT, other users, Rupan VM, IPv6 and overlay targets.
3. Repeat after guest IP/MAC changes, VLAN tags, secondary addresses and new guest/container routes; host policy must remain effective.
4. Verify own remote workspace succeeds and other workspaces/private resources fail for an actual invited-user NetBird identity; separately verify Rupan's path.
5. Verify LAN paths with NetBird disconnected and unauthorized application identities; browser and SSH authorization must hold independently.
6. Exercise public homelab hostnames, direct WAN hairpin and alternate origins. The expected result is service-level unauthorized access, not a blanket assertion that TCP cannot connect.
7. Repeat boundary checks after host/VM/relevant firewall restart. Verify restoring a VM backup cannot regain revoked credentials or broader rights.
8. Record actual rules, NetBird group/policy exports with secrets redacted, client identity, target, result and timestamp. Static configuration checks do not prove deployed isolation.
