# Connections (database)

Shared connection models live in `elims_instruments.database.connections`.

## Models (Mermaid UML)

```mermaid
classDiagram
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
```

## Usage

- Use the `Connection` discriminated union to accept any supported connection.
- `ConnectionType` is a SQLAlchemy `TypeDecorator` that stores validated
  connection models as JSON in the database.
