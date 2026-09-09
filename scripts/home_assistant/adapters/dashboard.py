from __future__ import annotations

from typing import Any

from ..canonical import canonical_hash, strip_volatile
from ..client import HomeAssistantClient, HomeAssistantNotFoundError
from ..models import ActionType, OwnerMode, PlanAction, ResourceDocument
from .base import BaseAdapter


class DashboardAdapter(BaseAdapter):
    kind = "dashboard"
    owner_mode = OwnerMode.UI_EDITABLE.value

    def export_from_live(self, client: HomeAssistantClient) -> list[ResourceDocument]:
        docs: list[ResourceDocument] = []
        dashboards = client.list_dashboards()
        # Storage dashboards
        for d in dashboards:
            url_path = d.get("url_path")
            if not url_path:
                continue
            try:
                conf = client.get_dashboard_config(url_path)
                # Combine dashboard metadata and views
                desired = {
                    "title": d.get("title", url_path.capitalize()),
                    "icon": d.get("icon"),
                    "require_admin": d.get("require_admin", False),
                    "show_in_sidebar": d.get("show_in_sidebar", True),
                }
                if "views" in conf:
                    desired["views"] = conf["views"]
                if "strategy" in conf:
                    desired["strategy"] = conf["strategy"]
                docs.append(
                    ResourceDocument(
                        kind=self.kind,
                        key=url_path,
                        owner_mode=self.owner_mode,
                        desired=desired,
                        metadata={"id": d.get("id"), "mode": d.get("mode", "storage")},
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
            return ["Dashboard configuration must be a mapping"]
        if "views" not in doc.desired and "strategy" not in doc.desired:
            errors.append(
                "Dashboard missing required 'views' list or 'strategy' mapping"
            )
        return errors

    def apply(self, client: HomeAssistantClient, action: PlanAction) -> None:
        if action.action in (ActionType.CREATE, ActionType.UPDATE):
            if not isinstance(action.after, dict):
                raise ValueError(
                    f"Cannot apply dashboard {action.key}: payload must be a dict"
                )
            # If dashboard doesn't exist, create it in dashboard collection
            existing_dashboards = {
                d.get("url_path"): d for d in client.list_dashboards()
            }
            if action.key not in existing_dashboards:
                client.create_dashboard(
                    url_path=action.key,
                    title=action.after.get("title", action.key.capitalize()),
                    icon=action.after.get("icon"),
                    require_admin=action.after.get("require_admin", False),
                    show_in_sidebar=action.after.get("show_in_sidebar", True),
                )
            # Save configuration (views or strategy)
            conf: dict[str, Any] = {}
            if "views" in action.after:
                conf["views"] = action.after["views"]
            if "strategy" in action.after:
                conf["strategy"] = action.after["strategy"]
            client.save_dashboard_config(action.key, conf)
        elif action.action == ActionType.DELETE:
            dashboards = {
                d.get("url_path"): d.get("id") for d in client.list_dashboards()
            }
            dashboard_id = dashboards.get(action.key)
            if dashboard_id:
                client.delete_dashboard(dashboard_id)

    def verify(self, client: HomeAssistantClient, doc: ResourceDocument) -> bool:
        try:
            live_conf = client.get_dashboard_config(doc.key)
            expected_conf: dict[str, Any] = {}
            if isinstance(doc.desired, dict):
                if "views" in doc.desired:
                    expected_conf["views"] = doc.desired["views"]
                if "strategy" in doc.desired:
                    expected_conf["strategy"] = doc.desired["strategy"]
            return canonical_hash(live_conf) == canonical_hash(expected_conf)
        except HomeAssistantNotFoundError:
            return False

    def delete(self, client: HomeAssistantClient, key: str) -> None:
        dashboards = {d.get("url_path"): d.get("id") for d in client.list_dashboards()}
        dashboard_id = dashboards.get(key)
        if dashboard_id:
            client.delete_dashboard(dashboard_id)
