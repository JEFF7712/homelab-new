# Homelab Workstream Map

1. OPNsense control plane: import, provider-backed DHCP, firewall, and Unbound state, typed API reconciliation for interface and FRR-global state, read-after-write checks, and encrypted pre-change backups.
2. AdGuard and NetBird appliance: NixOS disko layout, impermanence, SOPS bootstrap, AdGuard data migration, NetBird routing policy, and live DNS and remote-access checks.
3. NAS platform: disk burn-in, mirrored NVMe system pool, ZFS datasets and retention, NFS export, Attic, GitLab runner, and restore verification.
4. k3s and Cilium: three-server NixOS roles, embedded etcd, custom-CNI bootstrap, Cilium BGP control plane v2, LoadBalancer canary, and OPNsense route verification.
5. Flux platform and migration: GitLab bootstrap, SOPS and ESO dependency chain, storage classes, ingress, observability, application migration, and decommission gates.
