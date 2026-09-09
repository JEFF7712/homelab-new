from __future__ import annotations

from ..canonical import canonical_hash, strip_volatile
from ..client import HomeAssistantClient, HomeAssistantNotFoundError
from ..models import ActionType, OwnerMode, PlanAction, ResourceDocument
from .base import BaseAdapter


class ScriptAdapter(BaseAdapter):
    kind = "script"
    owner_mode = OwnerMode.UI_EDITABLE.value

    def export_from_live(self, client: HomeAssistantClient) -> list[ResourceDocument]:
        docs: list[ResourceDocument] = []
        entities = client.list_entities()
        for ent in entities:
            entity_id = ent.get("entity_id", "")
            if entity_id.startswith("script."):
                unique_id = ent.get("unique_id")
                script_key = unique_id or entity_id.removeprefix("script.")
                try:
                    config = client.get_script(script_key)
                    docs.append(
                        ResourceDocument(
                            kind=self.kind,
                            key=script_key,
                            owner_mode=self.owner_mode,
                            desired=config,
                            metadata={"entity_id": entity_id},
                        )
                    )
                except HomeAssistantNotFoundError:
                    continue
        return docs

    def canonicalize(self, doc: ResourceDocument) -> ResourceDocument:
        clean_desired = strip_volatile(doc.desired)
        return ResourceDocument(
            schema_version=doc.schema_version,
            kind=self.kind,
            key=doc.key,
            owner_mode=self.owner_mode,
            desired=clean_desired,
            metadata=dict(doc.metadata),
        )

    def validate(self, doc: ResourceDocument) -> list[str]:
        errors: list[str] = []
        if not isinstance(doc.desired, dict):
            return ["Script configuration must be a mapping"]
        has_sequence = (
            "sequence" in doc.desired
            or "action" in doc.desired
            or "actions" in doc.desired
        )
        if not has_sequence:
            errors.append("Script missing required 'sequence' or 'actions' field")
        return errors

    def apply(self, client: HomeAssistantClient, action: PlanAction) -> None:
        if action.action in (ActionType.CREATE, ActionType.UPDATE):
            if not isinstance(action.after, dict):
                raise ValueError(
                    f"Cannot apply script {action.key}: payload must be a dict"
                )
            client.save_script(action.key, action.after)
        elif action.action == ActionType.DELETE:
            client.delete_script(action.key)

    def verify(self, client: HomeAssistantClient, doc: ResourceDocument) -> bool:
        try:
            live = client.get_script(doc.key)
            return canonical_hash(live) == canonical_hash(doc.desired)
        except HomeAssistantNotFoundError:
            return False

    def delete(self, client: HomeAssistantClient, key: str) -> None:
        client.delete_script(key)
