"""Create and collect DUT objects independently of bench configuration."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import ClassVar

from elims_instruments.bench.factory import (
    NamedCollection,
    register_string_builder,
    resolve_assignments,
)
from elims_instruments.database import DutCrud, DutModel
from elims_instruments.utils.logger import LoggerHelper, get_logger

from .abstract import Dut
from .error import DutAssetNotFoundError

DutBuilder = Callable[[DutModel], Dut]
logger = get_logger(__name__, LoggerHelper.Color.YELLOW)


class DutFactory:
    """Create registered DUT objects from database models."""

    _registry: ClassVar[dict[str, DutBuilder]] = {}

    @classmethod
    def register(
        cls,
        project: str,
        builder: DutBuilder,
        *,
        replace: bool = False,
    ) -> None:
        """Register a specialized builder for a DUT project."""
        register_string_builder(
            cls._registry,
            project,
            builder,
            key_error="DUT project must be a non-empty string",
            builder_error="DUT builder must be callable",
            duplicate_error=lambda key: (
                f"DUT project already has a registered builder: {key!r}"
            ),
            replace=replace,
        )
        logger.debug(
            "Registered DUT builder {} for project {}",
            getattr(builder, "__name__", type(builder).__name__),
            project,
        )

    @classmethod
    def create(cls, dut: DutModel) -> Dut:
        """Create the concrete DUT registered for a DUT project."""
        project_key = dut.project.strip().casefold()
        if project_key not in cls._registry:
            available = ", ".join(cls._registry)
            raise ValueError(
                f"Unknown DUT project: '{dut.project}'. "
                f"Available projects: {available or 'None registered yet'}"
            )
        builder = cls._registry[project_key]
        logger.debug(
            "Creating {} for DUT asset {}",
            getattr(builder, "__name__", type(builder).__name__),
            dut.asset_tag,
        )
        instance = builder(dut)
        if not isinstance(instance, Dut):
            raise TypeError("DUT builders must return a Dut object")
        return instance


class DutCollection(NamedCollection[Dut]):
    """Read-only DUT collection supporting mapping and attribute access."""


def create_duts(
    assignments: Mapping[str, str],
    configuration: Path = Path("bench.toml"),
) -> DutCollection:
    """Resolve asset tags and create a named collection of DUT objects."""
    logger.info(
        "Creating {} DUTs using bench configuration {}",
        len(assignments),
        configuration,
    )
    if not assignments:
        logger.info("Created 0 DUTs")
        return DutCollection({})

    with DutCrud(logger, configuration, create_tables=False) as repository:
        duts = resolve_assignments(
            assignments,
            repository,
            lookup_field="asset_tag",
            builder=DutFactory.create,
            not_found=DutAssetNotFoundError,
        )
    collection = DutCollection(duts)
    logger.info("Created {} DUTs", len(collection))
    return collection
