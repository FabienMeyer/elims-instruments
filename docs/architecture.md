# Architecture

This document shows the high-level architecture of the `elims_instruments` package.

## Class Diagram (Mermaid UML)

```mermaid
classDiagram
    direction TB
    class Connection {
        <<abstract>>
        +kind: str
    }
    class SocketConnection {
        +ip_address: str
        +port: int
        +mac_address: str | None
        +timeout_seconds: float
    }
    class VisaConnection {
        +resource_name: str
        +timeout_seconds: float
    }
    class ComConnection {
        +port: str
        +baud_rate: int
    }
    class USBConnection {
        +vendor_id: int
        +product_id: int
    }
    class InstrumentModel {
        +id: str
        +type: str
        +maker: str
        +model: str
        +serial_number: str | None
        +connection: Connection
    }
    class BoardModel {
        +id: str
        +type: str
        +maker: str
        +model: str
        +serial_number: str | None
        +connection: Connection
    }

    Connection <|-- SocketConnection
    Connection <|-- VisaConnection
    Connection <|-- ComConnection
    Connection <|-- USBConnection

    InstrumentModel --> Connection : has
    BoardModel --> Connection : has
```

## Sequence (CLI -> CRUD)

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Repo
    User->>CLI: elims instruments add ...
    CLI->>Repo: InstrumentCrud.add(model)
    Repo-->>CLI: stored model
    CLI-->>User: JSON output
```

## Draw.io Diagram

An exported, editable diagram is available at `docs/assets/architecture.svg`.
