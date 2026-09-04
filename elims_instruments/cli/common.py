"""Shared CLI resource helpers."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Protocol, TypeVar

import typer

if TYPE_CHECKING:
    from collections.abc import Iterator

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


@contextmanager
def managed_repository(repository: RepositoryT) -> Iterator[RepositoryT]:
    """Yield a repository and always release its database engine."""
    try:
        yield repository
    finally:
        repository.engine.dispose()
