"""Reusable numeric limits."""

from __future__ import annotations

import math
from dataclasses import dataclass, fields
from itertools import pairwise
from typing import TypeGuard


@dataclass(frozen=True, slots=True, kw_only=True)
class Limits:
    """A typical value with optional recommended and absolute bounds.

    Only :attr:`typical` is required. Missing bounds are open-ended. Supplied
    values must be finite numbers ordered as follows::

        absolute_minimum <= minimum <= typical <= maximum <= absolute_maximum

    Integers are preserved as integers and booleans are not accepted as
    numeric values.
    """

    absolute_minimum: int | float | None = None
    minimum: int | float | None = None
    typical: int | float
    maximum: int | float | None = None
    absolute_maximum: int | float | None = None

    def __post_init__(self) -> None:
        """Validate every supplied value and their relative ordering."""
        defined_values: list[int | float] = []
        for field in fields(self):
            value = getattr(self, field.name)
            if value is None:
                if field.name == "typical":
                    raise TypeError("Typical must be an integer or float")
                continue
            self._validate_number(value, field.name.replace("_", " "))
            defined_values.append(value)

        if any(lower > upper for lower, upper in pairwise(defined_values)):
            raise ValueError(
                "Limits must satisfy absolute_minimum <= minimum <= typical "
                "<= maximum <= absolute_maximum"
            )

    @classmethod
    def exact(cls, value: int | float) -> Limits:
        """Create a limit whose recommended and absolute bounds equal *value*."""
        _value = cls._validate_number(value, "value")
        return cls(
            absolute_minimum=_value,
            minimum=_value,
            typical=_value,
            maximum=_value,
            absolute_maximum=_value,
        )

    def is_between(self, value: int | float) -> bool:
        """Return whether *value* is finite and within recommended bounds."""
        return self._is_within_bounds(
            value,
            self.minimum,
            self.maximum,
        )

    def __contains__(self, value: object) -> bool:
        """Return whether *value* is a valid number within recommended bounds."""
        return self._is_within_bounds(value, self.minimum, self.maximum)

    def is_between_absolute(self, value: int | float) -> bool:
        """Return whether *value* is finite and within absolute bounds."""
        return self._is_within_bounds(
            value,
            self.absolute_minimum,
            self.absolute_maximum,
        )

    def validate(self, value: int | float, *, label: str = "Value") -> int | float:
        """Return *value* if it is finite and within recommended bounds."""
        return self._validate_within_bounds(
            value,
            label=label,
            range_name="allowed",
            minimum=self.minimum,
            maximum=self.maximum,
        )

    def validate_absolute(
        self,
        value: int | float,
        *,
        label: str = "Value",
    ) -> int | float:
        """Return *value* if it is finite and within absolute bounds."""
        return self._validate_within_bounds(
            value,
            label=label,
            range_name="absolute",
            minimum=self.absolute_minimum,
            maximum=self.absolute_maximum,
        )

    def _validate_within_bounds(
        self,
        value: int | float,
        *,
        label: str,
        range_name: str,
        minimum: int | float | None,
        maximum: int | float | None,
    ) -> int | float:
        """Perform the shared number and range validation."""
        candidate = self._validate_number(value, label)
        if not self._is_within_bounds(candidate, minimum, maximum):
            raise ValueError(
                f"{label.capitalize()} {candidate} is outside the {range_name} range "
                f"{self._format_range(minimum, maximum)}"
            )
        return candidate

    @staticmethod
    def _is_within_bounds(
        value: object,
        minimum: int | float | None,
        maximum: int | float | None,
    ) -> bool:
        """Return whether *value* is within optional inclusive bounds."""
        return (
            Limits._is_valid_number(value)
            and (minimum is None or minimum <= value)
            and (maximum is None or value <= maximum)
        )

    @classmethod
    def _validate_number(
        cls,
        value: int | float,
        label: str,
    ) -> int | float:
        """Return a finite integer or float without changing its type."""
        if cls._is_valid_number(value):
            return value
        if isinstance(value, float):
            raise ValueError(f"{label.capitalize()} must be finite")
        raise TypeError(f"{label.capitalize()} must be an integer or float")

    @staticmethod
    def _is_valid_number(value: object) -> TypeGuard[int | float]:
        """Return whether *value* is a finite non-boolean integer or float."""
        return (
            not isinstance(value, bool)
            and isinstance(value, (int, float))
            and (not isinstance(value, float) or math.isfinite(value))
        )

    @staticmethod
    def _format_range(
        minimum: int | float | None,
        maximum: int | float | None,
    ) -> str:
        """Format optional bounds for an error message."""
        lower = "-infinity" if minimum is None else str(minimum)
        upper = "infinity" if maximum is None else str(maximum)
        return f"[{lower}, {upper}]"
