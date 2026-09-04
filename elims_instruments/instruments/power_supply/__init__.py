"""Power-supply drivers package."""

from .factory import PowerSupplyFactory as _PowerSupplyFactory
from .factory import create_power_supply
from .ks36313a import KeysightE36313A as _KeysightE36313A

_PowerSupplyFactory.register("Keysight E36313A", _KeysightE36313A)
_PowerSupplyFactory.register("E36313A", _KeysightE36313A)

__all__ = ["create_power_supply"]
