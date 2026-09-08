from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from collections import Counter
from pathlib import Path
from typing import Any, ClassVar

import yaml

ROOT = Path(__file__).resolve().parents[1]
GITOPS = ROOT / "gitops"
INVENTORY = GITOPS / "registry-cutover" / "consumer-inventory.yaml"
DIGEST = re.compile(r"@sha256:([0-9a-f]{64})$")


def documents(path: Path) -> list[dict[str, Any]]:
    return [
        document
        for document in yaml.safe_load_all(path.read_text())
        if isinstance(document, dict)
    ]


def images(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "image" and isinstance(child, str):
                found.append(child)
            found.extend(images(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(images(child))
    return found


def rendered_cutover() -> list[dict[str, Any]]:
    rendered: list[dict[str, Any]] = []
    for overlay in sorted((GITOPS / "registry-cutover/components").iterdir()):
        if (
            overlay.name.endswith("-canary")
            or not (overlay / "kustomization.yaml").is_file()
        ):
            continue
        result = subprocess.run(
            ["kubectl", "kustomize", str(overlay)],
            check=True,
            capture_output=True,
            text=True,
        )
        rendered.extend(
            document
            for document in yaml.safe_load_all(result.stdout)
            if isinstance(document, dict)
        )
    return rendered


class RegistryConsumerInventoryTests(unittest.TestCase):
    inventory: ClassVar[dict[str, Any]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory = documents(INVENTORY)[0]["spec"]

    def test_inventory_covers_every_direct_gitops_image(self) -> None:
        discovered: Counter[tuple[str, str]] = Counter()
        for path in sorted(GITOPS.rglob("*.yaml")):
            if "registry-cutover" in path.parts:
                continue
            relative = str(path.relative_to(ROOT))
            for document in documents(path):
                discovered.update((relative, image) for image in images(document))

        inventoried = Counter(
            (entry["file"], entry["source"])
            for entry in self.inventory["directManifests"]
        )
        self.assertEqual(discovered, inventoried)

    def test_prepared_direct_mappings_preserve_existing_digests(self) -> None:
        prepared = [
            entry
            for entry in self.inventory["directManifests"]
            if entry["state"] == "prepared"
        ]
        self.assertTrue(prepared)
        for entry in prepared:
            source_digest = DIGEST.search(entry["source"])
            destination_digest = DIGEST.search(entry["destination"])
            if destination_digest is None:
                self.fail(f"prepared mapping lacks a digest: {entry}")
            if source_digest is not None:
                self.assertEqual(source_digest.group(1), destination_digest.group(1))
            self.assertTrue(entry["destination"].startswith("registry.rupan.dev/"))

        for entry in self.inventory["directManifests"]:
            if entry["state"] == "unresolved":
                self.assertIsNone(DIGEST.search(entry["source"]), entry)
                self.assertNotIn("@sha256:", entry["destination"])

    def test_direct_cutover_overlay_renders_only_verified_local_digests(self) -> None:
        rendered_images: list[str] = []
        for document in rendered_cutover():
            rendered_images.extend(images(document))

        expected = {
            entry["destination"]
            for entry in self.inventory["directManifests"]
            if entry["state"] == "prepared"
        }
        self.assertTrue(expected.issubset(set(rendered_images)))
        for image in rendered_images:
            if image.startswith("registry.rupan.dev/"):
                self.assertRegex(image, DIGEST)

        prepared_sources = {
            entry["source"]
            for entry in self.inventory["directManifests"]
            if entry["state"] == "prepared"
        }
        self.assertTrue(prepared_sources.isdisjoint(rendered_images))

    def test_stateless_canary_changes_only_apolline(self) -> None:
        result = subprocess.run(
            [
                "kubectl",
                "kustomize",
                str(GITOPS / "registry-cutover/components/websites-canary"),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        rendered_images = [
            image
            for document in yaml.safe_load_all(result.stdout)
            if isinstance(document, dict)
            for image in images(document)
        ]
        local = [
            image
            for image in rendered_images
            if image.startswith("registry.rupan.dev/")
        ]
        self.assertEqual(
            local,
            [
                "registry.rupan.dev/apps/apolline@sha256:"
                "3e60662d89254ab85ea9ab0a534d70922eee627a1de7b5b8cf08903435eb4c8a"
            ],
        )
        self.assertGreater(len(rendered_images), 1)

    def test_alloy_helm_overlay_uses_flux_digest_post_renderer(self) -> None:
        release = next(
            document
            for document in rendered_cutover()
            if document.get("kind") == "HelmRelease"
            and document["metadata"]["name"] == "alloy"
        )
        mappings = release["spec"]["postRenderers"][0]["kustomize"]["images"]
        config_reloader = next(
            image
            for image in mappings
            if image["name"] == "quay.io/prometheus-operator/prometheus-config-reloader"
        )
        self.assertEqual(
            config_reloader["newName"],
            "registry.rupan.dev/upstream/quay.io/prometheus-operator/prometheus-config-reloader",
        )
        self.assertRegex(f"@{config_reloader['digest']}", DIGEST)

    def test_monitoring_overlay_wires_nas_scrape_and_registry_alerts(self) -> None:
        rendered = rendered_cutover()
        release = next(
            document
            for document in rendered
            if document.get("kind") == "HelmRelease"
            and document["metadata"]["name"] == "kube-prometheus-stack"
        )
        scrape_configs = release["spec"]["values"]["prometheus"]["prometheusSpec"][
            "additionalScrapeConfigs"
        ]
        self.assertEqual(
            scrape_configs,
            [
                {
                    "job_name": "nas-01-node",
                    "static_configs": [
                        {"targets": ["10.0.30.20:9100"], "labels": {"host": "nas-01"}}
                    ],
                }
            ],
        )

        rule = next(
            document
            for document in rendered
            if document.get("kind") == "PrometheusRule"
        )
        self.assertEqual(rule["metadata"]["labels"]["release"], "kube-prometheus-stack")
        alerts = {
            item["alert"]: item["expr"]
            for group in rule["spec"]["groups"]
            for item in group["rules"]
        }
        self.assertEqual(
            set(alerts),
            {
                "RegistryExporterDown",
                "RegistryFilesystemPressure",
                "ZotUnitFailed",
                "RegistryTlsCertificateExpiring",
                "RegistryBackupStale",
            },
        )
        self.assertIn(
            'mountpoint="/tank/registry"', alerts["RegistryFilesystemPressure"]
        )
        self.assertIn('name="zot.service"', alerts["ZotUnitFailed"])
        self.assertIn(
            "homelab_zot_tls_certificate_expiry_timestamp_seconds",
            alerts["RegistryTlsCertificateExpiring"],
        )
        self.assertIn(
            "homelab_zot_backup_last_success_timestamp_seconds",
            alerts["RegistryBackupStale"],
        )

    def test_every_helm_release_has_versioned_generated_image_inventory(self) -> None:
        releases: dict[str, str] = {}
        for path in sorted(GITOPS.rglob("*.yaml")):
            if "registry-cutover" in path.parts:
                continue
            for release in documents(path):
                if release.get("kind") != "HelmRelease":
                    continue
                releases[release["metadata"]["name"]] = str(
                    release["spec"]["chart"]["spec"]["version"]
                )

        inventoried: dict[str, set[str]] = {}
        for entry in self.inventory["helmGenerated"]:
            self.assertTrue(entry["sources"], entry)
            self.assertEqual(len(entry["sources"]), len(entry["destinations"]), entry)
            self.assertTrue(
                all(
                    destination.startswith("registry.rupan.dev/upstream/")
                    for destination in entry["destinations"]
                ),
                entry,
            )
            self.assertTrue(entry["overridePaths"], entry)
            inventoried.setdefault(entry["release"], set()).add(
                str(entry["chartVersion"])
            )
            if entry["state"] == "prepared":
                self.assertTrue(
                    all(
                        DIGEST.search(destination)
                        for destination in entry["destinations"]
                    )
                )
                for source, destination in zip(
                    entry["sources"], entry["destinations"], strict=True
                ):
                    source_digest = DIGEST.search(source)
                    if source_digest is not None:
                        self.assertEqual(
                            source_digest.group(1), DIGEST.search(destination).group(1)
                        )
            else:
                self.assertTrue(
                    all(not DIGEST.search(source) for source in entry["sources"])
                )
                self.assertTrue(
                    all(
                        not DIGEST.search(destination)
                        for destination in entry["destinations"]
                    )
                )

        self.assertEqual(
            {name: {version} for name, version in releases.items()},
            inventoried,
        )

    def test_cutover_is_not_flux_active(self) -> None:
        self.assertFalse(self.inventory["activation"]["includedByFlux"])
        self.assertEqual(self.inventory["activation"]["state"], "prepared")
        self.assertEqual(
            self.inventory["activation"]["canaryPath"],
            "./gitops/registry-cutover/components/websites-canary",
        )
        active_files = [
            GITOPS / "clusters/homelab-01" / "kustomization.yaml",
            *sorted((GITOPS / "clusters/homelab-01").glob("*.yaml")),
        ]
        for path in active_files:
            if path.exists():
                self.assertNotIn("registry-cutover", path.read_text())

        active_local_references = []
        for path in sorted(GITOPS.rglob("*.yaml")):
            if "registry-cutover" not in path.parts:
                active_local_references.extend(
                    (path, image)
                    for document in documents(path)
                    for image in images(document)
                    if image.startswith("registry.rupan.dev/")
                )
        self.assertEqual(active_local_references, [])

    def test_bootstrap_exceptions_have_non_gitops_owners(self) -> None:
        exceptions = self.inventory["bootstrapExceptions"]
        self.assertEqual(
            {entry["id"] for entry in exceptions}, {"cilium", "k3s-runtime-images"}
        )
        for entry in exceptions:
            self.assertTrue(entry["owner"].startswith("flake/"))
            self.assertTrue(entry["reason"])

    def test_registry_node_rollout_is_explicit_and_serial(self) -> None:
        pipeline = yaml.safe_load((ROOT / ".gitlab-ci.yml").read_text())
        self.assertEqual(
            pipeline[".registry_ssh"]["before_script"][0],
            'export PATH="/run/current-system/sw/bin:$PATH"',
        )
        expected = [
            ("deploy_registry_node_01", "registry_import", "homelab-01"),
            ("deploy_registry_node_02", "deploy_registry_node_01", "homelab-02"),
            ("deploy_registry_node_03", "deploy_registry_node_02", "homelab-03"),
        ]
        for job_name, dependency, host in expected:
            job = pipeline[job_name]
            self.assertEqual(job["extends"], ".deploy_registry_node")
            self.assertEqual(job["needs"], [dependency])
            self.assertEqual(job["variables"]["DEPLOY_HOST"], host)
        self.assertEqual(
            pipeline[".deploy_registry_node"]["resource_group"],
            "registry-node-rollout",
        )
        importer = pipeline["registry_import"]
        self.assertEqual(importer["needs"], ["registry_lock"])
        importer_script = "\n".join(importer["script"])
        self.assertIn("getent ahostsv4 registry.rupan.dev", importer_script)
        self.assertIn("https://registry.rupan.dev/v2/", importer_script)

    @unittest.skipUnless(shutil.which("nix"), "nix is required for evaluated variants")
    def test_registry_variants_enable_local_only_runtime(self) -> None:
        expression = """
          let flake = builtins.getFlake (toString ./flake); in
          builtins.mapAttrs (_: configuration: {
            enable = configuration.config.homelab.k3s.registry.enable;
            enforce = configuration.config.homelab.k3s.registry.enforceLocalImages;
          }) {
            normal = flake.nixosConfigurations.homelab-01;
            registry = flake.nixosConfigurations.homelab-01-registry;
          }
        """
        result = subprocess.run(
            ["nix", "eval", "--impure", "--json", "--expr", expression],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        evaluated = json.loads(result.stdout)
        self.assertEqual(evaluated["normal"], {"enable": False, "enforce": False})
        self.assertEqual(evaluated["registry"], {"enable": True, "enforce": True})


if __name__ == "__main__":
    unittest.main()
