"""Build validated connections from grouped CLI options."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

import typer
from pydantic import ValidationError

from elims_instruments.database import (
    ComConnection,
    Connection,
    ConnectionKind,
    SocketConnection,
    USBConnection,
    VisaConnection,
)

ValueT = TypeVar("ValueT")


@dataclass(frozen=True, kw_only=True)
class SocketConnectionOptions:
    """Command-line values used to build a socket connection."""

    ip_address: str | None = None
    port: int | None = None
    mac_address: str | None = None
    timeout_seconds: float | None = None


@dataclass(frozen=True, kw_only=True)
class ComConnectionOptions:
    """Command-line values used to build a serial connection."""

    port: str | None = None
    baud_rate: int | None = None
    bytesize: int | None = None
    stop_bits: float | None = None
    parity: str | None = None
    timeout_seconds: float | None = None


@dataclass(frozen=True, kw_only=True)
class USBConnectionOptions:
    """Command-line values used to build a USB connection."""

    vendor_id: int | None = None
    product_id: int | None = None
    serial_number: str | None = None
    interface: int | None = None
    timeout_seconds: float | None = None


@dataclass(frozen=True, kw_only=True)
class VisaConnectionOptions:
    """Command-line values used to build a VISA connection."""

    resource_name: str | None = None
    timeout_seconds: float | None = None


def _value_or_default(value: ValueT | None, default: ValueT) -> ValueT:
    """Use a model default only when the CLI option was omitted."""
    return default if value is None else value


def _build_socket(options: SocketConnectionOptions) -> SocketConnection:
    if options.ip_address is None or options.port is None:
        raise typer.BadParameter(
            "socket connections require --ip-address and --port",
            param_hint="--connection",
        )
    return SocketConnection(
        ip_address=options.ip_address,
        port=options.port,
        mac_address=options.mac_address,
        timeout_seconds=_value_or_default(options.timeout_seconds, 5.0),
    )


def _build_com(options: ComConnectionOptions) -> ComConnection:
    if options.port is None:
        raise typer.BadParameter(
            "com connections require --com-port",
            param_hint="--connection",
        )
    return ComConnection(
        port=options.port,
        baud_rate=_value_or_default(options.baud_rate, 9600),
        bytesize=_value_or_default(options.bytesize, 8),
        stop_bits=_value_or_default(options.stop_bits, 1.0),
        parity=_value_or_default(options.parity, "N"),
        timeout_seconds=_value_or_default(options.timeout_seconds, 5.0),
    )


def _build_usb(options: USBConnectionOptions) -> USBConnection:
    if options.vendor_id is None or options.product_id is None:
        raise typer.BadParameter(
            "usb connections require --vendor-id and --product-id",
            param_hint="--connection",
        )
    return USBConnection(
        vendor_id=options.vendor_id,
        product_id=options.product_id,
        serial_number=options.serial_number,
        interface=options.interface,
        timeout_seconds=_value_or_default(options.timeout_seconds, 10.0),
    )


def _build_visa(options: VisaConnectionOptions) -> VisaConnection:
    if options.resource_name is None:
        raise typer.BadParameter(
            "VISA connections require --resource-name",
            param_hint="--connection",
        )
    return VisaConnection(
        resource_name=options.resource_name,
        timeout_seconds=_value_or_default(options.timeout_seconds, 30.0),
    )


def build_connection(
    kind: ConnectionKind,
    *,
    socket: SocketConnectionOptions | None = None,
    com: ComConnectionOptions | None = None,
    usb: USBConnectionOptions | None = None,
    visa: VisaConnectionOptions | None = None,
) -> Connection:
    """Build the selected connection from its type-specific option group."""
    try:
        match kind:
            case ConnectionKind.SOCKET:
                return _build_socket(socket or SocketConnectionOptions())
            case ConnectionKind.COM:
                return _build_com(com or ComConnectionOptions())
            case ConnectionKind.USB:
                return _build_usb(usb or USBConnectionOptions())
            case ConnectionKind.VISA:
                return _build_visa(visa or VisaConnectionOptions())
    except ValidationError as error:
        raise typer.BadParameter(str(error), param_hint="--connection") from error

    raise typer.BadParameter(
        f"unsupported connection kind: {kind}",
        param_hint="--connection",
    )
