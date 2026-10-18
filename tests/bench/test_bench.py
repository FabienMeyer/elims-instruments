"""Tests for named bench configuration loading."""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import TYPE_CHECKING

import pytest
from loguru import logger
from sqlmodel import SQLModel

import elims_instruments.bench.bench as bench_module
from elims_instruments.bench import (
    Bench,
    BenchConfigurationError,
    Dut,
    DutFactory,
    Project,
    ProjectFactory,
)
from elims_instruments.bench.instruments import (
    InstrumentAssetNotFoundError,
    InstrumentFactory,
    UnsupportedInstrumentTypeError,
)
from elims_instruments.bench.instruments.counter.ks53220a import Keysight53220A
from elims_instruments.bench.instruments.multimeter.ks34401a import Keysight34401A
from elims_instruments.characterization import (
    TemperatureSpecification,
    VoltageSpecification,
)
from elims_instruments.database import (
    BoardCrud,
    BoardModel,
    DutCrud,
    DutModel,
    InstrumentCrud,
    InstrumentModel,
    InstrumentType,
    ProjectCrud,
    ProjectModel,
    ProjectRevisionSpecifications,
    USBConnection,
    VisaConnection,
)
from elims_instruments.utils import Limits

if TYPE_CHECKING:
    from pathlib import Path


def revision_specifications() -> list[ProjectRevisionSpecifications]:
    """Build the operating profile used by the bench fixture."""
    return [
        ProjectRevisionSpecifications(
            die_revision="A",
            voltage_specifications=(VoltageSpecification("VDD", Limits(typical=1.2)),),
            temperature_specifications=(
                TemperatureSpecification("DUT", Limits(typical=25)),
            ),
        )
    ]


class ProjectInstrumentName(StrEnum):
    """Instrument names authorized by the example project."""

    COUNTER = "counter"
    FIRST = "first"
    MISSING = "missing"
    PRIMARY_DMM = "primary_dmm"
    SECOND = "second"


class ProjectBoardName(StrEnum):
    """Board names authorized by the example project."""

    CHARACTERIZATION_BOARD = "characterization_board"


class ProjectDutName(StrEnum):
    """DUT names authorized by the example project."""

    CHARACTERIZED_IC = "characterized_ic"


class BenchProjectName(StrEnum):
    """Project names authorized by the bench consumer."""

    CHARACTERIZATION = "characterization"


class DemoDut(Dut):
    """Concrete DUT used by bench tests."""

    def get_id(self) -> str:
        """Return the database DUT ID."""
        return self.dut.id

    def reset(self) -> None:
        """Reset this test DUT."""
        super().reset()


class DemoProject(Project):
    """Concrete project used by bench tests."""

    def get_id(self) -> str:
        """Return the database project ID."""
        return self.project.id


@pytest.fixture
def bench_configuration(tmp_path: Path) -> Path:
    """Create a combined bench configuration and populated database."""
    DutFactory.register("demo-project", DemoDut, replace=True)
    ProjectFactory.register("demo-project", DemoProject)
    configuration = tmp_path / "bench.toml"
    database = (tmp_path / "instruments.db").as_posix()
    configuration.write_text(
        f'[database]\nurl = "sqlite:///{database}"\necho = false\n',
        encoding="utf-8",
    )
    repository = InstrumentCrud(logging.getLogger(__name__), configuration)
    repository.upsert_many(
        [
            InstrumentModel(
                id="dmm-1",
                asset_tag="DMM-001",
                type=InstrumentType.MULTIMETER,
                maker="Keysight",
                model="34401A",
                connection=VisaConnection(resource_name="GPIB0::1::INSTR"),
            ),
            InstrumentModel(
                id="counter-1",
                asset_tag="CNT-001",
                type=InstrumentType.COUNTER,
                maker="Keysight",
                model="53220A",
                connection=VisaConnection(resource_name="GPIB0::2::INSTR"),
            ),
        ]
    )
    board_repository = BoardCrud(logging.getLogger(__name__), configuration)
    board = board_repository.add(
        BoardModel(
            id="board-1",
            asset_tag="BRD-001",
            type="generic",
            maker="ELIMS",
            model="Characterization Board A",
            connection=USBConnection(vendor_id=1, product_id=2),
        )
    )
    dut_repository = DutCrud(logging.getLogger(__name__), configuration)
    dut = dut_repository.add(
        DutModel(
            id="dut-1",
            asset_tag="DUT-001",
            project="demo-project",
            corner="TT",
            die_revision="A",
            lot_number="LOT-001",
        )
    )
    project = ProjectModel(
        id="project-1",
        internal_name="demo-project",
        datasheet_name="Demo IC",
        specifications=revision_specifications(),
    )
    project.supported_duts = [dut]
    project.supported_boards = [board]
    project_repository = ProjectCrud(logging.getLogger(__name__), configuration)
    project_repository.add(project)
    return configuration


def _write_bench_configuration(
    configuration: Path,
    assignments: str,
) -> None:
    """Write one combined database and bench configuration."""
    database_table = configuration.read_text(encoding="utf-8").split(
        "[instruments]",
        maxsplit=1,
    )[0]
    configuration.write_text(
        f"{database_table}\n{assignments}",
        encoding="utf-8",
    )


def test_bench_creates_named_drivers(
    bench_configuration: Path,
) -> None:
    """TOML names resolve asset tags through their matching factories."""
    messages: list[str] = []
    sink_id = logger.add(
        lambda message: messages.append(message.record["message"]),
        level="DEBUG",
    )
    _write_bench_configuration(
        bench_configuration,
        '[instruments]\nprimary_dmm = "DMM-001"\ncounter = "CNT-001"\n',
    )

    try:
        bench = Bench(
            bench_configuration,
            authorized_instrument_names=ProjectInstrumentName,
        )
    finally:
        logger.remove(sink_id)

    assert isinstance(bench.instruments.primary_dmm, Keysight34401A)
    assert isinstance(bench.instruments["counter"], Keysight53220A)
    assert list(bench.instruments) == ["primary_dmm", "counter"]
    assert (
        "Loaded bench with 2 instruments, 0 boards, 0 DUTs, and 0 projects" in messages
    )
    assert "Created Keysight34401A driver for asset DMM-001" in messages
    assert "Created Keysight53220A driver for asset CNT-001" in messages


def test_bench_creates_named_board(
    bench_configuration: Path,
) -> None:
    """A board assignment resolves to the base characterization-board driver."""
    _write_bench_configuration(
        bench_configuration,
        '[instruments]\nprimary_dmm = "DMM-001"\n'
        '[boards]\ncharacterization_board = "BRD-001"\n',
    )

    bench = Bench(
        bench_configuration,
        authorized_instrument_names=ProjectInstrumentName,
        authorized_board_names=ProjectBoardName,
    )

    assert bench.boards.characterization_board.board.asset_tag == "BRD-001"


def test_bench_creates_named_dut(bench_configuration: Path) -> None:
    """A DUT assignment resolves independently from its board fixture."""
    _write_bench_configuration(
        bench_configuration,
        '[instruments]\nprimary_dmm = "DMM-001"\n'
        '[boards]\ncharacterization_board = "BRD-001"\n'
        '[duts]\ncharacterized_ic = "DUT-001"\n',
    )

    bench = Bench(
        bench_configuration,
        authorized_instrument_names=ProjectInstrumentName,
        authorized_board_names=ProjectBoardName,
        authorized_dut_names=ProjectDutName,
    )

    assert bench.duts.characterized_ic.dut.asset_tag == "DUT-001"
    assert bench.boards.characterization_board.board.asset_tag == "BRD-001"


def test_bench_creates_named_project(bench_configuration: Path) -> None:
    """A project assignment resolves by its unique database name."""
    _write_bench_configuration(
        bench_configuration,
        '[instruments]\nprimary_dmm = "DMM-001"\n'
        '[projects]\ncharacterization = "demo-project"\n',
    )

    bench = Bench(
        bench_configuration,
        authorized_instrument_names=ProjectInstrumentName,
        authorized_project_names=BenchProjectName,
    )

    assert isinstance(bench.projects.characterization, DemoProject)
    assert bench.projects.characterization.get_id() == "project-1"
    assert bench.projects.characterization.project.supported_duts[0].id == "dut-1"


def test_bench_reads_configuration_once(
    bench_configuration: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One parsed TOML mapping supplies every assignment section."""
    load_count = 0
    original_load = bench_module.load

    def counting_load(configuration_file):
        nonlocal load_count
        load_count += 1
        return original_load(configuration_file)

    monkeypatch.setattr(bench_module, "load", counting_load)
    _write_bench_configuration(
        bench_configuration,
        '[instruments]\nprimary_dmm = "DMM-001"\n'
        '[boards]\ncharacterization_board = "BRD-001"\n'
        '[duts]\ncharacterized_ic = "DUT-001"\n',
    )

    Bench(
        bench_configuration,
        authorized_instrument_names=ProjectInstrumentName,
        authorized_board_names=ProjectBoardName,
        authorized_dut_names=ProjectDutName,
    )

    assert load_count == 1


def test_bench_report_columns_are_unique_and_role_qualified(
    bench_configuration: Path,
) -> None:
    """A multi-asset bench produces unambiguous characterization columns."""
    _write_bench_configuration(
        bench_configuration,
        '[instruments]\nprimary_dmm = "DMM-001"\ncounter = "CNT-001"\n'
        '[boards]\ncharacterization_board = "BRD-001"\n'
        '[duts]\ncharacterized_ic = "DUT-001"\n',
    )
    bench = Bench(
        bench_configuration,
        authorized_instrument_names=ProjectInstrumentName,
        authorized_board_names=ProjectBoardName,
        authorized_dut_names=ProjectDutName,
    )

    headers = bench.report_header()

    assert headers == [
        "instrument_primary_dmm_asset_tag",
        "instrument_primary_dmm_calibration_date",
        "instrument_counter_asset_tag",
        "instrument_counter_calibration_date",
        "board_characterization_board_asset_tag",
        "dut_characterized_ic_dut_id",
        "dut_characterized_ic_serial_number",
        "dut_characterized_ic_corner",
        "dut_characterized_ic_revision",
    ]
    assert len(headers) == len(set(headers))
    assert bench.report_value() == [
        "DMM-001",
        "",
        "CNT-001",
        "",
        "BRD-001",
        "dut-1",
        "",
        "TT",
        "A",
    ]


def test_bench_loading_does_not_create_database_tables(
    bench_configuration: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resolving a complete bench never performs schema creation."""
    _write_bench_configuration(
        bench_configuration,
        '[instruments]\nprimary_dmm = "DMM-001"\n'
        '[boards]\ncharacterization_board = "BRD-001"\n'
        '[duts]\ncharacterized_ic = "DUT-001"\n'
        '[projects]\ncharacterization = "demo-project"\n',
    )

    def reject_schema_creation(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("Bench loading attempted to create database tables")

    monkeypatch.setattr(SQLModel.metadata, "create_all", reject_schema_creation)

    bench = Bench(
        bench_configuration,
        authorized_instrument_names=ProjectInstrumentName,
        authorized_board_names=ProjectBoardName,
        authorized_dut_names=ProjectDutName,
        authorized_project_names=BenchProjectName,
    )

    assert len(bench.instruments) == 1
    assert len(bench.boards) == 1
    assert len(bench.duts) == 1
    assert len(bench.projects) == 1


def test_bench_without_board_table_has_empty_board_collection(
    bench_configuration: Path,
) -> None:
    """Existing instrument-only bench files remain valid."""
    _write_bench_configuration(
        bench_configuration,
        '[instruments]\nprimary_dmm = "DMM-001"\n',
    )

    bench = Bench(
        bench_configuration,
        authorized_instrument_names=ProjectInstrumentName,
    )

    assert len(bench.boards) == 0
    assert len(bench.projects) == 0


def test_bench_requires_instruments_table(bench_configuration: Path) -> None:
    """The required instrument section has a specific missing-table error."""
    with pytest.raises(
        BenchConfigurationError,
        match=r"must contain an \[instruments\] table",
    ):
        Bench(
            bench_configuration,
            authorized_instrument_names=ProjectInstrumentName,
        )


@pytest.mark.parametrize(
    ("section", "authorized_names_argument", "authorized_names"),
    [
        ("instruments", "authorized_instrument_names", ProjectInstrumentName),
        ("boards", "authorized_board_names", ProjectBoardName),
        ("duts", "authorized_dut_names", ProjectDutName),
        ("projects", "authorized_project_names", BenchProjectName),
    ],
)
def test_bench_rejects_non_table_assignment_sections(
    bench_configuration: Path,
    section: str,
    authorized_names_argument: str,
    authorized_names: type[StrEnum],
) -> None:
    """Malformed assignment sections identify the section that is invalid."""
    database_configuration = bench_configuration.read_text(encoding="utf-8")
    configuration = f'{section} = "invalid"\n{database_configuration}'
    if section != "instruments":
        configuration += '[instruments]\nprimary_dmm = "DMM-001"\n'
    bench_configuration.write_text(configuration, encoding="utf-8")
    arguments: dict[str, object] = {
        "authorized_instrument_names": ProjectInstrumentName,
        authorized_names_argument: authorized_names,
    }

    with pytest.raises(
        BenchConfigurationError,
        match=rf"\[{section}\] must be a table",
    ):
        Bench(bench_configuration, **arguments)  # type: ignore[arg-type]


def test_bench_rejects_unauthorized_project_name(
    bench_configuration: Path,
) -> None:
    """A project key must be authorized by the caller."""
    _write_bench_configuration(
        bench_configuration,
        '[instruments]\nprimary_dmm = "DMM-001"\n'
        '[projects]\nunexpected = "demo-project"\n',
    )

    with pytest.raises(BenchConfigurationError, match="unexpected"):
        Bench(
            bench_configuration,
            authorized_instrument_names=ProjectInstrumentName,
            authorized_project_names=BenchProjectName,
        )


def test_bench_rejects_missing_asset_tag(
    bench_configuration: Path,
) -> None:
    """Every configured asset tag must exist in the instrument database."""
    _write_bench_configuration(
        bench_configuration,
        '[instruments]\nmissing = "DMM-999"\n',
    )

    with pytest.raises(InstrumentAssetNotFoundError, match="DMM-999"):
        Bench(
            bench_configuration,
            authorized_instrument_names=ProjectInstrumentName,
        )


def test_bench_rejects_duplicate_asset_assignments(
    bench_configuration: Path,
) -> None:
    """One physical instrument cannot have multiple bench names."""
    _write_bench_configuration(
        bench_configuration,
        '[instruments]\nfirst = "DMM-001"\nsecond = "DMM-001"\n',
    )

    with pytest.raises(BenchConfigurationError, match="DMM-001"):
        Bench(
            bench_configuration,
            authorized_instrument_names=ProjectInstrumentName,
        )


def test_bench_rejects_unauthorized_name(
    bench_configuration: Path,
) -> None:
    """A TOML key must be authorized by the project."""
    _write_bench_configuration(
        bench_configuration,
        '[instruments]\nunexpected = "DMM-001"\n',
    )

    with pytest.raises(BenchConfigurationError, match="unexpected"):
        Bench(
            bench_configuration,
            authorized_instrument_names=ProjectInstrumentName,
        )


def test_instrument_factory_rejects_unregistered_type() -> None:
    """A model category without a registered driver factory is rejected."""
    instrument = InstrumentModel(
        id="scope-1",
        asset_tag="SCOPE-001",
        type=InstrumentType.OSCILLOSCOPE,
        maker="Keysight",
        model="DSOX1204G",
        connection=VisaConnection(resource_name="TCPIP0::scope::INSTR"),
    )

    with pytest.raises(UnsupportedInstrumentTypeError, match="oscilloscope"):
        InstrumentFactory.create(instrument)
