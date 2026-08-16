from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from elims_instruments.utils.timestamp import Timestamp


class TestTimestamp:
    """Tests for Timestamp."""

    def test_stores_datetime(self) -> None:
        value = datetime(2026, 8, 8, 9, 3, 5, tzinfo=UTC)
        timestamp = Timestamp(value)
        assert timestamp.value is value

    def test_now_uses_local_timezone(self) -> None:
        localized = datetime(2026, 8, 8, 9, 3, 5, tzinfo=timezone(timedelta(hours=2)))
        utc_now = localized.astimezone(UTC)
        with patch("elims_instruments.utils.timestamp.datetime") as datetime_mock:
            datetime_mock.now.return_value = utc_now
            timestamp = Timestamp.now()
        datetime_mock.now.assert_called_once_with()
        assert timestamp.value == localized

    def test_returns_iso_8601_representation(self) -> None:
        timestamp = Timestamp(
            datetime(2026, 8, 8, 9, 3, 5, 123456, tzinfo=timezone(timedelta(hours=2)))
        )
        assert timestamp.iso() == "2026-08-08T09:03:05.123456+02:00"

    def test_returns_filename_representation(self) -> None:
        timestamp = Timestamp(datetime(2026, 8, 8, 9, 3, 5, tzinfo=UTC))
        assert timestamp.file() == "2026_08_08_09_03_05"

    def test_is_immutable(self) -> None:
        timestamp = Timestamp(datetime(2026, 8, 8, 9, 3, 5, tzinfo=UTC))
        with pytest.raises(FrozenInstanceError):
            timestamp.value = datetime.now(UTC)
