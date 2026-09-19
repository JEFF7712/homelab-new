from __future__ import annotations

from ..canonical import canonical_hash, strip_volatile
from ..client import HomeAssistantClient
from ..models import ActionType, OwnerMode, PlanAction, ResourceDocument
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
                        "name": ent.get("name") or ent.get("original_name"),
                        "icon": ent.get("icon") or ent.get("original_icon"),
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
        if action.action == ActionType.UPDATE:
            after = action.after
            if not isinstance(after, dict):
                raise ValueError(
                    f"Cannot apply helper {action.key}: payload must be a dict"
                )
            entity_id = after.get("entity_id")
            if not entity_id:
                raise ValueError(
                    f"Cannot apply helper {action.key}: payload missing 'entity_id'"
                )
            client.update_entity(
                entity_id, name=after.get("name"), icon=after.get("icon")
            )
        elif action.action == ActionType.CREATE:
            raise NotImplementedError(
                f"Cannot create helper '{action.key}': the entity registry cannot "
                "create helpers. Create it in the Home Assistant UI, then adopt "
                "it into Git."
            )
        elif action.action == ActionType.DELETE:
            raise NotImplementedError(
                f"Cannot delete helper '{action.key}': removing the registry entry "
                "does not delete the helper. Delete it in the Home Assistant UI, "
                "then adopt the deletion."
            )
        else:
            raise ValueError(
                f"Unknown action '{action.action}' for helper {action.key}"
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
            f"Cannot delete helper '{key}': removing the registry entry does not "
            "delete the helper. Delete it in the Home Assistant UI, then adopt "
            "the deletion."
        )
