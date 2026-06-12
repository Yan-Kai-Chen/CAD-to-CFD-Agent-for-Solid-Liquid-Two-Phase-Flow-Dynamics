"""Runtime registry for CAD backend implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .backend import CADBackend
from .schemas import CADBackendCapabilities


BackendFactory = Callable[[], CADBackend]


@dataclass(frozen=True)
class BackendRegistration:
    """Metadata and optional factory for one CAD backend."""

    name: str
    description: str
    capabilities: CADBackendCapabilities
    factory: BackendFactory | None = None

    def create(self) -> CADBackend:
        if self.factory is None:
            raise RuntimeError(f"CAD backend is registered without a factory: {self.name}")
        return self.factory()


class BackendRegistry:
    """Small explicit registry for backend discovery."""

    def __init__(self) -> None:
        self._items: dict[str, BackendRegistration] = {}

    def register(self, registration: BackendRegistration, *, replace: bool = False) -> None:
        key = registration.name.lower()
        if key in self._items and not replace:
            raise ValueError(f"CAD backend is already registered: {registration.name}")
        self._items[key] = registration

    def names(self) -> list[str]:
        return sorted(item.name for item in self._items.values())

    def get(self, name: str) -> BackendRegistration:
        key = name.lower()
        try:
            return self._items[key]
        except KeyError as exc:
            raise KeyError(f"Unknown CAD backend: {name}") from exc

    def create(self, name: str) -> CADBackend:
        return self.get(name).create()

    def describe(self) -> list[dict[str, object]]:
        return [
            {
                "name": item.name,
                "description": item.description,
                "capabilities": item.capabilities.to_dict(),
                "has_factory": item.factory is not None,
            }
            for item in sorted(self._items.values(), key=lambda value: value.name.lower())
        ]

    def clear(self) -> None:
        self._items.clear()


registry = BackendRegistry()
