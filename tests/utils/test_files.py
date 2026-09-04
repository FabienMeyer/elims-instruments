from datetime import datetime, timedelta, timezone
from pathlib import Path

from elims_instruments.utils.files import FileHelper
from elims_instruments.utils.timestamp import Timestamp


class TestFileHelper:
    """Tests for FileHelper."""

    def test_creates_directory(self, tmp_path: Path) -> None:
        """Test that the directory is created if it does not exist."""
        directory = tmp_path / "nested" / "logs"
        helper = FileHelper(directory, "test_file", FileHelper.FileSuffix.LOG)
        assert directory.is_dir()
        assert not helper.file_path.exists()

    def test_builds_filename_without_timestamp(self, tmp_path: Path) -> None:
        """Test that the file name is built correctly without a timestamp."""
        helper = FileHelper(tmp_path, "Instrument_Result", FileHelper.FileSuffix.LOG)
        assert helper.file_name == "instrument_result.log"
        assert helper.file_path == tmp_path / "instrument_result.log"

    def test_builds_filename_with_timestamp(self, tmp_path: Path) -> None:
        """Test that the file name is built correctly with a timestamp."""
        timestamp = Timestamp(
            datetime(2026, 8, 8, 9, 3, 5, tzinfo=timezone(timedelta(hours=2)))
        )
        helper = FileHelper(
            tmp_path, "Measurement", FileHelper.FileSuffix.LOG, timestamp
        )
        assert helper.file_name == "measurement_2026_08_08_09_03_05.log"
        assert helper.file_path == tmp_path / helper.file_name
