"""Files module."""

import dataclasses
from enum import StrEnum
from pathlib import Path

from elims_instruments.utils.timestamp import Timestamp


@dataclasses.dataclass
class FileHelper:
    """File helper."""

    class FileSuffix(StrEnum):
        """File suffix."""

        LOG = ".log"
        CSV = ".csv"
        TOML = ".toml"

    directory: Path
    stem: str
    suffix: FileSuffix
    timestamp: Timestamp | None = None

    def __post_init__(self) -> None:
        """Post initialization."""
        if not self.directory.exists():
            self.directory.mkdir(mode=0o777, parents=True, exist_ok=True)

    @property
    def file_name(self) -> str:
        """Return the file name.

        Returns:
            File name with suffix and optional timestamp.
        """
        if self.timestamp is not None:
            return f"{self.stem}_{self.timestamp.file()}{self.suffix.value}".lower()
        return f"{self.stem}{self.suffix.value}".lower()

    @property
    def file_path(self) -> Path:
        """Return the path.

        Returns:
            Full path to the file.
        """
        return self.directory / self.file_name
