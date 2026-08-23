"""Loguru configuration helpers."""

from __future__ import annotations

import dataclasses
from contextlib import suppress
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from sys import stderr
from typing import TYPE_CHECKING, Protocol, cast

from loguru import logger

from elims_instruments.utils.files import FileHelper
from elims_instruments.utils.timestamp import Timestamp

if TYPE_CHECKING:
    from loguru import Record


class Logger(Protocol):
    """Typed logging operations exposed to application modules."""

    def debug(self, message: str, *args: object, **kwargs: object) -> None:
        """Log a diagnostic message."""
        ...

    def info(self, message: str, *args: object, **kwargs: object) -> None:
        """Log an informational message."""
        ...

    def warning(self, message: str, *args: object, **kwargs: object) -> None:
        """Log a warning message."""
        ...

    def error(self, message: str, *args: object, **kwargs: object) -> None:
        """Log an error message."""
        ...


@dataclasses.dataclass
class LoggerHelper:
    """Configure shared Loguru sinks."""

    name: str
    color: LoggerHelper.Color
    file_directory: Path
    file_level: LoggerHelper.Level
    terminal_level: LoggerHelper.Level
    rotation: str | int | None = None

    class Color(StrEnum):
        """Colors for log messages."""

        BLACK = "black"
        BLUE = "blue"
        CYAN = "cyan"
        GREEN = "green"
        LIGHT_BLACK = "light-black"
        LIGHT_BLUE = "light-blue"
        LIGHT_CYAN = "light-cyan"
        LIGHT_GREEN = "light-green"
        LIGHT_MAGENTA = "light-magenta"
        LIGHT_RED = "light-red"
        LIGHT_WHITE = "light-white"
        LIGHT_YELLOW = "light-yellow"
        MAGENTA = "magenta"
        RED = "red"
        WHITE = "white"
        YELLOW = "yellow"

    class Level(StrEnum):
        """Log levels supported."""

        TRACE = "TRACE"
        DEBUG = "DEBUG"
        INFO = "INFO"
        SUCCESS = "SUCCESS"
        WARNING = "WARNING"
        ERROR = "ERROR"
        CRITICAL = "CRITICAL"

    def __post_init__(self) -> None:
        """Create the log file description and contextual logger."""
        self._terminal_sink_id: int | None = None
        self._file_sink_id: int | None = None

    def configure(self) -> None:
        """Configure the logger with terminal and file sinks."""
        self.file = FileHelper(
            self.file_directory, self.name, FileHelper.FileSuffix.LOG, Timestamp.now()
        )
        self.configure_terminal_logger()
        self.configure_file_logger()
        self._logger = cast(
            "Logger",
            logger.bind(
                source=self.name,
                source_color=self.color.value,
            ),
        )

    def logger(self) -> Logger:
        """Return this helper's contextual Loguru logger.

        Returns:
            A Loguru logger bound to this helper's source and color.
        """
        return self._logger

    def terminal_format(self, record: Record) -> str:
        """Select the terminal color from the logger's bound context.

        Args:
            record: The log record to format.
        Returns:
            A formatted log string with the appropriate color.
        """
        record["extra"].setdefault("source", record["name"])
        color = record["extra"].get("source_color", self.color.value)
        return (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            f"<{color}>{{extra[source]: <16}}</{color}> | "
            f"<{color}>{{message}}</{color}>\n"
            "{exception}"
        )

    def configure_terminal_logger(self) -> None:
        """Add a colored terminal sink unless it is already configured."""
        if self._terminal_sink_id is None:
            # Replace Loguru's initial stderr handler to avoid duplicate output.
            with suppress(ValueError):
                logger.remove(0)
            self._terminal_sink_id = logger.add(
                stderr,
                level=self.terminal_level.value,
                format=self.terminal_format,
                colorize=True,
            )

    def file_format(self) -> str:
        """Return the plain-text log format.

        Returns:
            A string representing the plain-text log format.
        """
        return (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{extra[source]: <16} | {name}:{function}:{line} - {message}"
            "{exception}"
        )

    def configure_file_logger(self) -> None:
        """Add a UTF-8 file sink unless it is already configured."""
        if self._file_sink_id is None:
            self._file_sink_id = logger.add(
                self.file.file_path,
                level=self.file_level.value,
                format=self.file_format(),
                encoding="utf-8",
                rotation=self.rotation,
            )

    def bind(self, source: str, source_color: Color) -> Logger:
        """Return a logger bound to the given source and color.

        Args:
            source: The source name to bind to the logger.
            source_color: The color to bind to the logger.
        Returns:
            A logger bound to the given source and color.
        """
        return cast(
            "Logger",
            logger.bind(source=source, source_color=source_color.value),
        )


LOGGER_HELPER = LoggerHelper(
    name="api",
    color=LoggerHelper.Color.CYAN,
    file_directory=Path("logs"),
    file_level=LoggerHelper.Level.DEBUG,
    terminal_level=LoggerHelper.Level.DEBUG,
)

CLI_LOGGER_HELPER = LoggerHelper(
    name="cli",
    color=LoggerHelper.Color.MAGENTA,
    file_directory=Path("logs"),
    file_level=LoggerHelper.Level.DEBUG,
    terminal_level=LoggerHelper.Level.WARNING,
    rotation="10 MB",
)


@lru_cache
def get_logger(
    source: str,
    source_color: LoggerHelper.Color = LoggerHelper.Color.CYAN,
) -> Logger:
    """Return a cached logger bound through the shared logger helper.

    Sink configuration remains the application's responsibility through
    ``LOGGER_HELPER.configure()``. Bound loggers automatically use those sinks
    once configured.
    """
    return LOGGER_HELPER.bind(source, source_color)


@lru_cache
def get_cli_logger() -> Logger:
    """Configure and return the shared rotating CLI logger."""
    CLI_LOGGER_HELPER.configure()
    return CLI_LOGGER_HELPER.logger()
