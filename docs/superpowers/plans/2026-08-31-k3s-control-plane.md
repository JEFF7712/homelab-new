# k3s Control Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Declare and validate a three-server NixOS k3s control plane that is ready for Cilium custom-CNI bootstrap without configuring any physical host.

**Architecture:** A reusable NixOS k3s-server module takes role-specific hostname, node IP, cluster-init, server endpoint, and token-file inputs. Three host profiles consume that module, use embedded etcd, disable flannel and built-in network policy, and expose no workload configuration. The first node performs cluster initialization; joining nodes use a runtime-provisioned token file. Cilium installation remains a separate GitOps workstream after the router VLAN 30 plan is reviewed.

**Tech Stack:** Nix flakes, NixOS modules, k3s, static evaluation tests.

---

### Task 1: Define the k3s server module contract

**Files:**
- Create: `flake/modules/k3s-server.nix`
- Create: `tests/test_k3s_module_contract.py`

- [x] **Step 1: Write the failing module contract test**

```python
module = (ROOT / "flake/modules/k3s-server.nix").read_text()
self.assertIn("--flannel-backend=none", module)
self.assertIn("--disable-network-policy", module)
self.assertIn("clusterInit", module)
self.assertIn("tokenFile", module)
```

- [x] **Step 2: Run the test and confirm it fails because the module is absent**

Run: `nix develop ./flake -c python -m unittest tests/test_k3s_module_contract.py -v`

Expected: `FileNotFoundError` for `flake/modules/k3s-server.nix`.

- [x] **Step 3: Implement the module**

```nix
{ lib, ... }:
{
  services.k3s = {
    enable = true;
    role = "server";
    clusterInit = cfg.clusterInit;
    tokenFile = cfg.tokenFile;
    serverAddr = lib.mkIf (cfg.serverAddress != null) cfg.serverAddress;
    extraFlags = [
      "--node-ip=${cfg.nodeIp}"
      "--advertise-address=${cfg.nodeIp}"
      "--flannel-backend=none"
      "--disable-network-policy"
    ];
  };
}
```

- [x] **Step 4: Re-run the test and commit**

Run: `nix develop ./flake -c python -m unittest tests/test_k3s_module_contract.py -v`

Commit: `feat: add k3s server module`

### Task 2: Add three role declarations

**Files:**
- Create: `flake/hosts/homelab-01/default.nix`
- Create: `flake/hosts/homelab-02/default.nix`
- Create: `flake/hosts/homelab-03/default.nix`

- [ ] **Step 1: Write the failing host-count test**

```python
for host in ("homelab-01", "homelab-02", "homelab-03"):
    profile = (ROOT / f"flake/hosts/{host}/default.nix").read_text()
    self.assertIn(f'networking.hostName = "{host}"', profile)
```

- [ ] **Step 2: Run and confirm failure**

Run: `nix develop ./flake -c python -m unittest tests/test_k3s_module_contract.py -v`

Expected: assertion failure for `homelab-01`.

- [ ] **Step 3: Add host profiles with no physical installation target**

```nix
{
  imports = [ ../../modules/k3s-server.nix ];
  networking.hostName = "homelab-01";
}
```

Repeat with `homelab-02` and `homelab-03`. The profiles carry the planned node addresses but are not `nixosConfigurations` until hardware and filesystem modules are captured from the actual servers. Add a static profile contract instead of pretending a generic NixOS evaluation is installable.

- [ ] **Step 4: Re-run static tests**

Run: `nix develop ./flake -c python -m unittest discover -s tests -v`

Expected: the three profiles satisfy the k3s control-plane contract without configuring a physical host.

- [ ] **Step 5: Commit**

Commit: `feat: declare three k3s servers`

### Task 3: Add Cilium bootstrap contract

**Files:**
- Create: `gitops/clusters/homelab-01/cilium/values.yaml`
- Create: `gitops/clusters/homelab-01/cilium/kustomization.yaml`
- Create: `gitops/tests/test_cilium_contract.py`

- [ ] **Step 1: Write the failing Cilium values test**

```python
values = (ROOT / "gitops/clusters/homelab-01/cilium/values.yaml").read_text()
self.assertIn("kubeProxyReplacement: true", values)
self.assertIn("bgpControlPlane:", values)
```

- [ ] **Step 2: Run and confirm the path is absent**

Run: `nix develop ./flake -c python -m unittest gitops/tests/test_cilium_contract.py -v`

Expected: `FileNotFoundError`.

- [ ] **Step 3: Add a Cilium values contract with no peer addresses**

```yaml
kubeProxyReplacement: true
bgpControlPlane:
  enabled: true
```

Use a kustomization that references only this values file. Do not add BGP peers until VLAN 30 nodes and OPNsense interface assignment are live.

- [ ] **Step 4: Run the test and YAML lint**

Run: `nix develop ./flake -c python -m unittest gitops/tests/test_cilium_contract.py -v && nix develop ./flake -c yamllint gitops`

- [ ] **Step 5: Commit**

Commit: `feat: add Cilium bootstrap contract`

### Task 4: Verify the isolated control-plane contract

**Files:**
- Modify: `.gitlab-ci.yml`

- [ ] **Step 1: Add a failing CI contract test that requires k3s and Cilium tests**

```python
pipeline = (ROOT / ".gitlab-ci.yml").read_text()
self.assertIn("test_k3s_module_contract", pipeline)
self.assertIn("test_cilium_contract", pipeline)
```

- [ ] **Step 2: Run and confirm failure**

Run: `nix develop ./flake -c python -m unittest discover -s tests -v`

Expected: assertion failure for `test_k3s_module_contract`.

- [ ] **Step 3: Add the tests to `repository_tests`**

```yaml
- nix develop ./flake -c python -m unittest discover -s tests -v
```

Place the new test directories under `tests/` so the existing discovery command executes them.

- [ ] **Step 4: Run the full repository verification**

Run: `nix develop ./flake -c python -m unittest discover -s tests -v && nix flake check ./flake && nix develop ./flake -c yamllint . && nix develop ./flake -c gitleaks detect --source . --redact`

- [ ] **Step 5: Commit**

Commit: `ci: validate k3s control plane contract`
