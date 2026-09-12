"""Minimal runtime DUT implementation for the example project.

This module contains runtime behavior only. DUT inventory is still created and
managed separately through the CLI as a ``DutModel`` record.
"""

from elims_instruments.bench import Dut, DutFactory
from elims_instruments.database import DutModel
from examples.bench_setup.constants import PROJECT_DRIVER_NAME


class ExampleDut(Dut):
    """Concrete DUT implementation for the ``demo-project`` example."""

    def get_id(self) -> str:
        """Return the persistent database identifier."""
        return self.dut.id

    def reset(self) -> None:
        """Reset the DUT to its known initial state.

        Replace this placeholder with the project-specific reset sequence when
        the example is connected to hardware.
        """
        super().reset()


DutFactory.register(PROJECT_DRIVER_NAME, ExampleDut)


def create_example_dut() -> ExampleDut:
    """Create the simulated DUT reused by the sweep examples."""
    return ExampleDut(
        DutModel(
            id="example-dut",
            asset_tag="DUT-001",
            project=PROJECT_DRIVER_NAME,
            corner="TT",
            die_revision="A",
            metal_revision="0",
            package_revision="R1",
            serial_number="1",
        )
    )
