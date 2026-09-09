from __future__ import annotations

from ..canonical import canonical_hash
from ..client import HomeAssistantClient
from ..models import OwnerMode, PlanAction, ResourceDocument
from .base import BaseAdapter


class CoreConfigurationAdapter(BaseAdapter):
    kind = "core"
    owner_mode = OwnerMode.GIT_OWNED.value

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
        # Core configuration changes are deployed via Git/Flux/Kubernetes ConfigMap
        pass

    def verify(self, client: HomeAssistantClient, doc: ResourceDocument) -> bool:
        live_cfg = client.get_core_configuration()
        return canonical_hash(live_cfg) == canonical_hash(doc.desired)

    def delete(self, client: HomeAssistantClient, key: str) -> None:
        pass
