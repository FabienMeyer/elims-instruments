"""Abstract base class for thermal test systems."""

from elims_instruments.instruments.abstract import Instrument


class ThermalTestSystem(Instrument):
    """Base class for directed-air and direct-contact thermal test systems."""
