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
                desired: dict[str, Any] = dict(conf)
                # Combine dashboard metadata and configuration
                if "title" not in desired or not desired["title"]:
                    desired["title"] = d.get("title", url_path.capitalize())
                for meta_key in ("icon", "require_admin", "show_in_sidebar"):
                    if meta_key in d:
                        desired[meta_key] = d[meta_key]

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
            else:
                dashboard_info = existing_dashboards[action.key]
                dashboard_id = dashboard_info.get("id") or action.key
                metadata_updates: dict[str, Any] = {}
                for field in ("title", "icon", "require_admin", "show_in_sidebar"):
                    if field in action.after:
                        metadata_updates[field] = action.after[field]
                if metadata_updates:
                    client.update_dashboard(
                        dashboard_id=dashboard_id, **metadata_updates
                    )

            # Save configuration (exclude collection-only metadata fields from config body)
            conf = {
                k: v
                for k, v in action.after.items()
                if k not in ("icon", "require_admin", "show_in_sidebar")
            }
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
            live_docs = {
                d.key: self.canonicalize(d) for d in self.export_from_live(client)
            }
            live_doc = live_docs.get(doc.key)
            if live_doc is None or live_doc.desired is None:
                return False
            expected = self.canonicalize(doc).desired
            return canonical_hash(live_doc.desired) == canonical_hash(expected)
        except Exception:
            return False

    def delete(self, client: HomeAssistantClient, key: str) -> None:
        dashboards = {d.get("url_path"): d.get("id") for d in client.list_dashboards()}
        dashboard_id = dashboards.get(key)
        if dashboard_id:
            client.delete_dashboard(dashboard_id)
