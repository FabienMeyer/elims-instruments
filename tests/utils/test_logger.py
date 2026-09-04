from pathlib import Path

from elims_instruments.utils.logger import (
    CLI_LOGGER_HELPER,
    LoggerHelper,
    get_cli_logger,
    get_logger,
)


class TestLoggerHelper:
    def test_get_logger_reuses_bound_logger(self) -> None:
        assert get_logger("bench") is get_logger("bench")

    def test_cli_logger_is_shared_and_rotates_at_ten_megabytes(self) -> None:
        assert get_cli_logger() is get_cli_logger()
        assert CLI_LOGGER_HELPER.rotation == "10 MB"

    def test_file_format(self, tmp_path: Path) -> None:
        helper = LoggerHelper(
            name="app",
            color=LoggerHelper.Color.CYAN,
            file_directory=tmp_path / "logs",
            file_level=LoggerHelper.Level.DEBUG,
            terminal_level=LoggerHelper.Level.DEBUG,
        )
        helper.configure()
        expected = (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{extra[source]: <16} | {name}:{function}:{line} - {message}"
            "{exception}"
        )

        assert helper.file_format() == expected

    def test_terminal_format(self, tmp_path: Path) -> None:
        helper = LoggerHelper(
            name="app",
            color=LoggerHelper.Color.CYAN,
            file_directory=tmp_path / "logs",
            file_level=LoggerHelper.Level.DEBUG,
            terminal_level=LoggerHelper.Level.DEBUG,
        )
        helper.configure()
        record = {
            "name": "app",
            "message": "Starting application",
            "extra": {"source_color": LoggerHelper.Color.BLUE.value},
            "time": None,
        }

        formatted = helper.terminal_format(record)

        assert "<blue>{extra[source]: <16}</blue>" in formatted
        assert "<blue>{message}</blue>" in formatted

    def test_configure_file(self, tmp_path: Path) -> None:
        helper = LoggerHelper(
            name="app",
            color=LoggerHelper.Color.CYAN,
            file_directory=tmp_path / "logs",
            file_level=LoggerHelper.Level.DEBUG,
            terminal_level=LoggerHelper.Level.DEBUG,
        )
        helper.configure()
        assert helper._file_sink_id is not None

    def test_configure_terminal(self, tmp_path: Path) -> None:
        helper = LoggerHelper(
            name="app",
            color=LoggerHelper.Color.CYAN,
            file_directory=tmp_path / "logs",
            file_level=LoggerHelper.Level.DEBUG,
            terminal_level=LoggerHelper.Level.DEBUG,
        )
        helper.configure()
        assert helper._terminal_sink_id is not None
