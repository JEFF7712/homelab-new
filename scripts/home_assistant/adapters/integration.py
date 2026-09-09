from __future__ import annotations

from ..canonical import strip_volatile
from ..client import HomeAssistantClient
from ..models import OwnerMode, PlanAction, ResourceDocument
from .base import BaseAdapter


class IntegrationAdapter(BaseAdapter):
    kind = "integration"
    owner_mode = OwnerMode.OBSERVE_ONLY.value

    def export_from_live(self, client: HomeAssistantClient) -> list[ResourceDocument]:
        entries = client.list_config_entries()
        docs: list[ResourceDocument] = []
        for entry in entries:
            entry_id = entry.get("entry_id")
            domain = entry.get("domain")
            if not entry_id or not domain:
                continue
            # Keep only nonsecret observe-only options
            desired = {
                "entry_id": entry_id,
                "domain": domain,
                "title": entry.get("title"),
                "source": entry.get("source"),
                "disabled_by": entry.get("disabled_by"),
                "pref_disable_new_entities": entry.get("pref_disable_new_entities"),
                "pref_disable_polling": entry.get("pref_disable_polling"),
            }
            docs.append(
                ResourceDocument(
                    kind=self.kind,
                    key=f"{domain}_{entry_id[:8]}",
                    owner_mode=self.owner_mode,
                    desired=desired,
                )
            )
        return docs

    def canonicalize(self, doc: ResourceDocument) -> ResourceDocument:
        clean = strip_volatile(doc.desired)
        return ResourceDocument(
            schema_version=doc.schema_version,
            kind=self.kind,
            key=doc.key,
            owner_mode=self.owner_mode,
            desired=clean,
        )

    def validate(self, doc: ResourceDocument) -> list[str]:
        if not isinstance(doc.desired, dict):
            return ["Integration configuration must be a mapping"]
        if "domain" not in doc.desired:
            return ["Integration missing required 'domain'"]
        return []

    def apply(self, client: HomeAssistantClient, action: PlanAction) -> None:
        # Integrations are observe-only
        pass

    def verify(self, client: HomeAssistantClient, doc: ResourceDocument) -> bool:
        return True

    def delete(self, client: HomeAssistantClient, key: str) -> None:
        pass
