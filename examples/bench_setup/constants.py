"""Names and paths shared by the database-backed examples."""

from enum import StrEnum
from pathlib import Path

BENCH_CONFIGURATION = Path(__file__).with_name("bench.toml")
BOARD_DRIVER_NAME = "characterization"
PROJECT_DRIVER_NAME = "example-project"


class InstrumentName(StrEnum):
    PRIMARY_DMM = "primary_dmm"
    FREQUENCY_COUNTER = "frequency_counter"


class BoardName(StrEnum):
    CHARACTERIZATION_BOARD = "characterization_board"


class DutName(StrEnum):
    CHARACTERIZED_IC = "characterized_ic"


class ProjectName(StrEnum):
    CHARACTERIZATION = "characterization"
