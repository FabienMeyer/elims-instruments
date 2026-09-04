"""Inner sweep orchestration for a test-specific parameter."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from collections.abc import Iterator

    from elims_instruments.duts import Dut

DutT = TypeVar("DutT", bound="Dut")


class InnerMatrix(ABC, Generic[DutT]):
    """Base matrix that supplies a DUT to each test-specific sweep."""

    def __init__(
        self,
        dut: DutT,
        iterations: int,
    ) -> None:
        """Store the DUT and validate the one-based test iterations."""
        if iterations < 1:
            raise ValueError("Inner matrix iterations must be at least one")
        self.dut = dut
        self.iterations = range(1, iterations + 1)

    @abstractmethod
    def __iter__(self) -> Iterator[InnerSweep[DutT]]:
        """Yield the test-specific arguments for every iteration."""


@dataclass(frozen=True, slots=True)
class InnerSweep(Generic[DutT]):
    """Shared values present in every test-specific inner sweep."""

    dut: DutT
    iteration: int

    def reset(self) -> None:
        """Reset the DUT to a known state."""
        self.dut.reset()
