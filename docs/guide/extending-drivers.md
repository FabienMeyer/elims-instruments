# Extending drivers

Factories separate persisted identity from project-specific behavior. Concrete
implementations are registered once during application startup, before loading a
bench.

## Add an instrument model

Instrument categories have a category factory and, where useful, a family base
class. A concrete driver inherits its category/family behavior:

```python
from elims_instruments.instruments.power_supply.ks36300 import KeysightE36300


class KeysightE36399A(KeysightE36300):
    """Driver for a hypothetical E36399A model."""
```

Register every accepted database model spelling in the package initializer:

```python
PowerSupplyFactory.register("Keysight E36399A", KeysightE36399A)
PowerSupplyFactory.register("E36399A", KeysightE36399A)
```

Model lookup strips whitespace and ignores case.

## Add a DUT implementation

`Dut` is an abstract base class. A concrete class must implement `get_id()` and
may add project-specific register maps or limits.

```python
from elims_instruments.duts import Dut, DutFactory


class CharacterizationDut(Dut):
    def get_id(self) -> str:
        return self.dut.id


DutFactory.register("demo-project", CharacterizationDut)
```

The registry key matches `DutModel.project`.

## Add a project implementation

`Project` is also abstract. Concrete projects can expose sequences or domain
operations while retaining the validated `ProjectModel` relationship data.

```python
from elims_instruments.projects import Project, ProjectFactory


class CharacterizationProject(Project):
    def get_id(self) -> str:
        return self.project.id


ProjectFactory.register("demo-project", CharacterizationProject)
```

The registry key matches `ProjectModel.internal_name`; `datasheet_name` is the
client-facing name and does not affect driver selection.

## Registration guidance

- Register builders during deterministic application startup.
- Keep database records free of executable Python import paths.
- Reject unknown models/projects rather than selecting a vaguely compatible driver.
- Unit-test aliases, invalid registrations, and the concrete type returned.
- Keep hardware communication out of constructors so bench loading is predictable.
