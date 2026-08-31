# OPNsense Bootstrap Convergence Design

## Status

Approved on 2026-08-31.

## Goal

Converge the physical OPNsense router on the final six-VLAN homelab design without preserving the current interface layout as a migration constraint.

## Control plane

The laptop is allowed to perform one bootstrap apply because GitLab shared-runner quota is exhausted and the private NAS runner does not exist yet. OpenTofu state is created in the private GitLab project before any resource import or mutation. Later plans and applies use the same HTTP state with locking. Once the NAS runner exists, laptop applies stop.

OpenTofu owns VLAN devices, Kea DHCP subnets and reservations, firewall rules, and supported Unbound resources. Existing provider-supported objects are imported before convergence. The OPNsense reconciler owns interface assignments and resolves generated VLAN device names from live VLAN `(parent, tag)` records rather than assuming names such as `vlan30`.

## Desired network

The router converges on VLANs 10, 20, 30, 40, 50, and 60 over `igb0`. The existing VLAN 20 object with UUID `47cac540-15b6-4838-9de1-f7e8e7307d2b` is imported. New VLANs are created by the provider. Interface assignments use the live generated device names and configure gateway addresses `10.0.<tag>.1/24`.

The managed switch uses one tagged trunk to OPNsense. Host-facing ports are assigned tagged or untagged membership and PVIDs according to their final roles. The existing untagged LAN can remain temporarily for bootstrap access, but it is not part of the target design.

## Execution and proof

The bootstrap sequence is state initialization, import, refresh-only plan, desired plan review, provider apply, interface reconciliation, switch convergence, and runtime reachability checks. No credential, plaintext configuration backup, or backend token enters Git or command output.

Success requires persistent GitLab state, one imported VLAN 20 object, all six live VLANs on `igb0`, all six gateway CIDRs present, DHCP scopes matching desired state, switch trunk reachability, and a subsequent clean OpenTofu plan.
