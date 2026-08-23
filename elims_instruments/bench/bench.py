"""Load a laboratory bench from TOML configuration."""

from __future__ import annotations

import keyword
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from tomllib import TOMLDecodeError, load

from elims_instruments.bench.error import BenchConfigurationError
from elims_instruments.boards import BoardCollection, create_boards
from elims_instruments.duts import DutCollection, create_duts
from elims_instruments.instruments.factory import (
    InstrumentCollection,
    create_instruments,
)
from elims_instruments.utils.logger import get_logger

AuthorizedNames = Collection[str] | type[StrEnum]
AssignmentErrorFactory = Callable[[object], BenchConfigurationError]
logger = get_logger(__name__)


@dataclass(frozen=True)
class _AssignmentSpec:
    """Validation behavior for one bench assignment section."""

    section: str
    collection_type: type[object]
    optional: bool
    unauthorized_error: AssignmentErrorFactory
    invalid_name_error: AssignmentErrorFactory


_INSTRUMENT_SPEC = _AssignmentSpec(
    section="instruments",
    collection_type=InstrumentCollection,
    optional=False,
    unauthorized_error=BenchConfigurationError.unauthorized_name,
    invalid_name_error=BenchConfigurationError.invalid_name,
)
_BOARD_SPEC = _AssignmentSpec(
    section="boards",
    collection_type=BoardCollection,
    optional=True,
    unauthorized_error=BenchConfigurationError.unauthorized_board_name,
    invalid_name_error=BenchConfigurationError.invalid_board_name,
)
_DUT_SPEC = _AssignmentSpec(
    section="duts",
    collection_type=DutCollection,
    optional=True,
    unauthorized_error=BenchConfigurationError.unauthorized_dut_name,
    invalid_name_error=BenchConfigurationError.invalid_dut_name,
)


def _authorized_name_values(authorized_names: AuthorizedNames) -> set[str]:
    """Normalize a project-owned enum or collection of authorized names."""
    if isinstance(authorized_names, type) and issubclass(authorized_names, StrEnum):
        return {member.value for member in authorized_names}
    if any(not isinstance(name, str) for name in authorized_names):
        raise BenchConfigurationError.invalid_authorized_names()
    return set(authorized_names)


def _read_configuration(configuration: Path) -> dict[str, object]:
    """Read and parse a bench TOML file once."""
    logger.debug("Reading bench configuration from {}", configuration)
    try:
        with configuration.open("rb") as configuration_file:
            return load(configuration_file)
    except (OSError, TOMLDecodeError) as error:
        raise BenchConfigurationError.invalid_file(configuration) from error


def _validate_assignments(
    raw_configuration: Mapping[str, object],
    configuration: Path,
    authorized_names: set[str],
    specification: _AssignmentSpec,
) -> dict[str, str]:
    """Validate one named assignment table from a parsed configuration."""
    logger.debug(
        "Validating bench {} from {}",
        specification.section,
        configuration,
    )
    assignments = raw_configuration.get(specification.section)
    if assignments is None and specification.optional:
        return {}
    if not isinstance(assignments, dict):
        raise BenchConfigurationError.missing_instruments_table()

    validated: dict[str, str] = {}
    used_asset_tags: set[str] = set()
    for name, asset_tag in assignments.items():
        if name not in authorized_names:
            raise specification.unauthorized_error(name)
        if (
            not isinstance(name, str)
            or not name.isidentifier()
            or keyword.iskeyword(name)
            or name.startswith("_")
            or hasattr(specification.collection_type, name)
        ):
            raise specification.invalid_name_error(name)
        if not isinstance(asset_tag, str) or not asset_tag.strip():
            raise BenchConfigurationError.invalid_asset_tag(name)
        if asset_tag in used_asset_tags:
            raise BenchConfigurationError.duplicate_asset_tag(asset_tag)
        validated[name] = asset_tag
        used_asset_tags.add(asset_tag)
        logger.debug(
            "Validated bench {} assignment {} -> {}",
            specification.section,
            name,
            asset_tag,
        )
    logger.debug(
        "Validated {} bench {}",
        len(validated),
        specification.section,
    )
    return validated


class Bench:
    """A configured bench containing instruments, boards, and DUTs."""

    def __init__(
        self,
        configuration: Path = Path("bench.toml"),
        *,
        authorized_instrument_names: AuthorizedNames,
        authorized_board_names: AuthorizedNames = (),
        authorized_dut_names: AuthorizedNames = (),
    ) -> None:
        """Load configured instruments, boards, and DUTs."""
        logger.info("Loading bench from {}", configuration)
        raw_configuration = _read_configuration(configuration)
        assignments = _validate_assignments(
            raw_configuration,
            configuration,
            _authorized_name_values(authorized_instrument_names),
            _INSTRUMENT_SPEC,
        )
        board_assignments = _validate_assignments(
            raw_configuration,
            configuration,
            _authorized_name_values(authorized_board_names),
            _BOARD_SPEC,
        )
        dut_assignments = _validate_assignments(
            raw_configuration,
            configuration,
            _authorized_name_values(authorized_dut_names),
            _DUT_SPEC,
        )
        self.instruments = create_instruments(assignments, configuration)
        self.boards = create_boards(board_assignments, configuration)
        self.duts = create_duts(dut_assignments, configuration)
        logger.info(
            "Loaded bench with {} instruments, {} boards, and {} DUTs",
            len(self.instruments),
            len(self.boards),
            len(self.duts),
        )
