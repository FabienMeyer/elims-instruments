"""Revision identifiers shared by DUTs and characterization profiles."""

from typing import Annotated

from pydantic import BeforeValidator, StringConstraints


def _normalize_revision(value: object) -> object:
    """Normalize string revision values before pattern validation."""
    return value.strip().upper() if isinstance(value, str) else value


DieRevision = Annotated[
    str,
    BeforeValidator(_normalize_revision),
    StringConstraints(pattern=r"^[A-Z]+$"),
]
PackageRevision = Annotated[
    str,
    BeforeValidator(_normalize_revision),
    StringConstraints(pattern=r"^R[1-9]\d*$"),
]

