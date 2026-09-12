from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from scripts.home_assistant.canonical import parse_yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
HA_DIR = REPO_ROOT / "home-assistant"
NODE_RED_DIR = HA_DIR / "node-red"
CORE_CONFIG = HA_DIR / "core" / "configuration.yaml"
GITOPS_HA_DIR = REPO_ROOT / "gitops" / "home-assistant"


def _load_yaml(path: Path):
    return parse_yaml(path.read_text(encoding="utf-8"))


def _load_yaml_multi(path: Path) -> list:
    """Parse a multi-document YAML file with HA !include / !secret tags."""
    out = []
    raw = path.read_text(encoding="utf-8")
    for chunk in re.split(r"^---\s*\n", raw, flags=re.MULTILINE):
        if not chunk.strip():
            continue
        out.append(parse_yaml(chunk))
    return out


def _strip_indent(text: str, prefix: str) -> str:
    """Strip a leading literal-block indent prefix from each line."""
    out_lines = []
    for line in text.splitlines():
        if line.startswith(prefix):
            out_lines.append(line[len(prefix) :])
        elif line.strip() == "":
            out_lines.append("")
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


class TestNodeRedSeeds(unittest.TestCase):
    def test_flows_json_parses(self) -> None:
        data = json.loads((NODE_RED_DIR / "flows.json").read_text(encoding="utf-8"))
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
        for entry in data:
            self.assertIn("id", entry)
            self.assertIn("type", entry)

    def test_settings_template_uses_envsubst_placeholders(self) -> None:
        raw = (NODE_RED_DIR / "settings.js.tpl").read_text(encoding="utf-8")
        for placeholder in (
            "${NODERED_CREDENTIAL_SECRET}",
            "${NODERED_ADMIN_USERNAME}",
            "${NODERED_ADMIN_PASSWORD_HASH}",
        ):
            self.assertIn(placeholder, raw, f"missing placeholder: {placeholder}")
        self.assertIn("flowFile: 'flows.json'", raw)
        self.assertIn("adminAuth", raw)

    def test_settings_template_executable_is_module_exports(self) -> None:
        raw = (NODE_RED_DIR / "settings.js.tpl").read_text(encoding="utf-8")
        self.assertRegex(raw, r"module\.exports\s*=")


class TestNodeRedConfigMapParity(unittest.TestCase):
    def setUp(self) -> None:
        self.cm = _load_yaml(GITOPS_HA_DIR / "nodered-config.yaml")
        self.cm_data = self.cm["data"]

    def test_configmap_has_seed_keys(self) -> None:
        self.assertIn("flows.json", self.cm_data)
        self.assertIn("settings.js.tpl", self.cm_data)

    def test_flows_data_matches_canonical(self) -> None:
        cm_flows = json.loads(self.cm_data["flows.json"])
        canonical = json.loads(
            (NODE_RED_DIR / "flows.json").read_text(encoding="utf-8")
        )
        self.assertEqual(cm_flows, canonical)

    def test_settings_data_matches_canonical(self) -> None:
        canonical = (NODE_RED_DIR / "settings.js.tpl").read_text(encoding="utf-8")
        cm_value = self.cm_data["settings.js.tpl"]
        # YAML `|` block scalar drops the trailing newline; canonical file has one.
        self.assertEqual(cm_value.rstrip("\n"), canonical.rstrip("\n"))


class TestHomeAssistantNoderedIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.core_cfg = _load_yaml(CORE_CONFIG)
        self.gitoos_cfg = _load_yaml(GITOPS_HA_DIR / "config.yaml")
        # The gitops ConfigMap embeds configuration.yaml under data.configuration.yaml.
        embedded = self.gitoos_cfg["data"]["configuration.yaml"]
        self.gitoops_inline_cfg = parse_yaml(embedded)

    def test_core_config_has_nodered_block(self) -> None:
        self.assertIn("nodered", self.core_cfg)
        link = self.core_cfg["nodered"]["http_link"]
        self.assertIn("url", link)
        self.assertIn("username", link)
        self.assertIn("password", link)

    def test_gitops_config_mirrors_core_config(self) -> None:
        self.assertEqual(self.gitoops_inline_cfg, self.core_cfg)


class TestGitopsNodeRedManifests(unittest.TestCase):
    def setUp(self) -> None:
        self.secrets = _load_yaml(GITOPS_HA_DIR / "nodered-secrets.yaml")
        self.volume = _load_yaml(GITOPS_HA_DIR / "nodered-volume.yaml")
        self.docs = _load_yaml_multi(GITOPS_HA_DIR / "nodered-deployment.yaml")
        self.deployment = next(d for d in self.docs if d.get("kind") == "Deployment")
        self.kustomization = _load_yaml(GITOPS_HA_DIR / "kustomization.yaml")

    def test_kustomization_includes_nodered_resources(self) -> None:
        for required in (
            "nodered-secrets.yaml",
            "nodered-volume.yaml",
            "nodered-config.yaml",
            "nodered-deployment.yaml",
        ):
            self.assertIn(
                required,
                self.kustomization["resources"],
                f"kustomization missing {required}",
            )

    def test_external_secret_has_required_keys(self) -> None:
        data = self.secrets["spec"]["data"]
        keys = {entry["secretKey"] for entry in data}
        self.assertSetEqual(
            keys,
            {"admin-username", "admin-password-hash", "credential-secret"},
        )
        # nodered-secrets template stores raw opaque keys; the rendered
        # HA secrets.yaml lives in the home-assistant-secrets ExternalSecret.
        template_type = self.secrets["spec"]["target"]["template"].get("type")
        self.assertEqual(template_type, "Opaque")

    def test_volume_uses_nfs_cluster(self) -> None:
        self.assertEqual(self.volume["spec"]["storageClassName"], "nfs-cluster")
        self.assertEqual(self.volume["metadata"]["name"], "nodered-data")
        self.assertEqual(self.volume["spec"]["accessModes"], ["ReadWriteMany"])

    def test_deployment_has_init_container_for_rendering(self) -> None:
        pod_spec = self.deployment["spec"]["template"]["spec"]
        init_names = {c["name"] for c in pod_spec["initContainers"]}
        self.assertIn("render-settings", init_names)
        init = next(
            c for c in pod_spec["initContainers"] if c["name"] == "render-settings"
        )
        env_names = {e["name"] for e in init["env"]}
        self.assertSetEqual(
            env_names,
            {
                "NODERED_CREDENTIAL_SECRET",
                "NODERED_ADMIN_USERNAME",
                "NODERED_ADMIN_PASSWORD_HASH",
            },
        )
        for env_entry in init["env"]:
            self.assertIn("valueFrom", env_entry, "init env must come from secret")
            self.assertEqual(
                env_entry["valueFrom"]["secretKeyRef"]["name"], "nodered-secrets"
            )

    def test_deployment_mounts_seed_and_data(self) -> None:
        pod_spec = self.deployment["spec"]["template"]["spec"]
        main_container = next(
            c for c in pod_spec["containers"] if c["name"] == "nodered"
        )
        mount_names = {v["name"] for v in main_container["volumeMounts"]}
        self.assertSetEqual(mount_names, {"data", "tmp"})

        volumes = {v["name"]: v for v in pod_spec["volumes"]}
        self.assertIn("data", volumes)
        self.assertEqual(
            volumes["data"]["persistentVolumeClaim"]["claimName"], "nodered-data"
        )
        self.assertIn("seed", volumes)
        self.assertEqual(volumes["seed"]["configMap"]["name"], "nodered-seed")

    def test_deployment_image_is_registry_pinned(self) -> None:
        main_container = next(
            c
            for c in self.deployment["spec"]["template"]["spec"]["containers"]
            if c["name"] == "nodered"
        )
        image = main_container["image"]
        self.assertTrue(image.startswith("registry.rupan.dev/"))
        self.assertIn("@sha256:", image, "image must be digest pinned")

    def test_service_advertises_via_bgp(self) -> None:
        service_doc = next(d for d in self.docs if d.get("kind") == "Service")
        self.assertEqual(service_doc["spec"]["type"], "LoadBalancer")
        self.assertEqual(
            service_doc["spec"]["loadBalancerClass"],
            "io.cilium/bgp-control-plane",
        )
        self.assertEqual(service_doc["spec"]["ports"][0]["port"], 1880)


class TestHomeAssistantSecretsHasNoderedCreds(unittest.TestCase):
    def test_secrets_yaml_template_has_nodered_keys(self) -> None:
        secrets = _load_yaml(GITOPS_HA_DIR / "secrets.yaml")
        template_data = secrets["spec"]["target"]["template"]["data"]
        secrets_yaml = template_data["secrets.yaml"]
        # nodered_url is a literal in-cluster URL; credentials are templated.
        self.assertIn("nodered_url:", secrets_yaml)
        for required_placeholder in (
            "{{ .nodered_username }}",
            "{{ .nodered_password }}",
        ):
            self.assertIn(
                required_placeholder,
                secrets_yaml,
                f"missing placeholder {required_placeholder}",
            )
        for required_key in ("nodered_username", "nodered_password"):
            self.assertIn(required_key, secrets_yaml)
        data_keys = {entry["secretKey"] for entry in secrets["spec"]["data"]}
        self.assertIn("nodered_username", data_keys)
        self.assertIn("nodered_password", data_keys)


class TestFluxKustomizationHealthChecks(unittest.TestCase):
    def test_home_assistant_kustomization_health_checks_nodered(self) -> None:
        path = REPO_ROOT / "gitops" / "clusters" / "homelab-01" / "home-assistant.yaml"
        doc = _load_yaml(path)
        checks = doc["spec"]["healthChecks"]
        nodered_checks = [hc for hc in checks if hc.get("name") == "nodered"]
        self.assertEqual(len(nodered_checks), 1)
        hc = nodered_checks[0]
        self.assertEqual(hc["kind"], "Deployment")
        self.assertEqual(hc["namespace"], "home-assistant")


if __name__ == "__main__":
    unittest.main()
