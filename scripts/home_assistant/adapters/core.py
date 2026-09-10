from __future__ import annotations

import hashlib
import re
from pathlib import Path

from ..canonical import canonical_hash
from ..client import HomeAssistantClient
from ..models import OwnerMode, PlanAction, ResourceDocument
from .base import BaseAdapter


def sync_core_to_gitops(repo_root: Path) -> None:
    """Synchronize home-assistant/core/configuration.yaml into gitops/home-assistant/config.yaml
    and recalculate checksum/config in gitops/home-assistant/deployment.yaml."""
    core_file = repo_root / "home-assistant" / "core" / "configuration.yaml"
    if not core_file.is_file():
        return
    core_content = core_file.read_text(encoding="utf-8")

    # Render into gitops ConfigMap
    config_cm_file = repo_root / "gitops" / "home-assistant" / "config.yaml"
    indented_lines = ["    " + line for line in core_content.splitlines()]
    indented_content = "\n".join(indented_lines) + "\n"
    cm_text = (
        "apiVersion: v1\n"
        "kind: ConfigMap\n"
        "metadata:\n"
        "  name: home-assistant-config\n"
        "  namespace: home-assistant\n"
        "data:\n"
        f"  configuration.yaml: |\n{indented_content}"
    )
    config_cm_file.write_text(cm_text, encoding="utf-8")

    # Update deployment checksum/config
    deployment_file = repo_root / "gitops" / "home-assistant" / "deployment.yaml"
    if deployment_file.is_file():
        checksum = hashlib.sha256(core_content.encode("utf-8")).hexdigest()
        dep_text = deployment_file.read_text(encoding="utf-8")
        dep_text = re.sub(
            r"checksum/config:\s*[a-f0-9]+",
            f"checksum/config: {checksum}",
            dep_text,
        )
        deployment_file.write_text(dep_text, encoding="utf-8")


class CoreConfigurationAdapter(BaseAdapter):
    kind = "core"
    owner_mode = OwnerMode.GIT_OWNED.value
    supports_mutation = False

    def export_from_live(self, client: HomeAssistantClient) -> list[ResourceDocument]:
        cfg = client.get_core_configuration()
        return [
            ResourceDocument(
                kind=self.kind,
                key="configuration",
                owner_mode=self.owner_mode,
                desired=cfg,
                metadata={"status": "live-probed"},
            )
        ]

    def canonicalize(self, doc: ResourceDocument) -> ResourceDocument:
        return doc

    def validate(self, doc: ResourceDocument) -> list[str]:
        errors: list[str] = []
        if not isinstance(doc.desired, dict):
            return ["Core configuration must be a mapping"]
        if "default_config" not in doc.desired and "homeassistant" not in doc.desired:
            errors.append(
                "Core configuration must include 'default_config' or 'homeassistant'"
            )
        return errors

    def apply(self, client: HomeAssistantClient, action: PlanAction) -> None:
        raise NotImplementedError(
            "Core configuration is git-owned and deployed via GitOps / Flux ConfigMap. "
            "Direct live API mutation is not supported for core configuration."
        )

    def verify(self, client: HomeAssistantClient, doc: ResourceDocument) -> bool:
        live_cfg = client.get_core_configuration()
        return canonical_hash(live_cfg) == canonical_hash(doc.desired)

    def delete(self, client: HomeAssistantClient, key: str) -> None:
        raise NotImplementedError("Core configuration cannot be deleted.")
