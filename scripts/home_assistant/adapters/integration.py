from __future__ import annotations

from ..canonical import canonical_hash, strip_volatile
from ..client import HomeAssistantClient
from ..models import OwnerMode, PlanAction, ResourceDocument
from .base import BaseAdapter


class IntegrationAdapter(BaseAdapter):
    kind = "integration"
    owner_mode = OwnerMode.OBSERVE_ONLY.value
    supports_mutation = False

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
        raise NotImplementedError(
            f"Mutations are not supported for observe-only integration '{action.key}'."
        )

    def verify(self, client: HomeAssistantClient, doc: ResourceDocument) -> bool:
        live_docs = {d.key: self.canonicalize(d) for d in self.export_from_live(client)}
        live_doc = live_docs.get(doc.key)
        if live_doc is None or live_doc.desired is None:
            return False
        return canonical_hash(live_doc.desired) == canonical_hash(
            self.canonicalize(doc).desired
        )

    def delete(self, client: HomeAssistantClient, key: str) -> None:
        raise NotImplementedError(
            f"Deletions are not supported for observe-only integration '{key}'."
        )
