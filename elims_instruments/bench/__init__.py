"""Named laboratory bench configuration."""

from .bench import Bench
from .error import BenchConfigurationError

__all__ = [
    "Bench",
    "BenchConfigurationError",
]
