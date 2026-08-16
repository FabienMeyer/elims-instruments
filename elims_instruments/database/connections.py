"""Shared connection models and DB JSON type."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import TypeAdapter
from sqlalchemy import JSON, Column
from sqlalchemy.types import TypeDecorator
from sqlmodel import Field, SQLModel

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.engine.interfaces import Dialect


class SocketConnection(SQLModel):
    """Socket connection settings."""

    kind: Literal["socket"] = "socket"
    ip_address: str = Field(
        min_length=1,
        max_length=15,
        regex=r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$",
    )
    port: int = Field(ge=1, le=65535)
    mac_address: str | None = Field(
        default=None,
        min_length=1,
        max_length=17,
        regex=r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$",
    )
    timeout_seconds: float = Field(default=5.0, gt=0)


class VisaConnection(SQLModel):
    """VISA connection settings."""

    kind: Literal["visa"] = "visa"
    resource_name: str = Field(min_length=1)
    timeout_seconds: float = Field(default=30.0, gt=0)
    read_termination: str | None = "\n"
    write_termination: str | None = "\n"

    @property
    def timeout_milliseconds(self) -> int:
        return round(self.timeout_seconds * 1_000)


class ComConnection(SQLModel):
    """Serial (COM) connection settings."""

    kind: Literal["com"] = "com"
    port: str = Field(min_length=1)
    baud_rate: int = Field(default=9600, ge=110, le=460800)
    bytesize: int = Field(default=8, ge=5, le=8)
    stop_bits: float = Field(default=1.0, gt=0)
    parity: str | None = Field(default="N", min_length=1, max_length=1)
    timeout_seconds: float = Field(default=5.0, gt=0)


class USBConnection(SQLModel):
    """USB connection settings."""

    kind: Literal["usb"] = "usb"
    vendor_id: int = Field(ge=0)
    product_id: int = Field(ge=0)
    serial_number: str | None = Field(default=None, min_length=1)
    interface: int | None = Field(default=None, ge=0)
    timeout_seconds: float = Field(default=10.0, gt=0)


class ConnectionKind(StrEnum):
    SOCKET = "socket"
    VISA = "visa"
    COM = "com"
    USB = "usb"


Connection = Annotated[
    SocketConnection | VisaConnection | ComConnection | USBConnection,
    Field(discriminator="kind"),
]

_CONNECTION_ADAPTER: TypeAdapter[Connection] = TypeAdapter(Connection)
_RAW_CONNECTION_LIST_ADAPTER: TypeAdapter[list[dict[str, object]]] = TypeAdapter(
    list[dict[str, object]]
)


class ConnectionType(TypeDecorator[Connection]):
    """Store a validated connection model in a JSON database column."""

    impl = JSON
    cache_ok = True

    def process_bind_param(self, value: Connection | None, dialect: 'Dialect'):
        del dialect
        return None if value is None else value.model_dump(mode="json")

    def process_result_value(self, value: dict[str, Any] | None, dialect: 'Dialect'):
        del dialect
        return None if value is None else _CONNECTION_ADAPTER.validate_python(value)


__all__ = [
    "SocketConnection",
    "VisaConnection",
    "ComConnection",
    "USBConnection",
    "Connection",
    "ConnectionKind",
    "ConnectionType",
]
