# Driver support

Inventory support and hardware-driver support are separate. The database can
store any validated instrument category and model, while `Bench` can construct a
runtime object only when both its category and model have registered factories.

## Built-in model recognition

| Category | Recognized model aliases | Runtime class | Hardware I/O |
| --- | --- | --- | --- |
| Multimeter | `Keysight 34401A`, `34401A` | `Keysight34401A` | Not implemented |
| Multimeter | `Keysight 34410A`, `34410A` | `Keysight34410A` | Not implemented |
| Multimeter | `Keysight 34465A`, `34465A` | `Keysight34465A` | Not implemented |
| Counter | `Keysight 53220A`, `53220A` | `Keysight53220A` | Not implemented |
| Power supply | `Keysight E36313A`, `E36313A` | `KeysightE36313A` | Not implemented |
| Thermal test system | None | — | No built-in model driver |
| Oscilloscope | None | — | No category factory |

Alias lookup strips surrounding whitespace and ignores case. The current
Keysight classes identify supported models, but their `connect()`,
`disconnect()`, and `get_id()` methods raise `NotImplementedError`. They must not
be treated as production hardware drivers yet.

!!! warning "No real-hardware guarantee"

    The test suite exercises factories, validation, sequencing, cleanup, and
    simulated characterization. It does not verify communication with physical
    instruments.

## Boards, DUTs, and projects

- Board type `generic` uses the base `Board` implementation. Other board types
  must be registered with `BoardFactory`.
- DUT drivers are registered under `DutModel.project` and must implement
  `get_id()` and `reset()`.
- Project implementations are registered under `ProjectModel.internal_name`
  and must implement `get_id()`.

Factories normalize string keys by stripping whitespace and ignoring case.
Registering the same builder twice is harmless; replacing a different builder
requires `replace=True`.

See [Extending drivers](extending-drivers.md) for complete registration
patterns. The bundled [examples](examples.md) use simulated sources and custom
board, DUT, and project implementations, so they can run without laboratory
hardware.
