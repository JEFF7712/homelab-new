# Local registry implementation and acceptance record

Date: 2026-09-07
Base revision: `465512037c8f6e0ef890f3781ec8e6d1c1757650`
Inventory revision: `6d26784d9b4a898ab3b922b4db26d5370cd44fed`

## Intended final state

The new homelab publishes, imports, browses, and pulls container images through zot at `registry.rupan.dev`. Required current, bootstrap, and rollback content is present by immutable digest. First-party producers publish locally, upstream updates retain their original identity mapping, restore is proven, and all in-scope consumers use the local registry. The nix-snapshotter pilot remains separate.

## Baseline evidence

Read-only checks on 2026-09-06 established:

- all three k3s servers were Ready and reachable;
- Flux reported healthy Kustomizations, with the ntfy HelmRelease still reconciling at the observation instant;
- no failed non-completed workloads were listed;
- all three nodes ran k3s `v1.35.7+k3s1` and lacked `registries.yaml`;
- `nas-01` had healthy single-disk `tank`, 8.92 TiB free, and active Attic, GitLab Runner, and NFS services;
- the independent backup disk had 123 GiB free;
- the registry hostname had no exact public Cloudflare DNS record, but inherited the public tunnel wildcard;
- zot was not installed or listening;
- source and live image inventories differed materially because charts and k3s generate images not visible in direct YAML.

The live inventory covered Pods, init containers, Deployments, DaemonSets, StatefulSets, Jobs, CronJobs, Flux controllers, Cilium, k3s pause/CoreDNS/metrics-server/Helm helpers, cert-manager, ESO, observability charts, backup jobs, and direct application workloads.

## Architecture decisions implemented

- Zot is a native NAS service with local ZFS storage and an independently managed HTTPS endpoint.
- Zot v2.1.20 supersedes the researched v2.1.18 because v2.1.18 has a critical digest multi-tag authorization bypass fixed in v2.1.19.
- Private AdGuard DNS overrides the existing public wildcard only for authorized private clients.
- Registry content, the lock, node mirror rewrites, policy checks, retention identities, and updates share one mapping.
- Node credentials arrive as protected runtime files. They do not enter Git or the Nix store.
- The platform and content preparation are separate from the Flux-active consumer cutover.
- Restic provides encrypted independent-disk backups without initial pruning. Sanoid provides local snapshots.
- Upstream fallback is disabled only as part of the content-complete node rollout.
- The conventional OCI migration precedes any nix-snapshotter experiment.

## Implementation status

| Area | Repository implementation | Live acceptance |
| --- | --- | --- |
| NAS zot service, TLS, auth, storage | Complete, zot 2.1.20 evaluates and its assembled configuration passes `zot verify` | Not deployed |
| Private DNS | Exact AdGuard rewrite and manual CI deployment gate complete | Not deployed |
| Image inventory and lock | 65 immutable records, zero blocking discovery gaps | Destination does not exist yet |
| Digest-preserving import workflow | Copy, verify, conflict refusal, update candidate, and structured reports complete | No content copied |
| k3s node credentials and fallback policy | Three registry-enabled variants and serialized manual rollout complete | Not deployed |
| Flux consumer cutover | Per-owner Kustomize overlays render only locked local digests and remain inactive | Not applied |
| First-party producers | 15 destinations and credential identities specified | Existing producers still publish externally |
| Backup and isolated restore | Sanoid and encrypted independent-disk restic configuration complete | Capacity gate and restore proof outstanding |
| Monitoring | Node exporter metrics and Prometheus alerts complete | Not active |
| Nix snapshotter | Deferred pilot | Not started |

The lock contains 15 nonblocking producer handoffs. They do not prevent copying
the retained releases, but they prevent declaring first-party publishing
migrated. Every lock entry records source identity, raw digest, media type,
platform coverage, destination, consumers, and retention tags. Required
referrers are empty because no source signature, SBOM, or provenance policy was
found for these images. Each record states that authenticity is unsupported,
rather than treating a digest-preserving copy as publisher verification.

## Local verification evidence

The following repository evidence was obtained without changing live state:

- registry supply, consumer, and zot module tests passed, including real
  `zot verify`, conflicting-tag refusal, platform mismatch detection, private
  atomic credential output, rendered public-image rejection, and inactive
  Flux cutover checks;
- all ordinary and registry-enabled k3s configurations, `nas-01`, and
  `adguard-netbird-01` passed Nix evaluation or dry-build checks;
- the 65-image lock passes the offline copy-plan and consumer-policy checks;
- every per-owner cutover overlay renders successfully, and the rendered image
  fields are exact `registry.rupan.dev/...@sha256:` references;
- `nix develop ./flake -c just check` passed all offline gates and 193 tests;
- `nix develop ./flake -c just fmt-check` and
  `nix develop ./flake -c just check-changed` passed.

These checks do not prove TLS issuance, live authorization, destination
content, uncached pulls, backup recovery, garbage collection, or application
health after cutover.

## External producer ownership

The following producer repositories were found locally and are outside this repository's ownership boundary:

| Application | Producer checkout | Existing publication |
| --- | --- | --- |
| apolline | `/home/rupan/businesses/apolline/apolline-site` | Docker Hub from GitHub-hosted Actions |
| darkbit | `/home/rupan/businesses/darkbit/darkbit-site` | Docker Hub from GitHub-hosted Actions |
| distrojeff | `/home/rupan/businesses/distrojeff/distrojeff-site` | Docker Hub from GitHub-hosted Actions |
| nix-agent-site | `/home/rupan/projects/nix-agent` | GHCR from GitHub-hosted Actions |
| pulse-site | `/home/rupan/projects/pulse` | GHCR from GitHub-hosted Actions |
| rupanism | `/home/rupan/projects/sites/rupanism` | GHCR from GitHub-hosted Actions |
| solubility-gnn | `/home/rupan/projects/old/soluble` | Docker Hub from GitHub-hosted Actions |
| spatia | `/home/rupan/projects/spatia` | GHCR backend/frontend workflow, current consumer name requires reconciliation |
| quartz | `/home/rupan/obsidian` | GHCR from GitHub-hosted Actions |
| homelab-renovate-agent | `/home/rupan/homelab` | Docker Hub from legacy GitLab CI |
| homelab-renovate-dashboard | `/home/rupan/homelab` | Docker Hub from legacy GitLab CI |

The producer checkout or pipeline was not found for `cr-demo`, `ism`,
`majorfinder`, or `photography`. Their retained releases can be imported from
the external image repository, but future local builds remain blocked on owner
discovery. The exact destinations and required publisher identities are in the
lock and the generated access-control policy.

The inspected majorfinder and photography repositories deploy to Cloudflare Pages and did not contain the image producer used by Kubernetes. The `cr-demo` and `ism` producer pipelines were not found. These are unresolved owners, not evidence that homelab manifests produce the images.

GitHub-hosted runners cannot be assumed to reach the private endpoint. Each producer needs an authorized private runner or a transfer to the existing NAS GitLab runner. Producer patches must build once, publish only to `registry.rupan.dev/apps/<project>`, retain commit provenance, and return the verified destination digest before desired state changes. No producer repository was edited by this implementation session.

## Authorization boundary

No branch was pushed, CI job triggered, DNS service activated, host switched, registry content copied, Kubernetes object changed, or producer repository modified while preparing this patch. Those actions affect shared infrastructure or external repositories and require explicit authorization after the deployment preflight is reviewed.

## Remaining live acceptance sequence

1. Supply protected runtime credentials and confirm backup capacity.
2. Authorize the private DNS and NAS manual deployment jobs.
3. Import and independently verify all locked content.
4. Authorize the three serialized node jobs.
5. Prove an uncached pull, then authorize each Flux path cutover in sequence.
6. Authorize producer-repository changes and prove one first-party build.
7. Run the candidate update workflow for one upstream release.
8. Restore into isolation, test cold authenticated pulls without upstream access, and exercise retained-content garbage collection.
9. Record each live result here. Do not mark the migration complete until all rows have live proof.
