from __future__ import annotations

from abc import ABC, abstractmethod

from ..client import HomeAssistantClient
from ..models import OwnerMode, PlanAction, ResourceDocument


class BaseAdapter(ABC):
    """Abstract base class for all Home Assistant resource adapters."""

    kind: str
    owner_mode: str = OwnerMode.UI_EDITABLE.value

    @abstractmethod
    def export_from_live(self, client: HomeAssistantClient) -> list[ResourceDocument]:
        """Query Home Assistant and return live configuration documents for this kind."""
        raise NotImplementedError

    @abstractmethod
    def canonicalize(self, doc: ResourceDocument) -> ResourceDocument:
        """Strip volatile fields and format resource into canonical representation."""
        raise NotImplementedError

    @abstractmethod
    def validate(self, doc: ResourceDocument) -> list[str]:
        """Validate resource against schema and internal reference integrity. Return error messages."""
        raise NotImplementedError

    @abstractmethod
    def apply(self, client: HomeAssistantClient, action: PlanAction) -> None:
        """Mutate Home Assistant to realize the desired state in action."""
        raise NotImplementedError

    @abstractmethod
    def verify(self, client: HomeAssistantClient, doc: ResourceDocument) -> bool:
        """Read back from Home Assistant and verify semantic equality with desired state."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, client: HomeAssistantClient, key: str) -> None:
        """Remove resource from Home Assistant."""
        raise NotImplementedError
