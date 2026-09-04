"""Create and collect DUT objects independently of bench configuration."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import ClassVar

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
    def register(cls, project: str, builder: DutBuilder) -> None:
        """Register a specialized builder for a DUT project."""
        if not isinstance(project, str) or not project.strip():
            raise ValueError("DUT project must be a non-empty string")
        if not callable(builder):
            raise TypeError("DUT builder must be callable")
        normalized_project = project.strip().casefold()
        cls._registry[normalized_project] = builder
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


class DutCollection(Mapping[str, Dut]):
    """Read-only DUT collection supporting mapping and attribute access."""

    def __init__(self, duts: Mapping[str, Dut]) -> None:
        """Store named DUT objects in an immutable mapping."""
        self._duts = MappingProxyType(dict(duts))

    def __getitem__(self, name: str) -> Dut:
        """Return the DUT assigned to *name*."""
        return self._duts[name]

    def __iter__(self) -> Iterator[str]:
        """Iterate over configured DUT names."""
        return iter(self._duts)

    def __len__(self) -> int:
        """Return the number of configured DUTs."""
        return len(self._duts)

    def __getattr__(self, name: str) -> Dut:
        """Allow attribute access such as ``duts.characterized_ic``."""
        try:
            return self._duts[name]
        except KeyError as error:
            raise AttributeError(name) from error


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

    repository = DutCrud(logger, configuration)
    duts: dict[str, Dut] = {}
    try:
        for name, asset_tag in assignments.items():
            logger.debug("Resolving DUT {} from asset {}", name, asset_tag)
            dut = repository.fetch("asset_tag", asset_tag)
            if dut is None:
                raise DutAssetNotFoundError(asset_tag)
            duts[name] = DutFactory.create(dut)
    finally:
        repository.engine.dispose()
    collection = DutCollection(duts)
    logger.info("Created {} DUTs", len(collection))
    return collection
