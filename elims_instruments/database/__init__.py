"""Database models and repositories."""

from elims_instruments.characterization import ProjectRevisionSpecifications

from .board import (
    BoardCrud,
    BoardModel,
    parse_board_list,
)
from .connections import (
    ComConnection,
    Connection,
    ConnectionKind,
    ConnectionType,
    SocketConnection,
    USBConnection,
    VisaConnection,
)
from .crud import AssetCrud, Crud, DatabaseConfigurationError, DuplicateAssetTagError
from .dut import DutCrud, DutModel, parse_dut_list
from .instrument import (
    CalibrationStatus,
    InstrumentCrud,
    InstrumentModel,
    InstrumentRevisionAction,
    InstrumentRevisionModel,
    InstrumentType,
    parse_instrument_list,
)
from .migrations import upgrade_database
from .project import (
    ProjectCrud,
    ProjectModel,
    parse_project_list,
    parse_project_specifications,
)

__all__ = [
    "AssetCrud",
    "BoardCrud",
    "BoardModel",
    "CalibrationStatus",
    "ComConnection",
    "Connection",
    "ConnectionKind",
    "ConnectionType",
    "Crud",
    "DatabaseConfigurationError",
    "DuplicateAssetTagError",
    "DutCrud",
    "DutModel",
    "InstrumentCrud",
    "InstrumentModel",
    "InstrumentRevisionAction",
    "InstrumentRevisionModel",
    "InstrumentType",
    "ProjectCrud",
    "ProjectModel",
    "ProjectRevisionSpecifications",
    "SocketConnection",
    "USBConnection",
    "VisaConnection",
    "parse_board_list",
    "parse_dut_list",
    "parse_instrument_list",
    "parse_project_list",
    "parse_project_specifications",
    "upgrade_database",
]
