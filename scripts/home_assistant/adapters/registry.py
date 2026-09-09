from __future__ import annotations

from typing import Any

from ..canonical import canonical_hash
from ..client import HomeAssistantClient
from ..models import ActionType, OwnerMode, PlanAction, ResourceDocument
from .base import BaseAdapter

ALLOWLISTED_AREA_FIELDS = ("area_id", "name", "icon", "floor_id", "aliases")
ALLOWLISTED_FLOOR_FIELDS = ("floor_id", "name", "level", "icon", "aliases")
ALLOWLISTED_LABEL_FIELDS = ("label_id", "name", "icon", "color", "description")
ALLOWLISTED_DEVICE_FIELDS = ("id", "name_by_user", "area_id", "disabled_by")
ALLOWLISTED_ENTITY_FIELDS = (
    "entity_id",
    "name",
    "icon",
    "area_id",
    "floor_id",
    "disabled_by",
    "hidden_by",
    "labels",
)


def _filter_dict(data: dict[str, Any], allowlist: tuple[str, ...]) -> dict[str, Any]:
    return {k: data[k] for k in allowlist if k in data and data[k] is not None}


class AreaRegistryAdapter(BaseAdapter):
    kind = "area"
    owner_mode = OwnerMode.UI_EDITABLE.value

    def export_from_live(self, client: HomeAssistantClient) -> list[ResourceDocument]:
        areas = client.list_areas()
        clean_areas = [
            _filter_dict(a, ALLOWLISTED_AREA_FIELDS)
            for a in sorted(areas, key=lambda x: str(x.get("area_id", "")))
        ]
        return [
            ResourceDocument(
                kind=self.kind,
                key="collection",
                owner_mode=self.owner_mode,
                desired=clean_areas,
            )
        ]

    def canonicalize(self, doc: ResourceDocument) -> ResourceDocument:
        desired = doc.desired if isinstance(doc.desired, list) else []
        clean = [_filter_dict(a, ALLOWLISTED_AREA_FIELDS) for a in desired]
        clean.sort(key=lambda x: str(x.get("area_id", "")))
        return ResourceDocument(
            schema_version=doc.schema_version,
            kind=self.kind,
            key=doc.key,
            owner_mode=self.owner_mode,
            desired=clean,
        )

    def validate(self, doc: ResourceDocument) -> list[str]:
        errors: list[str] = []
        if not isinstance(doc.desired, list):
            return ["Area collection must be a list of area objects"]
        seen_ids: set[str] = set()
        for idx, area in enumerate(doc.desired):
            if not isinstance(area, dict):
                errors.append(f"Area at index {idx} must be a mapping")
                continue
            aid = area.get("area_id")
            if not aid:
                errors.append(f"Area at index {idx} missing required 'area_id'")
            elif aid in seen_ids:
                errors.append(f"Duplicate area_id '{aid}' at index {idx}")
            else:
                seen_ids.add(aid)
        return errors

    def apply(self, client: HomeAssistantClient, action: PlanAction) -> None:
        if action.action in (ActionType.CREATE, ActionType.UPDATE):
            desired_areas = action.after if isinstance(action.after, list) else []
            existing_areas = {
                a["area_id"]: a for a in client.list_areas() if "area_id" in a
            }

            for area in desired_areas:
                if not isinstance(area, dict):
                    continue
                aid = area.get("area_id")
                if not aid:
                    continue
                name = area.get("name", aid.capitalize())
                kwargs = {k: v for k, v in area.items() if k not in ("area_id", "name")}
                if aid in existing_areas:
                    client.update_area(aid, name=name, **kwargs)
                else:
                    client.create_area(name=name, **kwargs)

    def verify(self, client: HomeAssistantClient, doc: ResourceDocument) -> bool:
        live = self.export_from_live(client)
        if not live:
            return False
        return canonical_hash(live[0].desired) == canonical_hash(doc.desired)

    def delete(self, client: HomeAssistantClient, key: str) -> None:
        pass


class DeviceRegistryAdapter(BaseAdapter):
    kind = "device"
    owner_mode = OwnerMode.UI_EDITABLE.value

    def export_from_live(self, client: HomeAssistantClient) -> list[ResourceDocument]:
        devices = client.list_devices()
        # Only export devices with user customizations (e.g. name_by_user, area_id)
        customized: list[dict[str, Any]] = []
        for d in devices:
            if d.get("name_by_user") or d.get("area_id") or d.get("disabled_by"):
                customized.append(_filter_dict(d, ALLOWLISTED_DEVICE_FIELDS))
        customized.sort(key=lambda x: str(x.get("id", "")))
        return [
            ResourceDocument(
                kind=self.kind,
                key="collection",
                owner_mode=self.owner_mode,
                desired=customized,
            )
        ]

    def canonicalize(self, doc: ResourceDocument) -> ResourceDocument:
        desired = doc.desired if isinstance(doc.desired, list) else []
        clean = [_filter_dict(d, ALLOWLISTED_DEVICE_FIELDS) for d in desired]
        clean.sort(key=lambda x: str(x.get("id", "")))
        return ResourceDocument(
            schema_version=doc.schema_version,
            kind=self.kind,
            key=doc.key,
            owner_mode=self.owner_mode,
            desired=clean,
        )

    def validate(self, doc: ResourceDocument) -> list[str]:
        if not isinstance(doc.desired, list):
            return ["Device collection must be a list"]
        return []

    def apply(self, client: HomeAssistantClient, action: PlanAction) -> None:
        if action.action in (ActionType.CREATE, ActionType.UPDATE):
            desired_devices = action.after if isinstance(action.after, list) else []
            for dev in desired_devices:
                if isinstance(dev, dict) and "id" in dev:
                    kwargs = {k: v for k, v in dev.items() if k != "id"}
                    client.update_device(dev["id"], **kwargs)

    def verify(self, client: HomeAssistantClient, doc: ResourceDocument) -> bool:
        live = self.export_from_live(client)
        if not live:
            return False
        return canonical_hash(live[0].desired) == canonical_hash(doc.desired)

    def delete(self, client: HomeAssistantClient, key: str) -> None:
        pass


class EntityRegistryAdapter(BaseAdapter):
    kind = "entity"
    owner_mode = OwnerMode.UI_EDITABLE.value

    def export_from_live(self, client: HomeAssistantClient) -> list[ResourceDocument]:
        entities = client.list_entities()
        # Export entities with user customizations (name, icon, area_id, labels, etc.)
        customized: list[dict[str, Any]] = []
        for e in entities:
            if (
                e.get("name")
                or e.get("icon")
                or e.get("area_id")
                or e.get("disabled_by")
                or e.get("hidden_by")
                or e.get("labels")
            ):
                customized.append(_filter_dict(e, ALLOWLISTED_ENTITY_FIELDS))
        customized.sort(key=lambda x: str(x.get("entity_id", "")))
        return [
            ResourceDocument(
                kind=self.kind,
                key="collection",
                owner_mode=self.owner_mode,
                desired=customized,
            )
        ]

    def canonicalize(self, doc: ResourceDocument) -> ResourceDocument:
        desired = doc.desired if isinstance(doc.desired, list) else []
        clean = [_filter_dict(e, ALLOWLISTED_ENTITY_FIELDS) for e in desired]
        clean.sort(key=lambda x: str(x.get("entity_id", "")))
        return ResourceDocument(
            schema_version=doc.schema_version,
            kind=self.kind,
            key=doc.key,
            owner_mode=self.owner_mode,
            desired=clean,
        )

    def validate(self, doc: ResourceDocument) -> list[str]:
        if not isinstance(doc.desired, list):
            return ["Entity collection must be a list"]
        return []

    def apply(self, client: HomeAssistantClient, action: PlanAction) -> None:
        if action.action in (ActionType.CREATE, ActionType.UPDATE):
            desired_entities = action.after if isinstance(action.after, list) else []
            for ent in desired_entities:
                if isinstance(ent, dict) and "entity_id" in ent:
                    kwargs = {k: v for k, v in ent.items() if k != "entity_id"}
                    client.update_entity(ent["entity_id"], **kwargs)

    def verify(self, client: HomeAssistantClient, doc: ResourceDocument) -> bool:
        live = self.export_from_live(client)
        if not live:
            return False
        return canonical_hash(live[0].desired) == canonical_hash(doc.desired)

    def delete(self, client: HomeAssistantClient, key: str) -> None:
        pass
