# OPNsense Bootstrap Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bootstrap persistent GitLab OpenTofu state and converge OPNsense on the final six-VLAN network using live VLAN device discovery.

**Architecture:** GitLab's HTTP backend stores and locks state for project `85910419` under state name `opnsense-production`. OpenTofu imports the existing VLAN 20 object and creates the other provider-backed resources. The Python reconciler maps desired parent and tag pairs to OPNsense-generated VLAN device names before applying explicit interface assignments.

**Tech Stack:** OpenTofu 1.9+, GitLab-managed OpenTofu state, browningluke/opnsense 0.26.0, Python 3.13, OPNsense 26.7 API.

---

### Task 1: Add persistent GitLab state

**Files:**
- Create: `tofu/opnsense/backend.tf`
- Modify: `.gitlab-ci.yml`
- Modify: `tests/test_repository_contract.py`

- [ ] **Step 1: Write the failing backend contract test**

Add a test that requires `backend "http" {}`, the `TF_HTTP_ADDRESS`, lock and unlock variables, and an `init -reconfigure` command without `-backend=false`.

- [ ] **Step 2: Run the contract test and confirm failure**

Run: `nix develop ./flake -c python -m unittest tests/test_repository_contract.py -v`

Expected: failure because `tofu/opnsense/backend.tf` is absent.

- [ ] **Step 3: Implement the backend and CI environment**

Create an empty HTTP backend block. Set `TF_STATE_NAME` to `opnsense-production`, derive the state and lock URLs from `CI_API_V4_URL` and `CI_PROJECT_ID`, authenticate as `gitlab-ci-token` with `CI_JOB_TOKEN`, and use POST and DELETE lock methods.

- [ ] **Step 4: Verify and commit**

Run: `nix develop ./flake -c python -m unittest tests/test_repository_contract.py -v && nix develop ./flake -c yamllint .gitlab-ci.yml`

Commit: `fix: persist OPNsense state in GitLab`

### Task 2: Make VLAN ownership import-safe

**Files:**
- Create: `tofu/opnsense/imports.tf`
- Modify: `tofu/opnsense/network.tf`
- Modify: `tofu/opnsense/variables.tf`
- Modify: `tofu/opnsense/homelab.auto.tfvars`
- Modify: `tests/test_opnsense_tofu_contract.py`

- [ ] **Step 1: Write the failing import contract test**

Require an import of `opnsense_interfaces_vlan.managed["clients"]` with ID `47cac540-15b6-4838-9de1-f7e8e7307d2b`. Require VLAN device names to be computed by the provider rather than supplied by variables.

- [ ] **Step 2: Run the test and confirm failure**

Run: `nix develop ./flake -c python -m unittest tests/test_opnsense_tofu_contract.py -v`

Expected: failure because `imports.tf` is absent and `device` remains configured.

- [ ] **Step 3: Implement import-safe VLAN declarations**

Add the exact VLAN 20 import block. Remove `device` from the VLAN variable type, resource arguments, and values. Keep parent, tag, and description as desired inputs.

- [ ] **Step 4: Validate and commit**

Run: `nix develop ./flake -c tofu -chdir=tofu/opnsense init -backend=false && nix develop ./flake -c tofu -chdir=tofu/opnsense validate && nix develop ./flake -c python -m unittest tests/test_opnsense_tofu_contract.py -v`

Commit: `fix: import existing OPNsense VLAN state`

### Task 3: Resolve generated VLAN devices

**Files:**
- Modify: `opnsense_reconciler/assignments.json`
- Modify: `opnsense_reconciler/reconcile.py`
- Modify: `tests/test_opnsense_reconcile.py`

- [ ] **Step 1: Write failing resolver tests**

Require desired assignments to use `parent` and numeric `tag`. Test that a live row containing `if = "igb0"`, `tag = "20"`, and `vlanif = "vlan01 [CLUSTER]"` resolves to device `vlan01`. Test that a missing desired tag refuses all writes.

- [ ] **Step 2: Run and confirm failure**

Run: `nix develop ./flake -c python -m unittest tests/test_opnsense_reconcile.py -v`

Expected: failure because assignments still contain hard-coded devices and the resolver is absent.

- [ ] **Step 3: Implement live resolution**

Read `/api/interfaces/vlan_settings/search_item`, index rows by physical parent and integer tag, strip the display suffix from `vlanif`, and inject the resolved device into the complete assignment record. Resolve every desired assignment before reading or writing assignment state.

- [ ] **Step 4: Verify and commit**

Run: `nix develop ./flake -c python -m unittest tests/test_opnsense_reconcile.py -v && nix develop ./flake -c pyright opnsense_reconciler tests`

Commit: `fix: resolve OPNsense VLAN device names`

### Task 4: Add executable reconciliation

**Files:**
- Modify: `opnsense_reconciler/inventory.py`
- Modify: `opnsense_reconciler/reconcile.py`
- Modify: `.gitlab-ci.yml`
- Modify: `tests/test_opnsense_reconcile.py`
- Modify: `tests/test_repository_contract.py`

- [ ] **Step 1: Write failing CLI and CI contract tests**

Require the reconciliation CLI to load `assignments.json`, use the protected OPNsense environment, and require the apply job to invoke it after `tofu apply`.

- [ ] **Step 2: Run and confirm failure**

Run: `nix develop ./flake -c python -m unittest tests/test_opnsense_reconcile.py tests/test_repository_contract.py -v`

Expected: failure because `reconcile.main` and the CI invocation are absent.

- [ ] **Step 3: Implement the CLI and CI ordering**

Reuse credential parsing and TLS-verified `HttpsClient`, add POST support, run OpenTofu first so all VLAN devices exist, then reconcile all six interface assignments.

- [ ] **Step 4: Verify and commit**

Run: `nix develop ./flake -c python -m unittest discover -s tests -v && nix flake check ./flake && nix develop ./flake -c gitleaks detect --source . --redact`

Commit: `feat: reconcile generated OPNsense interfaces`

### Task 5: Bootstrap and converge live state

**Files:**
- State: GitLab project `85910419`, state `opnsense-production`
- Evidence: ignored `artifacts/opnsense/`

- [ ] **Step 1: Initialize the GitLab HTTP backend without printing credentials**

Use `glab auth token` only through process substitution or environment assignment. Set `TF_HTTP_ADDRESS`, lock and unlock addresses, username `JEFF7712`, and the token in `TF_HTTP_PASSWORD`. Run `tofu init -reconfigure`.

- [ ] **Step 2: Import and inspect live provider state**

Run a refresh-only plan, then a desired plan. Inspect every create, update, destroy, and replacement. Do not apply if the plan replaces WAN or physical LAN ownership.

- [ ] **Step 3: Apply provider-backed desired state**

Apply the reviewed saved plan. Then run the interface reconciler with `opnsense_reconciler/assignments.json`.

- [ ] **Step 4: Configure switch VLAN membership**

Configure the OPNsense uplink as tagged VLANs 10, 20, 30, 40, 50, and 60. Assign host-facing ports and PVIDs to their final roles after discovering the live port map.

- [ ] **Step 5: Prove convergence**

Capture a fresh encrypted inventory, verify six VLAN tags and six gateway CIDRs, verify the management path and Internet path, and run a final plan that reports no provider-managed changes.
