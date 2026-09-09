from __future__ import annotations

from ..canonical import canonical_hash, strip_volatile
from ..client import HomeAssistantClient, HomeAssistantNotFoundError
from ..models import ActionType, OwnerMode, PlanAction, ResourceDocument
from .base import BaseAdapter


class AutomationAdapter(BaseAdapter):
    kind = "automation"
    owner_mode = OwnerMode.UI_EDITABLE.value

    def export_from_live(self, client: HomeAssistantClient) -> list[ResourceDocument]:
        docs: list[ResourceDocument] = []
        seen: set[str] = set()
        for auto in client.list_automations():
            auto_id = auto.get("id")
            if not auto_id:
                continue
            auto_id_str = str(auto_id)
            seen.add(auto_id_str)
            docs.append(
                ResourceDocument(
                    kind=self.kind,
                    key=auto_id_str,
                    owner_mode=self.owner_mode,
                    desired=auto,
                )
            )
        try:
            for ent in client.list_entities():
                entity_id = ent.get("entity_id", "")
                if entity_id.startswith("automation."):
                    auto_id = ent.get("unique_id") or entity_id.removeprefix(
                        "automation."
                    )
                    if auto_id in seen:
                        continue
                    seen.add(auto_id)
                    try:
                        cfg = client.get_automation(auto_id)
                        docs.append(
                            ResourceDocument(
                                kind=self.kind,
                                key=auto_id,
                                owner_mode=self.owner_mode,
                                desired=cfg,
                                metadata={"entity_id": entity_id},
                            )
                        )
                    except HomeAssistantNotFoundError:
                        continue
        except Exception:
            pass
        return docs

    def canonicalize(self, doc: ResourceDocument) -> ResourceDocument:
        clean_desired = strip_volatile(doc.desired)
        if isinstance(clean_desired, dict):
            clean_desired = dict(clean_desired)
            if "trigger" in clean_desired and "triggers" not in clean_desired:
                clean_desired["triggers"] = clean_desired.pop("trigger")
            if "action" in clean_desired and "actions" not in clean_desired:
                clean_desired["actions"] = clean_desired.pop("action")
            if "condition" in clean_desired and "conditions" not in clean_desired:
                clean_desired["conditions"] = clean_desired.pop("condition")
            if "id" not in clean_desired and doc.key:
                clean_desired["id"] = doc.key
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
            return ["Automation configuration must be a mapping"]
        if "id" not in doc.desired and doc.key:
            doc.desired["id"] = doc.key
        if not doc.desired.get("alias"):
            errors.append("Automation missing required 'alias' field")
        has_trigger = "triggers" in doc.desired or "trigger" in doc.desired
        if not has_trigger:
            errors.append("Automation missing required 'trigger' or 'triggers' field")
        has_action = "actions" in doc.desired or "action" in doc.desired
        if not has_action:
            errors.append("Automation missing required 'action' or 'actions' field")
        return errors

    def apply(self, client: HomeAssistantClient, action: PlanAction) -> None:
        if action.action in (ActionType.CREATE, ActionType.UPDATE):
            if not isinstance(action.after, dict):
                raise ValueError(
                    f"Cannot apply automation {action.key}: payload must be a dict"
                )
            payload = dict(action.after)
            payload["id"] = action.key
            client.save_automation(action.key, payload)
        elif action.action == ActionType.DELETE:
            client.delete_automation(action.key)

    def verify(self, client: HomeAssistantClient, doc: ResourceDocument) -> bool:
        try:
            live = client.get_automation(doc.key)
            clean_live = self.canonicalize(
                ResourceDocument(kind=self.kind, key=doc.key, desired=live)
            ).desired
            clean_desired = self.canonicalize(doc).desired
            return canonical_hash(clean_live) == canonical_hash(clean_desired)
        except HomeAssistantNotFoundError:
            return False

    def delete(self, client: HomeAssistantClient, key: str) -> None:
        client.delete_automation(key)
