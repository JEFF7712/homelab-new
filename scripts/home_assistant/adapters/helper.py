from __future__ import annotations

from ..canonical import strip_volatile
from ..client import HomeAssistantClient
from ..models import OwnerMode, PlanAction, ResourceDocument
from .base import BaseAdapter


class HelperAdapter(BaseAdapter):
    kind = "helper"
    owner_mode = OwnerMode.UI_EDITABLE.value

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
        pass

    def verify(self, client: HomeAssistantClient, doc: ResourceDocument) -> bool:
        return True

    def delete(self, client: HomeAssistantClient, key: str) -> None:
        pass
