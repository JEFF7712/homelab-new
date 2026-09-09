from __future__ import annotations

from .automation import AutomationAdapter
from .base import BaseAdapter
from .core import CoreConfigurationAdapter
from .dashboard import DashboardAdapter
from .helper import HelperAdapter
from .integration import IntegrationAdapter
from .registry import AreaRegistryAdapter, DeviceRegistryAdapter, EntityRegistryAdapter
from .scene import SceneAdapter
from .script import ScriptAdapter

ADAPTERS: dict[str, BaseAdapter] = {
    "core": CoreConfigurationAdapter(),
    "automation": AutomationAdapter(),
    "script": ScriptAdapter(),
    "scene": SceneAdapter(),
    "dashboard": DashboardAdapter(),
    "area": AreaRegistryAdapter(),
    "device": DeviceRegistryAdapter(),
    "entity": EntityRegistryAdapter(),
    "helper": HelperAdapter(),
    "integration": IntegrationAdapter(),
}


def get_adapter(kind: str) -> BaseAdapter:
    if kind not in ADAPTERS:
        raise ValueError(f"No adapter registered for resource kind '{kind}'")
    return ADAPTERS[kind]
