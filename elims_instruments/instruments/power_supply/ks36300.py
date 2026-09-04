"""Keysight E36300 series power supplies base driver."""

from elims_instruments.instruments.power_supply.abstract import PowerSupply


class KeysightE36300(PowerSupply):
    """Keysight E36300 series triple-output DC power supplies."""

    def connect(self) -> None:
        """Open connection to instrument."""
        raise NotImplementedError

    def disconnect(self) -> None:
        """Close connection to instrument."""
        raise NotImplementedError

    def get_id(self) -> str:
        """Get instrument identification.

        Returns:
            Identification string
        """
        raise NotImplementedError
