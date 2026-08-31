# OPNsense Control Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Safely import the running OPNsense configuration, establish a read-only evidence baseline, and add a CI-only reconciler for the approved VLAN, DHCP, DNS, firewall, and BGP design.

**Architecture:** OpenTofu owns provider-supported VLAN, Kea DHCP, Unbound, and firewall resources after UUID import. A typed Python reconciler owns only interface assignments and FRR global BGP state, using feature detection and read-after-write proofs. All API credentials and downloaded firewall exports remain outside Git.

**Tech Stack:** Python 3 standard library HTTP client, OpenTofu, browningluke/opnsense provider 0.26.0, OPNsense API, SOPS.

---

## File structure

- opnsense-reconciler/opnsense_reconciler/client.py: authenticated JSON client with certificate verification.
- opnsense-reconciler/opnsense_reconciler/inventory.py: backup and GET-only inventory operations.
- opnsense-reconciler/opnsense_reconciler/reconcile.py: feature-gated interface and FRR convergence.
- opnsense-reconciler/tests/: HTTP fixture contract tests.
- tofu/opnsense/: pinned provider, import blocks, and provider-managed declarations.
- docs/runbooks/opnsense-recovery.md: console recovery and rollback procedure.

### Task 1: Establish read-only firewall evidence

**Files:**
- Create: opnsense-reconciler/opnsense_reconciler/inventory.py
- Create: opnsense-reconciler/tests/test_inventory.py
- Create: docs/runbooks/opnsense-recovery.md

- [ ] **Step 1: Write the failing inventory contract test**

The test must use a fake transport and assert this exact read-only sequence:

~~~python
assert transport.calls == [
    ("GET", "/api/core/backup/providers"),
    ("GET", "/api/core/backup/backups/this"),
    ("GET", "/api/interfaces/overview/interfaces_info/true"),
    ("GET", "/api/interfaces/vlan_settings/search_item"),
    ("GET", "/api/interfaces/assignment/search_item"),
]
~~~

- [ ] **Step 2: Run the test and confirm it fails because collect_inventory is absent**

Run: nix develop ./flake -c python -m unittest opnsense-reconciler/tests/test_inventory.py -v

Expected: FAIL with ImportError for collect_inventory.

- [ ] **Step 3: Implement the GET-only collector**

Implement collect_inventory so it discovers the local backup provider rather than assuming this, downloads the newest returned backup by exact ID, computes SHA-256, and stores it only in the CI artifact directory. It must issue the assignment endpoint probe last and return assignment_api_available false on HTTP 404 or 403.

- [ ] **Step 4: Re-run the unit test**

Run: nix develop ./flake -c python -m unittest opnsense-reconciler/tests/test_inventory.py -v

Expected: PASS. No POST, PUT, PATCH, or DELETE call is present in the fake transport trace.

- [ ] **Step 5: Run the live read-only inventory**

Run from a GitLab protected CI job with OPNSENSE_URL, OPNSENSE_API_KEY, OPNSENSE_API_SECRET, and OPNSENSE_CA_PEM supplied as masked variables:

~~~bash
python -m opnsense_reconciler.inventory --artifact-dir "$CI_PROJECT_DIR/artifacts/opnsense"
~~~

Expected: an encrypted config export, its SHA-256, runtime interface inventory, VLAN inventory, and assignment API availability result. The job fails if TLS verification or any GET response fails.

### Task 2: Add feature-gated interface reconciliation

**Files:**
- Create: opnsense-reconciler/opnsense_reconciler/reconcile.py
- Create: opnsense-reconciler/tests/test_reconcile.py

- [ ] **Step 1: Write the failing feature-gate test**

~~~python
with self.assertRaisesRegex(RuntimeError, "assignment API unavailable"):
    reconcile_interfaces(
        client=client,
        assignment_api_available=False,
        desired_interfaces=[],
    )
self.assertEqual(client.calls, [])
~~~

- [ ] **Step 2: Run the test and confirm it fails because reconcile_interfaces is absent**

Run: nix develop ./flake -c python -m unittest opnsense-reconciler/tests/test_reconcile.py -v

Expected: FAIL with ImportError for reconcile_interfaces.

- [ ] **Step 3: Implement one coherent interface transaction**

The reconciler must read current assignment records, compare canonical desired records, POST add_item or set_item only for changed interfaces, call POST reconfigure exactly once, then verify assigned device, IPv4 CIDR, route, and management reachability. It must refuse a transaction that changes the management interface and every other LAN interface together.

- [ ] **Step 4: Re-run the test suite**

Run: nix develop ./flake -c python -m unittest discover -s opnsense-reconciler/tests -v

Expected: PASS for unavailable API, no-op, changed-interface, and unsafe-management-transaction tests.

### Task 3: Import provider-backed OPNsense objects

**Files:**
- Create: tofu/opnsense/providers.tf
- Create: tofu/opnsense/variables.tf
- Create: tofu/opnsense/network.tf
- Create: tofu/opnsense/imports.tf

- [ ] **Step 1: Write the failing static contract test**

The test must assert that network.tf contains resources named opnsense_interfaces_vlan, opnsense_kea_dhcpv4_subnet, opnsense_kea_dhcpv4_reservation, opnsense_firewall_filter, opnsense_unbound_settings, and opnsense_unbound_forward.

- [ ] **Step 2: Run the test and confirm it fails because network.tf is absent**

Run: nix develop ./flake -c python -m unittest opnsense-reconciler/tests/test_tofu_contract.py -v

Expected: FAIL with FileNotFoundError for tofu/opnsense/network.tf.

- [ ] **Step 3: Declare imports from the read-only UUID inventory**

Use import blocks only with UUIDs emitted by Task 1. Import Unbound settings using the literal ID unbound_settings. Set Kea auto_collect to false for any managed DNS or router option. Preserve firewall sequence numbers during import.

- [ ] **Step 4: Validate without applying**

Run:

~~~bash
cd tofu/opnsense
tofu init -backend=false
tofu validate
tofu plan -refresh-only -out=refresh-only.tfplan
~~~

Expected: initialization and validation pass, and refresh-only plan contains no replacement of existing firewall rules.

### Task 4: Reconcile FRR BGP with runtime proof

**Files:**
- Modify: opnsense-reconciler/opnsense_reconciler/reconcile.py
- Modify: opnsense-reconciler/tests/test_reconcile.py
- Create: docs/runbooks/opnsense-bgp-proof.md

- [ ] **Step 1: Write the failing BGP proof test**

~~~python
result = verify_bgp(
    client,
    expected_peers={"10.0.30.11": 64512},
    expected_routes={"10.0.40.10/32"},
)
self.assertFalse(result.ready)
self.assertIn("10.0.40.10/32", result.missing_routes)
~~~

- [ ] **Step 2: Run the test and confirm it fails because verify_bgp is absent**

Run: nix develop ./flake -c python -m unittest opnsense-reconciler/tests/test_reconcile.py -v

Expected: FAIL with ImportError for verify_bgp.

- [ ] **Step 3: Implement FRR convergence and proof**

Manage GET and POST /api/quagga/bgp/get and set, neighbor UUID CRUD, and one POST /api/quagga/service/reconfigure. Require service status running, every intended bgpsummary peer established, matching neighbor ASNs, and each expected search_bgproute4 route before reporting readiness.

- [ ] **Step 4: Re-run the tests**

Run: nix develop ./flake -c python -m unittest discover -s opnsense-reconciler/tests -v

Expected: PASS for failed service, missing peer, missing route, and fully established BGP cases.

### Task 5: Add protected CI execution and recovery gates

**Files:**
- Modify: .gitlab-ci.yml
- Create: docs/runbooks/opnsense-recovery.md

- [ ] **Step 1: Add a failing CI contract test**

Assert that the pipeline contains separate opnsense_inventory, opnsense_plan, and opnsense_apply jobs, that only opnsense_apply is manual, and that its rules require main.

- [ ] **Step 2: Implement the CI stages**

Inventory is GET-only and stores encrypted artifacts. Plan runs OpenTofu refresh-only and desired-state plan. Apply is a manually triggered protected main-branch job that requires a successful inventory and plan artifact. It runs the reconciler backup and feature gate before any mutation, then records post-apply runtime proof.

- [ ] **Step 3: Validate locally**

Run:

~~~bash
nix develop ./flake -c python -m unittest discover -s tests -v
nix develop ./flake -c yamllint .gitlab-ci.yml
nix develop ./flake -c gitleaks detect --source . --redact
~~~

Expected: all commands exit 0.

## Final acceptance

- [ ] The first live job produces only read-only evidence and an encrypted configuration export.
- [ ] No apply is enabled until the installed firewall exposes the assignment API, the console recovery path is recorded, and OpenTofu imports produce a refresh-only plan with no unexpected replacement.
- [ ] The first BGP apply proves all Cilium peers established and its canary LoadBalancer route present before application traffic is migrated.

