from __future__ import annotations

from ..canonical import canonical_hash, strip_volatile
from ..client import HomeAssistantClient, HomeAssistantNotFoundError
from ..models import ActionType, OwnerMode, PlanAction, ResourceDocument
from .base import BaseAdapter


class SceneAdapter(BaseAdapter):
    kind = "scene"
    owner_mode = OwnerMode.UI_EDITABLE.value

    def export_from_live(self, client: HomeAssistantClient) -> list[ResourceDocument]:
        docs: list[ResourceDocument] = []
        entities = client.list_entities()
        for ent in entities:
            entity_id = ent.get("entity_id", "")
            if entity_id.startswith("scene."):
                unique_id = ent.get("unique_id")
                scene_id = unique_id or entity_id.removeprefix("scene.")
                try:
                    config = client.get_scene(scene_id)
                    docs.append(
                        ResourceDocument(
                            kind=self.kind,
                            key=scene_id,
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
            return ["Scene configuration must be a mapping"]
        if not doc.desired.get("name"):
            errors.append("Scene missing required 'name' field")
        if "entities" not in doc.desired:
            errors.append("Scene missing required 'entities' field")
        return errors

    def apply(self, client: HomeAssistantClient, action: PlanAction) -> None:
        if action.action in (ActionType.CREATE, ActionType.UPDATE):
            if not isinstance(action.after, dict):
                raise ValueError(
                    f"Cannot apply scene {action.key}: payload must be a dict"
                )
            client.save_scene(action.key, action.after)
        elif action.action == ActionType.DELETE:
            client.delete_scene(action.key)

    def verify(self, client: HomeAssistantClient, doc: ResourceDocument) -> bool:
        try:
            live = client.get_scene(doc.key)
            return canonical_hash(live) == canonical_hash(doc.desired)
        except HomeAssistantNotFoundError:
            return False

    def delete(self, client: HomeAssistantClient, key: str) -> None:
        client.delete_scene(key)
