"""Shared error handling for characterization hardware lifecycles."""

from collections.abc import Sequence
from typing import NoReturn


def raise_lifecycle_errors(
    message: str,
    operation_error: BaseException | None,
    cleanup_errors: Sequence[BaseException],
) -> NoReturn:
    """Raise one operation error or group it with every cleanup failure."""
    if operation_error is not None and not cleanup_errors:
        raise operation_error

    errors = [*(() if operation_error is None else (operation_error,)), *cleanup_errors]
    raise BaseExceptionGroup(message, errors)
