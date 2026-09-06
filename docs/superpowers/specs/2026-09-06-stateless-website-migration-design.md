# Stateless Website Migration Design

## Status

Approved for implementation planning on 2026-09-06.

## Goal

Migrate the first three stateless legacy websites, Apolline, Darkbit, and DistroJeff, from the Talos/ArgoCD homelab into the NixOS/k3s/Flux homelab without moving persistent data or changing the legacy repository.

## Scope

The migration covers:

- `apollinestore.com`, from `infrastructure/websites/apolline.yaml`.
- `darkbitapparel.com`, from `infrastructure/websites/darkbit.yaml`.
- `distrojeff.com`, from `infrastructure/websites/distrojeff.yaml`.

Each site is a single HTTP container with no persistent volume. The new manifests will preserve the legacy image, container port, replica count, and public hostname. Mutable image tags will be resolved to immutable digests before implementation when the registry exposes the digest.

The migration does not cover:

- Cloudflare tunnel hostname or origin configuration.
- Legacy deletion, Talos shutdown, Longhorn cleanup, or ArgoCD changes.
- The remaining websites, rupan sites, media workloads, Obsidian, PredMarkBot, or automation workloads.
- Persistent storage or database migration.

## Architecture

The new repository will own these resources under `gitops/websites/`:

```text
gitops/websites/
  kustomization.yaml
  apolline/
    kustomization.yaml
    namespace.yaml
    deployment.yaml
    service.yaml
    route.yaml
  darkbit/
    ...
  distrojeff/
    ...
```

Each site receives a namespace, a Deployment, a ClusterIP Service, and a Gateway API `HTTPRoute` attached to the existing `default/homelab` Gateway. Routes use the site hostname and forward `/` to the site Service on port 80. Certificate resources are not copied because public TLS is terminated by the existing Cloudflare path, while the in-cluster origin remains HTTP as with the current Immich route.

The cluster-level Flux Kustomization will depend on `ingress` and will health-check all three Deployments. This makes the migration declarative and prevents the website layer from reporting ready before the Gateway API resources and workloads exist.

## Workload hardening

Each Deployment will:

- Run one replica, matching the legacy workload.
- Use the legacy application container port.
- Set `allowPrivilegeEscalation: false` and drop all Linux capabilities.
- Use a RuntimeDefault seccomp profile.
- Run as non-root where the image supports it, preserving an explicit exception only if a live rollout proves the image requires root.
- Use a read-only root filesystem only when the image starts successfully with that restriction.
- Include an HTTP readiness probe on the application port when the site exposes a stable root endpoint.

The implementation will not invent health endpoints or writable mount paths. If a hardening setting prevents startup, the setting will be adjusted narrowly and the reason recorded in the implementation plan or verification report.

## Routing and external access

The initial change only creates in-cluster `HTTPRoute` resources. Cloudflare hostname routing remains an external follow-up because its configuration is outside this repository and requires live Cloudflare state verification. The website migration is considered internally successful when the Deployments, Services, Routes, and Gateway status are healthy. Public reachability is reported separately until Cloudflare routes are confirmed.

## Verification

Before any deployment:

1. Render all website Kustomizations and validate the resulting Kubernetes objects.
2. Verify every image reference is resolvable and immutable where possible.
3. Run the repository's focused Python, YAML, and secret checks applicable to changed files.

After authorized Flux deployment:

1. Confirm the website Flux Kustomization is ready.
2. Confirm all three Deployments have available replicas and no non-ready pods exist in their namespaces.
3. Confirm Services have ready endpoints.
4. Confirm each `HTTPRoute` is accepted and programmed by the Gateway.
5. Test the in-cluster origin path from an appropriate cluster-local probe.
6. Test public hostnames only after Cloudflare routing is independently confirmed.

No legacy resource will be removed until the replacement has passed these checks and the public access path, if migrated, has been verified.
