from __future__ import annotations

from ..canonical import canonical_hash, strip_volatile
from ..client import HomeAssistantClient
from ..models import OwnerMode, PlanAction, ResourceDocument
from .base import BaseAdapter


class HelperAdapter(BaseAdapter):
    kind = "helper"
    owner_mode = OwnerMode.OBSERVE_ONLY.value
    supports_mutation = False

    def export_from_live(self, client: HomeAssistantClient) -> list[ResourceDocument]:
        # Helpers are surfaced in entity registry under input_boolean, input_number, etc.
        docs: list[ResourceDocument] = []
        entities = client.list_entities()
        helper_domains = (
            "input_boolean.",
            "input_number.",
            "input_text.",
            "input_select.",
            "input_datetime.",
            "counter.",
            "timer.",
        )
        for ent in entities:
            entity_id = ent.get("entity_id", "")
            for dom in helper_domains:
                if entity_id.startswith(dom):
                    key = entity_id.replace(".", "_")
                    desired = {
                        "entity_id": entity_id,
                        "name": ent.get("name"),
                        "icon": ent.get("icon"),
                    }
                    docs.append(
                        ResourceDocument(
                            kind=self.kind,
                            key=key,
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
            return ["Helper configuration must be a mapping"]
        if "entity_id" not in doc.desired:
            return ["Helper missing required 'entity_id'"]
        return []

    def apply(self, client: HomeAssistantClient, action: PlanAction) -> None:
        raise NotImplementedError(
            f"Mutations are not supported for observe-only helper resource '{action.key}'. "
            "Helper configuration settings are observe-only via this adapter."
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
            f"Deletions are not supported for observe-only helper resource '{key}'."
        )
