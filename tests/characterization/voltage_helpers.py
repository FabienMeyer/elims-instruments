"""Shared builders for voltage and voltage-collection tests."""

from elims_instruments.characterization import VoltageSpecification
from elims_instruments.utils import Limits


def rail_spec(
    name: str = "VDD_CORE",
    *,
    voltage_limits: Limits | None = None,
    current_limits: Limits | None = None,
) -> VoltageSpecification:
    """Build a representative voltage-rail definition."""
    return VoltageSpecification(
        name=name,
        voltage_limits=voltage_limits or Limits(typical=1.2),
        current_limits=current_limits,
    )
