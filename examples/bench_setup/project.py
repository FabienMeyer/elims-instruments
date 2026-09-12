"""Runtime implementation for the demo characterization project."""

from elims_instruments.bench import Project, ProjectFactory
from examples.bench_setup.constants import PROJECT_DRIVER_NAME


class ExampleProject(Project):
    """Concrete runtime behavior for the demo project."""

    def get_id(self) -> str:
        """Return the persistent project identifier."""
        return self.project.id

    def describe(self) -> str:
        """Return a human-readable project description."""
        return (
            f"{self.project.datasheet_name} "
            f"(internal name: {self.project.internal_name})"
        )


ProjectFactory.register(PROJECT_DRIVER_NAME, ExampleProject)
