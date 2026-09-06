# Stateless Website Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate Apolline, Darkbit, and DistroJeff into the new Flux-managed k3s cluster as stateless Gateway API applications.

**Architecture:** Add one Kustomize directory per site under `gitops/websites/`, with a Namespace, hardened Deployment, ClusterIP Service, and HTTPRoute attached to the existing `default/homelab` Gateway. Add one cluster-level Flux Kustomization that depends on the existing ingress layer and health-checks all three Deployments.

**Tech Stack:** Kubernetes Deployments and Services, Gateway API `HTTPRoute`, Kustomize, Flux Kustomize Controller, GHCR images, `kubectl`, `kubeconform`, `yamllint`.

---

### Task 1: Resolve and record immutable website images

**Files:**
- Modify: `gitops/websites/*/deployment.yaml` after image inspection.

- [ ] **Step 1: Resolve the three legacy GHCR tags to digests.**

Run from the repository root:

```sh
for image in \
  ghcr.io/jeff7712/apolline:0.0.13 \
  ghcr.io/jeff7712/darkbit:0.0.25 \
  ghcr.io/jeff7712/distrojeff-site:0.0.22; do
  nix shell nixpkgs#skopeo -c skopeo inspect --format '{{.Name}}@{{.Digest}}' "docker://$image"
done
```

Expected: one `sha256:` digest per image. If registry inspection is unavailable, retain the exact legacy tag and record the verification limitation instead of inventing a digest.

### Task 2: Add the Apolline website manifests

**Files:**
- Create: `gitops/websites/apolline/kustomization.yaml`
- Create: `gitops/websites/apolline/namespace.yaml`
- Create: `gitops/websites/apolline/deployment.yaml`
- Create: `gitops/websites/apolline/service.yaml`
- Create: `gitops/websites/apolline/route.yaml`

- [ ] **Step 1: Define the Kustomization resources.**

`gitops/websites/apolline/kustomization.yaml` must contain:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - namespace.yaml
  - deployment.yaml
  - service.yaml
  - route.yaml
```

- [ ] **Step 2: Define namespace, Deployment, and Service.**

Use namespace `apolline`, Deployment `website-deploy`, selector label `app: apolline-web`, one replica, container port `8080`, and Service `apolline-svc` exposing port 80 to targetPort 8080. Preserve the legacy `/var/cache/nginx`, `/tmp`, and `/run` `emptyDir` mounts and run the container as UID 101 with all capabilities dropped, no privilege escalation, RuntimeDefault seccomp, and a read-only root filesystem.

- [ ] **Step 3: Define the Gateway API route.**

Create `HTTPRoute` `apolline-route` in namespace `apolline`, parent `default/homelab`, hostnames `apollinestore.com` and `www.apollinestore.com`, and a `/` PathPrefix backend reference to `apolline-svc:80`.

### Task 3: Add the Darkbit website manifests

**Files:**
- Create: `gitops/websites/darkbit/kustomization.yaml`
- Create: `gitops/websites/darkbit/namespace.yaml`
- Create: `gitops/websites/darkbit/deployment.yaml`
- Create: `gitops/websites/darkbit/service.yaml`
- Create: `gitops/websites/darkbit/route.yaml`

- [ ] **Step 1: Copy the Apolline manifest shape with Darkbit identities.**

Use namespace `darkbit`, Deployment `website-deploy`, selector label `app: darkbit-web`, Service `darkbit-svc`, route `darkbit-route`, hostnames `darkbitapparel.com` and `www.darkbitapparel.com`, and the resolved `ghcr.io/jeff7712/darkbit:0.0.25` image digest. Preserve the same port, security context, and three `emptyDir` mounts as Apolline.

### Task 4: Add the DistroJeff website manifests

**Files:**
- Create: `gitops/websites/distrojeff/kustomization.yaml`
- Create: `gitops/websites/distrojeff/namespace.yaml`
- Create: `gitops/websites/distrojeff/deployment.yaml`
- Create: `gitops/websites/distrojeff/service.yaml`
- Create: `gitops/websites/distrojeff/route.yaml`

- [ ] **Step 1: Copy the shared manifest shape with DistroJeff identities.**

Use namespace `distrojeff`, Deployment `website-deploy`, selector label `app: distrojeff-web`, Service `distrojeff-site-svc`, route `distrojeff-site-route`, hostnames `distrojeff.com` and `www.distrojeff.com`, and the resolved `ghcr.io/jeff7712/distrojeff-site:0.0.22` image digest. Preserve the legacy 500m CPU/256Mi memory limits, 100m CPU/128Mi memory requests, port 8080, security context, and three `emptyDir` mounts.

### Task 5: Wire the websites into Flux

**Files:**
- Create: `gitops/websites/kustomization.yaml`
- Create: `gitops/clusters/homelab-01/websites.yaml`

- [ ] **Step 1: Define the aggregate Kustomization.**

`gitops/websites/kustomization.yaml` must list the three site directories:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - apolline
  - darkbit
  - distrojeff
```

- [ ] **Step 2: Define the Flux Kustomization.**

Create Flux Kustomization `websites` in `flux-system` with path `./gitops/websites`, `prune: true`, interval `10m`, source `GitRepository/flux-system`, dependency `ingress`, and health checks for `apps/v1 Deployment/website-deploy` in namespaces `apolline`, `darkbit`, and `distrojeff`.

### Task 6: Render and validate before deployment

- [ ] **Step 1: Render the aggregate manifests.**

Run:

```sh
nix develop ./flake -c kubectl kustomize gitops/websites > /tmp/homelab-websites.yaml
```

Expected: output contains three Namespaces, three Deployments, three Services, and three HTTPRoutes, with no deprecated Traefik or cert-manager resources.

- [ ] **Step 2: Validate rendered Kubernetes schemas.**

Run:

```sh
nix develop ./flake -c kubeconform -strict -ignore-missing-schemas /tmp/homelab-websites.yaml
```

Expected: validation succeeds.

- [ ] **Step 3: Run focused repository checks.**

Run:

```sh
nix develop ./flake -c yamllint gitops/websites gitops/clusters/homelab-01/websites.yaml
git diff --check
```

Expected: both commands succeed.

### Task 7: Review and commit the implementation

- [ ] **Step 1: Inspect the final diff and status.**

Run:

```sh
git status --short
git diff --stat
git diff --no-ext-diff -- gitops/websites gitops/clusters/homelab-01/websites.yaml
```

Confirm no unrelated user files are staged or modified by the implementation.

- [ ] **Step 2: Commit the website migration.**

```sh
git add gitops/websites gitops/clusters/homelab-01/websites.yaml
git commit -m "feat: migrate stateless websites"
```

### Task 8: Verify live reconciliation after authorized publication

- [ ] **Step 1: Confirm the Flux resource becomes ready.**

From `homelab-01` after the commit is available to Flux:

```sh
sudo -n k3s kubectl -n flux-system get kustomization websites
```

Expected: `READY=True` and the current Git revision.

- [ ] **Step 2: Verify workloads, endpoints, and routes.**

```sh
sudo -n k3s kubectl get pods,svc,endpoints,httproute -n apolline
sudo -n k3s kubectl get pods,svc,endpoints,httproute -n darkbit
sudo -n k3s kubectl get pods,svc,endpoints,httproute -n distrojeff
```

Expected: one ready pod and one ready endpoint per site, with each HTTPRoute accepted and programmed. Public Cloudflare reachability remains a separate external check.
