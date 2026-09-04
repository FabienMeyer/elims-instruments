"""Minimal runtime board implementation for the example project.

This module contains runtime behavior only. Board inventory is still created
and managed separately through the CLI as a ``BoardModel`` record.
"""

from elims_instruments.boards import Board, BoardFactory


class ExampleBoard(Board):
    """Concrete characterization-board implementation."""

    def get_id(self) -> str:
        """Return the persistent database identifier."""
        return self.board.id

    def reset(self) -> None:
        """Reset the board to its known initial state.

        Replace this placeholder with the board-specific reset sequence when
        the example is connected to hardware.
        """


BoardFactory.register("characterization", ExampleBoard)
