"""Exceptions raised while resolving projects."""


class ProjectNotFoundError(LookupError):
    """Indicate that a configured project name is absent from the database."""

    def __init__(self, name: str) -> None:
        """Create an error for the unresolved project name."""
        self.name = name
        super().__init__(f"Project not found: {name}")
