"""Exceptions raised while loading laboratory bench configuration."""

from pathlib import Path
from typing import Self


class BenchConfigurationError(ValueError):
    """Raised when a bench configuration is invalid."""

    @classmethod
    def invalid_file(cls, configuration: Path) -> Self:
        """Create an error for a missing or malformed TOML file."""
        return cls(f"Invalid bench configuration: {configuration}")

    @classmethod
    def invalid_authorized_names(cls) -> Self:
        """Create an error for non-string authorized names."""
        return cls("Authorized bench names must be strings")

    @classmethod
    def missing_instruments_table(cls) -> Self:
        """Create an error for a missing ``[instruments]`` table."""
        return cls("bench.toml must contain an [instruments] table")

    @classmethod
    def unauthorized_board_name(cls, name: object) -> Self:
        """Create an error for a board name outside the project's allowlist."""
        return cls(f"Unauthorized board name: {name!r}")

    @classmethod
    def unauthorized_dut_name(cls, name: object) -> Self:
        """Create an error for a DUT name outside the project's allowlist."""
        return cls(f"Unauthorized DUT name: {name!r}")

    @classmethod
    def invalid_board_name(cls, name: object) -> Self:
        """Create an error for an invalid or reserved Python board name."""
        return cls(f"Invalid or reserved board name: {name!r}")

    @classmethod
    def invalid_dut_name(cls, name: object) -> Self:
        """Create an error for an invalid or reserved Python DUT name."""
        return cls(f"Invalid or reserved DUT name: {name!r}")

    @classmethod
    def unauthorized_name(cls, name: object) -> Self:
        """Create an error for a name outside the project's allowlist."""
        return cls(f"Unauthorized instrument name: {name!r}")

    @classmethod
    def invalid_name(cls, name: object) -> Self:
        """Create an error for an invalid or reserved Python name."""
        return cls(f"Invalid or reserved instrument name: {name!r}")

    @classmethod
    def invalid_asset_tag(cls, name: str) -> Self:
        """Create an error for an empty or non-string asset tag."""
        return cls(f"Asset tag for {name!r} must be a non-empty string")

    @classmethod
    def duplicate_asset_tag(cls, asset_tag: str) -> Self:
        """Create an error for an asset assigned to multiple names."""
        return cls(f"Asset tag is assigned more than once: {asset_tag}")
