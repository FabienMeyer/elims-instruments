# Architecture

The database stores physical assets. Instruments and boards can be reused by
many projects; each DUT stores its owning project.

```mermaid
classDiagram
    class InstrumentModel {
        +id: str
        +asset_tag: str
        +type: InstrumentType
        +maker: str
        +model: str
        +connection: Connection
    }
    class BoardModel {
        +id: str
        +asset_tag: str
        +type: str
        +maker: str
        +model: str
        +connection: Connection
    }
    class DutModel {
        +id: str
        +asset_tag: str
        +project: str
        +corner: str
        +revision: str
        +lot_number: str | None
        +wafer_id: str | None
        +die_x: int | None
        +die_y: int | None
    }
    class ProjectModel {
        +id: str
        +name: str
        +supported_duts: list[DutModel]
        +supported_boards: list[BoardModel]
    }

    InstrumentModel --> Connection
    BoardModel --> Connection
    ProjectModel ..> DutModel : supports
    ProjectModel ..> BoardModel : supports
```

`bench.toml` maps project-owned instrument, board, DUT, and project role names
to database identifiers. Asset roles use asset tags; project roles use unique
project names. `Bench` validates those names, resolves the records, and exposes
read-only collections.

```mermaid
flowchart LR
    Project[Project names] --> Config[bench.toml]
    Config --> Bench
    Database[(Asset database)] --> Bench
    Bench --> Instruments
    Bench --> Boards
    Bench --> DUTs
    Bench --> Projects
```

The instrument, board, DUT, and project CLI groups use the same validated
models and CRUD repositories as the Python API.

Schema changes are versioned with Alembic and applied with
`elims database upgrade`.
