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

    InstrumentModel --> Connection
    BoardModel --> Connection
```

`bench.toml` maps project-owned `InstrumentName`, `BoardName`, and `DutName`
roles to asset tags. `Bench` validates those names, resolves the assets, and
exposes read-only collections.

```mermaid
flowchart LR
    Project[Project names] --> Config[bench.toml]
    Config --> Bench
    Database[(Asset database)] --> Bench
    Bench --> Instruments
    Bench --> Boards
    Bench --> DUTs
```

The CLI groups use the same validated models and CRUD repositories as the
Python API.

Schema changes are versioned with Alembic and applied with
`elims database upgrade`.
