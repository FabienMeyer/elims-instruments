"""Reusable building blocks for named bench resource factories."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from types import MappingProxyType
from typing import TYPE_CHECKING, Generic, TypeVar

from sqlmodel import SQLModel

if TYPE_CHECKING:
    from elims_instruments.database import Crud

ModelT = TypeVar("ModelT", bound=SQLModel)
ItemT = TypeVar("ItemT")
BuilderT = TypeVar("BuilderT")


class NamedCollection(Mapping[str, ItemT], Generic[ItemT]):
    """Immutable named resources supporting mapping and attribute access."""

    def __init__(self, items: Mapping[str, ItemT]) -> None:
        self._items = MappingProxyType(dict(items))

    def __getitem__(self, name: str) -> ItemT:
        return self._items[name]

    def __iter__(self) -> Iterator[str]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __getattr__(self, name: str) -> ItemT:
        try:
            return self._items[name]
        except KeyError as error:
            raise AttributeError(name) from error


def resolve_assignments(
    assignments: Mapping[str, str],
    repository: Crud[ModelT],
    *,
    lookup_field: str,
    builder: Callable[[ModelT], ItemT],
    not_found: Callable[[str], Exception],
) -> dict[str, ItemT]:
    """Resolve configured identifiers and build their named runtime objects."""
    resolved: dict[str, ItemT] = {}
    for name, identifier in assignments.items():
        model = repository.fetch(lookup_field, identifier)
        if model is None:
            raise not_found(identifier)
        resolved[name] = builder(model)
    return resolved


def register_string_builder(
    registry: dict[str, BuilderT],
    key: str,
    builder: BuilderT,
    *,
    key_error: str,
    builder_error: str,
    duplicate_error: Callable[[str], str],
    replace: bool,
) -> None:
    """Validate and register a builder under a normalized string key."""
    if not isinstance(key, str) or not key.strip():
        raise ValueError(key_error)
    if not callable(builder):
        raise TypeError(builder_error)
    normalized_key = key.strip().casefold()
    registered = registry.get(normalized_key)
    if registered is builder:
        return
    if registered is not None and not replace:
        raise ValueError(duplicate_error(key))
    registry[normalized_key] = builder
