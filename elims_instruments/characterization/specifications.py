"""Revision-dependent electrical and thermal characterization parameters."""

from typing import Self

from pydantic import BaseModel, Field, model_validator

from elims_instruments.utils import Limits

from .revisions import DieRevision, PackageRevision
from .temperatures import TemperatureSpecification
from .voltages import VoltageSpecification


class ProjectRevisionSpecifications(BaseModel):
    """Electrical and thermal specifications for one exact DUT revision."""

    die_revision: DieRevision
    metal_revision: int | None = Field(default=None, ge=0)
    package_revision: PackageRevision | None = None
    voltage_specifications: tuple[VoltageSpecification, ...]
    temperature_specifications: tuple[TemperatureSpecification, ...]

    @model_validator(mode="after")
    def validate_specifications(self) -> Self:
        """Require named voltage and temperature specifications without duplicates."""
        for kind, specifications in (
            ("voltage", self.voltage_specifications),
            ("temperature", self.temperature_specifications),
        ):
            if not specifications:
                raise ValueError(f"At least one {kind} specification is required")
            names = [
                specification.name.strip().casefold()
                for specification in specifications
            ]
            if any(not name for name in names):
                raise ValueError(
                    f"{kind.capitalize()} specification names cannot be empty"
                )
            if len(names) != len(set(names)):
                raise ValueError(f"Duplicate {kind} specification names")
        return self


ProjectRevisionSpecifications.model_rebuild(_types_namespace={"Limits": Limits})
