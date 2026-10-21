"""Build validated connections from grouped CLI options."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
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


class InstrumentConnectionKind(StrEnum):
    """Connection types supported by instrument CLI commands."""

    SOCKET = "socket"
    VISA = "visa"


class BoardConnectionKind(StrEnum):
    """Connection types supported by board CLI commands."""

    SOCKET = "socket"
    COM = "com"
    USB = "usb"


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


ConnectionOptions = (
    SocketConnectionOptions
    | ComConnectionOptions
    | USBConnectionOptions
    | VisaConnectionOptions
)


def _provided_options(options: ConnectionOptions | None) -> list[str]:
    """Return explicitly supplied type-specific options, excluding shared timeout."""
    if options is None:
        return []
    return [
        f"--{field.replace('_', '-')}"
        for field, value in vars(options).items()
        if field != "timeout_seconds" and value is not None
    ]


def _has_options(options: ConnectionOptions | None) -> bool:
    """Report whether any value was supplied for an option group."""
    return options is not None and any(
        value is not None for value in vars(options).values()
    )


def _reject_unselected_options(
    selected: ConnectionKind,
    groups: tuple[tuple[ConnectionKind, ConnectionOptions | None], ...],
) -> None:
    """Reject options that belong to a different connection type."""
    unexpected = [
        option
        for kind, options in groups
        if kind is not selected
        for option in _provided_options(options)
    ]
    if unexpected:
        raise typer.BadParameter(
            f"{selected.value} connections do not accept {', '.join(unexpected)}",
            param_hint="--connection",
        )


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
    kind: ConnectionKind | str,
    *,
    socket: SocketConnectionOptions | None = None,
    com: ComConnectionOptions | None = None,
    usb: USBConnectionOptions | None = None,
    visa: VisaConnectionOptions | None = None,
) -> Connection:
    """Build the selected connection from its type-specific option group."""
    try:
        selected = ConnectionKind(kind)
    except ValueError as error:
        raise typer.BadParameter(
            f"unsupported connection kind: {kind}",
            param_hint="--connection",
        ) from error

    groups = (
        (ConnectionKind.SOCKET, socket),
        (ConnectionKind.COM, com),
        (ConnectionKind.USB, usb),
        (ConnectionKind.VISA, visa),
    )
    _reject_unselected_options(selected, groups)
    try:
        match selected:
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

    raise AssertionError("all connection kinds must be handled")


def build_optional_connection(
    kind: ConnectionKind | str | None,
    *,
    socket: SocketConnectionOptions | None = None,
    com: ComConnectionOptions | None = None,
    usb: USBConnectionOptions | None = None,
    visa: VisaConnectionOptions | None = None,
) -> Connection | None:
    """Build an update value, requiring a kind when any options were supplied."""
    if kind is None:
        if any(_has_options(options) for options in (socket, com, usb, visa)):
            raise typer.BadParameter(
                "--connection is required when connection options are supplied"
            )
        return None
    return build_connection(kind, socket=socket, com=com, usb=usb, visa=visa)
