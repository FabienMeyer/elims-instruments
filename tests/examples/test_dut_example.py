"""Tests for the database-backed DUT example helper."""

from examples.bench_setup.dut import ExampleDut, get_dut


def test_get_dut_by_id() -> None:
    """The characterization examples load their DUT by database ID."""
    dut = get_dut("demo-dut")

    assert isinstance(dut, ExampleDut)
    assert dut.get_id() == "demo-dut"
    assert dut.dut.asset_tag == "DUT-001"
