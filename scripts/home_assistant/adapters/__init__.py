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


def try_get_adapter(kind: str) -> BaseAdapter | None:
    """Return the adapter for `kind`, or None if no adapter is registered.

    Use this in validation passes that should not block the whole pipeline on
    a single bad resource. The strict `get_adapter` is reserved for commands
    that should refuse to run (plan/apply/execute) when the resource set is
    not fully understood.
    """
    return ADAPTERS.get(kind)
