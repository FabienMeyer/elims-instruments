"""Counter drivers package.

This package provides abstract base classes, factory patterns, and concrete
implementations for counter instruments.
"""

from .factory import CounterFactory as _CounterFactory
from .factory import create_counter
from .ks53220a import Keysight53220A as _Keysight53220A

_CounterFactory.register("Keysight 53220A", _Keysight53220A)
_CounterFactory.register("53220A", _Keysight53220A)

__all__ = ["create_counter"]
