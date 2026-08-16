# Instruments (database)

Models and repository for instruments: `elims_instruments.database.instrument`.

## InstrumentModel

Fields:

- `id`: str (primary key)
- `type`: str
- `maker`: str
- `model`: str
- `serial_number`: Optional[str]
- `connection`: `Connection` (see Connections)

```mermaid
classDiagram
    class InstrumentModel {
        +id: str
        +type: str
        +maker: str
        +model: str
        +serial_number: str | None
        +connection: Connection
    }
```

## InstrumentCrud

Provides `add`, `fetch`, `fetchall`, `update`, `remove`, and `upsert_many`.
