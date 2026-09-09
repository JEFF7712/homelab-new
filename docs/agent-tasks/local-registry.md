# Local registry implementation and acceptance record

Date: 2026-09-09
Accepted revision: `74b4579eb970bfc428031351c0546b976a7d4ea4`

## Result

The conventional OCI registry is deployed and serving the new homelab. Zot
2.1.20 runs natively on `nas-01`, stores data on `tank/registry`, and is reached
privately as `registry.rupan.dev`. The three k3s nodes have authenticated mirror
configuration with the default upstream endpoint disabled. Repository-owned
Flux consumers render to digest-pinned zot references, and all 17 Flux
Kustomizations applied the accepted revision successfully.

Attic remains the separate Nix binary cache. Forgejo, Harbor, S3-compatible
storage, and nix-snapshotter were not introduced.

## Live acceptance evidence

| Area | Evidence | Status |
| --- | --- | --- |
| Registry service | `zot`, `nginx`, and `tank-registry.mount` active on `nas-01`; `tank/registry` is a 16.1 GiB ZFS dataset with 8.89 TiB available | Accepted |
| TLS and private DNS | All nodes resolve `registry.rupan.dev` to `10.0.30.20`; trusted HTTPS works; anonymous `/v2/` returns 401 on the private path | Accepted |
| Locked import | Initial 65-image import and verification passed; update job `16400518165` copied and independently verified 61 of 61 upstream candidate records at revision `2b2a465` | Accepted |
| Identity | Import and verify reports matched source and destination manifest or index digests, platform sets, and declared referrers | Accepted |
| Update workflow | Valkey 9.1.2 was discovered as digest `sha256:c123e...e1d`, imported under an immutable release tag, verified, then rolled out from zot while retaining the previous digest | Accepted |
| Node runtime | Registry variants are active on all three nodes with upstream fallback disabled; a node pull of the new Valkey index succeeded through `registry.rupan.dev` | Accepted |
| Flux cutover | 17 of 17 Kustomizations Ready at `74b4579`; Home Assistant, Immich, Reloader, direct applications, controllers, storage, observability, and backup workloads use their prepared local overlays | Accepted |
| Stateful data | Home Assistant and Immich PostgreSQL PVCs remained Bound to `home-assistant-postgres-nvme` and `immich-postgres-nvme`; Immich remains on its intentional PostgreSQL 16 deployment | Accepted |
| Applications | `apollinestore.com`, `notes.rupan.dev`, `photos.rupan.dev`, and Home Assistant at `10.0.40.13:8123` returned HTTP 200 | Accepted |
| Observability | Prometheus returned `Prometheus Server is Ready`; Loki returned `ready`; registry alerts and node-exporter collectors are deployed | Accepted |
| Cluster health | All three nodes Ready; Cilium BGP established; the Cilium 1.20.1 installer completed after disabling chart ownership of the Flux-owned GatewayClass | Accepted |
| Backup and recovery | `registry-backup.service` last result is success; the independent XFS backup disk is mounted; a full restic backup, isolated restore, and restored digest pull were completed | Accepted |
| Offline recovery | A disposable cold pull succeeded with source-registry access blocked while zot served the retained digest | Accepted |

The current GitLab import credential was rotated after authentication drift was
detected. The production-scoped protected file variable and zot htpasswd entry
now agree. No credential value was written to Git or retained in task output.

## Authorization checks

Live checks established the intended least-privilege boundaries:

- anonymous clients cannot read the registry;
- the node identity can pull but cannot publish or delete;
- project publishers are restricted to their exact `apps/<project>` path;
- the upstream importer cannot publish into `apps/**`;
- only the maintenance identity has delete or administrative access.

The migration identity remains limited to the migration workflow. Rotate or
remove it after all first-party producer cutovers have been accepted.

## Recovery evidence and retained state

The registry dataset, credentials, metadata, and certificate state survived a
NAS service restart. Service startup is hard-gated on `tank-registry.mount`.
Restic created an encrypted snapshot on the independent disk, `restic check`
passed, and an isolated zot instance served restored current and rollback
digests. The cold-pull test did not alter production routing.

During the PostgreSQL 16 work, an attempted local PostgreSQL 14 recovery was
stopped once the concurrent migration ownership was identified. The intended
PostgreSQL 16 data directory was restored and verified with 2,232 assets and one
user before Immich was resumed. The unused recoverable copy remains at
`/persist/postgres/immich/pgdata.pg14-restored-20260909T1443Z`; it was not
deleted.

An earlier Flux prune during storage adoption removed stateful claims. The
claims and data were recovered, all affected NFS PV reclaim policies were set to
`Retain`, and the final Home Assistant and Immich cutovers preserved their
original Bound volumes. This incident is part of the acceptance history and is
not presented as a zero-downtime migration.

## Validation

Final validation at revision `74b4579` passed:

- `just check-changed`
- `just fmt-check`
- `just provision-check-deps && just check`
- 152 Python tests
- Ruff and pyright
- YAML lint and kubeconform over base and registry overlays
- OpenTofu validation
- gitleaks with no findings
- all NixOS configurations and flake checks
- Nix-agent dry-build of `homelab-01`

The protected GitLab quality pipeline also passed `repository_tests`,
`yaml_schema`, `nas_proof`, and `registry_lock`. Registry job `16400938636`
completed the idempotent full import, and `deploy_registry_node_01` job
`16400938640` applied the final Cilium ownership setting using a target-side
build.

## Producer publishing

Nine identified GitHub producers now build on repository-scoped homelab runners
and authenticate with their exact `publisher-<project>` identity. Their first
post-migration runs succeeded:

| Application | Producer commit | Successful run |
| --- | --- | --- |
| apolline | `52b4cb3` | `34394049932` |
| darkbit | `a9df393` | `34394128099` |
| distrojeff | `5411f87` | `34394157586` |
| nix-agent-site | `0dc6d65` | `34394191216` |
| pulse-site | `04ac384` | `34394230497` |
| rupanism | `5707feb` | `34387949066` |
| solubility-gnn | `5c30ab6` | `34395068342` |
| spatia | `83c733d` | `34394333185` |
| quartz | `c542788` | `34394360679` |

Apolline run `34394049932` published
`registry.rupan.dev/apps/apolline:0.0.14`; an authenticated cluster-node pull
returned digest `sha256:ab19a03f...8575`. This is the required direct
first-party publication proof. The build workflows still retain their external
publication during the transition; removing those outputs is deferred until all
producer and rollback consumers are accounted for.

The legacy `/home/rupan/homelab` pipeline still owns the renovate application
images and has unrelated local changes, so it was not modified here.

No producer checkout was found for `cr-demo`, `ism`, `majorfinder`, or
`photography`. Those four are explicit owner-discovery blockers for future
publishing, not missing runtime content.

New GitHub runner Deployments were created concurrently on 2026-09-09 and are
being adopted by separate repository work under
`gitops/automation/github-runner`. Until that work commits digest-pinned local
runner and DinD images, those newly introduced Pods are an explicit live
inventory exception. They were not modified here to avoid overwriting the
parallel owner.

The registry platform, upstream update workflow, restore path, direct
first-party publishing, and all existing repository-owned consumers are
operational. The concurrent GitHub runner adoption must still be committed and
converted to locked local runner images. The four unavailable producer owners
and the dirty legacy renovate checkout remain bounded future-publishing
handoffs.

## Deferred work

The nix-snapshotter pilot is intentionally deferred. It is not required for the
accepted conventional OCI registry and must retain its separate VM test matrix,
rollback, and failure boundary.
