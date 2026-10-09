"""Tests for the database-backed project example."""

from __future__ import annotations

from examples.bench_setup import project as project_example

from elims_instruments.bench import ProjectFactory
from elims_instruments.characterization import (
    ProjectRevisionSpecifications,
    TemperatureSpecification,
    VoltageSpecification,
)
from elims_instruments.database import DutModel, ProjectModel
from elims_instruments.utils import Limits


def _project_with_dut(
    project_id: str,
    internal_name: str,
    dut_id: str,
    die_revision: str,
) -> ProjectModel:
    """Build a project with one matching supported DUT."""
    project = ProjectModel(
        id=project_id,
        internal_name=internal_name,
        datasheet_name=f"{internal_name} IC",
        specifications=[
            ProjectRevisionSpecifications(
                die_revision=die_revision,
                voltage_specifications=(
                    VoltageSpecification("VDD", Limits(typical=1.2)),
                ),
                temperature_specifications=(
                    TemperatureSpecification("DUT", Limits(typical=25)),
                ),
            )
        ],
    )
    project.supported_duts = [
        DutModel(
            id=dut_id,
            asset_tag=f"DUT-{dut_id}",
            project=internal_name,
            corner="TT",
            die_revision=die_revision,
        )
    ]
    return project


def test_main_evaluates_only_each_projects_supported_duts(monkeypatch) -> None:
    """Multiple projects do not apply their profiles to unrelated DUTs."""
    first = _project_with_dut("project-1", "example-project", "001", "A")
    second = _project_with_dut("project-2", "second-project", "002", "B")
    ProjectFactory.register("second-project", project_example.ExampleProject)
    monkeypatch.setattr(project_example, "get_projects", lambda: [first, second])
    monkeypatch.setattr(project_example.LOGGER_HELPER, "configure", lambda: None)

    project_example.main()
