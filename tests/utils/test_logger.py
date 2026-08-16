from pathlib import Path

from elims_instruments.utils.logger import LoggerHelper


class TestLoggerHelper:
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
