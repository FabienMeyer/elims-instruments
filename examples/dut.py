"""Minimal runtime DUT implementation for the example project.

This module contains runtime behavior only. DUT inventory is still created and
managed separately through the CLI as a ``DutModel`` record.
"""

from elims_instruments.duts import Dut, DutFactory


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


DutFactory.register("example-project", ExampleDut)

