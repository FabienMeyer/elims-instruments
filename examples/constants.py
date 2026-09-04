from enum import StrEnum

class InstrumentName(StrEnum):
    PRIMARY_DMM = "primary_dmm"
    FREQUENCY_COUNTER = "frequency_counter"


class BoardName(StrEnum):
    CHARACTERIZATION_BOARD = "characterization_board"


class DutName(StrEnum):
    CHARACTERIZED_IC = "characterized_ic"


class ProjectName(StrEnum):
    CHARACTERIZATION = "characterization"
