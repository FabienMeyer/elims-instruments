"""Shared CLI resource helpers."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Protocol, TypeVar

import typer

from elims_instruments.database import DatabaseConfigurationError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from sqlalchemy.engine import Engine


class DisposableRepository(Protocol):
    """Repository exposing an engine that can be disposed."""

    @property
    def engine(self) -> Engine:
        """Return the repository engine."""
        ...


RepositoryT = TypeVar("RepositoryT", bound=DisposableRepository)

ConfigurationOption = Annotated[
    Path,
    typer.Option(
        "--config",
        "-c",
        help="Bench TOML configuration file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
]


def collect_changes(**values: object | None) -> dict[str, object]:
    """Return only explicitly supplied update values."""
    return {field: value for field, value in values.items() if value is not None}


def apply_optional_change(
    changes: dict[str, object],
    field: str,
    value: object | None,
    *,
    clear: bool,
) -> None:
    """Apply a nullable update while rejecting contradictory CLI flags."""
    label = field.replace("_", " ")
    if value is not None and clear:
        raise typer.BadParameter(f"cannot set and clear {label}")
    if clear:
        changes[field] = None
    elif value is not None:
        changes[field] = value


@contextmanager
def configuration_errors() -> Iterator[None]:
    """Present invalid database configuration as a normal CLI error."""
    try:
        yield
    except DatabaseConfigurationError as error:
        raise typer.BadParameter(str(error), param_hint="--config") from error


@contextmanager
def managed_repository(
    factory: Callable[[], RepositoryT],
) -> Iterator[RepositoryT]:
    """Create a repository and always release its database engine."""
    with configuration_errors():
        repository = factory()
    try:
        yield repository
    finally:
        repository.engine.dispose()
