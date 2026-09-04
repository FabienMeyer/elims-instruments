"""Tests for reusable numeric limits."""

from dataclasses import FrozenInstanceError

import pytest

from elims_instruments.utils import Limits


def complete_limit() -> Limits:
    """Return a limit with recommended and absolute bounds."""
    return Limits(
        absolute_minimum=0,
        minimum=1,
        typical=1.5,
        maximum=2,
        absolute_maximum=3,
    )


def test_limit_exposes_supplied_values() -> None:
    """All five specification values are retained without conversion."""
    limit = complete_limit()

    assert limit.absolute_minimum == 0
    assert limit.minimum == 1
    assert limit.typical == 1.5
    assert limit.maximum == 2
    assert limit.absolute_maximum == 3


def test_recommended_range_is_inclusive() -> None:
    """Recommended minimum and maximum values are accepted."""
    limit = complete_limit()

    assert limit.is_between(1)
    assert limit.is_between(1.5)
    assert limit.is_between(2)
    assert 1 in limit
    assert 0.5 not in limit


def test_absolute_range_is_distinct_from_recommended_range() -> None:
    """A value outside recommendations can remain inside absolute bounds."""
    limit = complete_limit()

    assert not limit.is_between(0.5)
    assert limit.is_between_absolute(0.5)
    assert limit.validate_absolute(0.5, label="measurement") == 0.5


def test_validation_reports_value_label_and_range() -> None:
    """An out-of-range error identifies the failed specification."""
    limit = complete_limit()

    with pytest.raises(ValueError, match=r"Measurement 3.*allowed range \[1, 2\]"):
        limit.validate(3, label="measurement")
    with pytest.raises(ValueError, match=r"Value 4.*absolute range \[0, 3\]"):
        limit.validate_absolute(4)


def test_only_typical_is_required() -> None:
    """Omitted bounds leave both ranges open-ended."""
    limit = Limits(typical=1.2)

    assert limit.minimum is None
    assert limit.maximum is None
    assert limit.is_between(-100)
    assert limit.is_between_absolute(100)
    assert limit.validate(-100) == -100


@pytest.mark.parametrize(
    ("limit", "accepted", "rejected"),
    [
        (Limits(typical=1.2, minimum=0.8), 2, 0.7),
        (Limits(typical=1.2, maximum=1.4), 0.7, 1.5),
        (Limits(typical=1.2, absolute_minimum=0.5), 2, 0.4),
        (Limits(typical=1.2, absolute_maximum=1.5), 0.4, 1.6),
    ],
)
def test_one_sided_bounds(
    limit: Limits,
    accepted: int | float,
    rejected: int | float,
) -> None:
    """Each supplied bound constrains only its corresponding side."""
    if limit.minimum is not None or limit.maximum is not None:
        assert limit.is_between(accepted)
        assert not limit.is_between(rejected)
    else:
        assert limit.is_between_absolute(accepted)
        assert not limit.is_between_absolute(rejected)


@pytest.mark.parametrize(
    "values",
    [
        (0, 2, 1, 3, 4),
        (0, 1, 3, 2, 4),
        (0, 1, 2, 4, 3),
        (2, None, 1, None, 4),
        (0, None, 5, None, 4),
    ],
)
def test_limit_rejects_values_in_the_wrong_order(
    values: tuple[int | None, ...],
) -> None:
    """Defined values must retain their logical ordering when fields are absent."""
    absolute_minimum, minimum, typical, maximum, absolute_maximum = values

    with pytest.raises(ValueError, match="must satisfy"):
        Limits(
            absolute_minimum=absolute_minimum,
            minimum=minimum,
            typical=typical,
            maximum=maximum,
            absolute_maximum=absolute_maximum,
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_limit_rejects_non_finite_values(value: float) -> None:
    """Neither specifications nor validated values may be non-finite."""
    with pytest.raises(ValueError, match="finite"):
        Limits(typical=value)

    limit = Limits(typical=1)
    assert not limit.is_between(value)
    assert value not in limit
    with pytest.raises(ValueError, match="finite"):
        limit.validate(value)


@pytest.mark.parametrize("value", [True, False, "1", None])
def test_limit_rejects_non_numeric_values(value: object) -> None:
    """Booleans and non-numeric objects are not treated as numbers."""
    with pytest.raises(TypeError, match="integer or float"):
        Limits(typical=value)  # type: ignore[arg-type]

    limit = Limits(typical=1)
    assert value not in limit


def test_integer_values_preserve_their_type() -> None:
    """Integer specifications and measurements remain integers."""
    limit = Limits(typical=8, minimum=0, maximum=16)

    assert isinstance(limit.typical, int)
    assert isinstance(limit.minimum, int)
    assert isinstance(limit.validate(12), int)


def test_exact_limit_sets_every_bound() -> None:
    """An exact limit represents one immutable accepted value."""
    limit = Limits.exact(3.3)

    assert limit == Limits(
        absolute_minimum=3.3,
        minimum=3.3,
        typical=3.3,
        maximum=3.3,
        absolute_maximum=3.3,
    )
    assert 3.3 in limit
    assert 3.2 not in limit


def test_limit_is_immutable_and_hashable() -> None:
    """Limits are safe reusable value objects."""
    limit = Limits(typical=1)

    assert {limit} == {Limits(typical=1)}
    with pytest.raises(FrozenInstanceError):
        limit.typical = 2  # type: ignore[misc]
