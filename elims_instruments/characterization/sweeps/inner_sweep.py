"""Inner sweep orchestration for a test-specific parameter."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from elims_instruments.bench.duts import Dut

DutT = TypeVar("DutT", bound="Dut")


class InnerMatrix(ABC, Generic[DutT]):
    """Base matrix that supplies a DUT to each test-specific sweep."""

    def __init__(
        self,
        test_id: str,
        dut: DutT,
        iterations: int,
    ) -> None:
        """Store the DUT and validate the one-based test iterations."""
        if not test_id.strip():
            raise ValueError("Inner matrix test_id must not be empty")
        self.test_id = test_id
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

    test_id: str
    dut: DutT
    iteration: int

    @abstractmethod
    def report_header(self) -> list[str]:
        """Return temperature and voltage headers for this operating point."""
        raise NotImplementedError

    @abstractmethod
    def report_value(self) -> list[str]:
        """Return measured operating-condition values in header order."""
        raise NotImplementedError

    @abstractmethod
    def get_test_id(self) -> str:
        """Return the subtest ID including the current sweep iteration."""
        raise NotImplementedError

    def reset(self) -> None:
        """Reset the DUT to a known state."""
        self.dut.reset()

    @abstractmethod
    def run(self) -> tuple[str, Sequence[str]]:
        """Execute this inner measurement and return its report values."""
        raise NotImplementedError
