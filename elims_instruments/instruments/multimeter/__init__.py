"""Multimeter drivers package.

This package provides abstract base classes, factory patterns, and concrete
implementations for multimeter instruments.
"""

from .factory import MultimeterFactory as _MultimeterFactory
from .factory import create_multimeter
from .ks34401a import Keysight34401A as _Keysight34401A
from .ks34410a import Keysight34410A as _Keysight34410A
from .ks34465a import Keysight34465A as _Keysight34465A

_MultimeterFactory.register("Keysight 34401A", _Keysight34401A)
_MultimeterFactory.register("34401A", _Keysight34401A)
_MultimeterFactory.register("Keysight 34410A", _Keysight34410A)
_MultimeterFactory.register("34410A", _Keysight34410A)
_MultimeterFactory.register("Keysight 34465A", _Keysight34465A)
_MultimeterFactory.register("34465A", _Keysight34465A)

__all__ = ["create_multimeter"]
