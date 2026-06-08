from __future__ import annotations

import pytest

from rig.config.errors import ConfigError
from rig.models.device import Device, DeviceType
from rig.models.graph import CycleError, DeviceGraph
from rig.models.rig import Rig


def _make_device(id: str, type: DeviceType, config=None) -> Device:
    if config is None:
        if type in (DeviceType.ANALOG,):
            config = {"type": "manual"}
        elif type == DeviceType.CONTROLLER:
            config = {"type": "controller", "banks": []}
        else:
            config = {"type": "midi", "midi_channel": 1}
    return Device(id=id, manufacturer="Acme", model="Pedal", type=type, config=config)


def _make_rig(devices: list[Device], signal_chain_ids: list[str], scenes=None) -> Rig:
    return Rig(
        name="test",
        devices={d.id: d for d in devices},
        signal_chain=list(signal_chain_ids),
    )


class TestApplyOrder:
    def test_linear_signal_chain_order(self) -> None:
        d1 = _make_device("d1", DeviceType.DIGITAL)
        d2 = _make_device("d2", DeviceType.DIGITAL)
        d3 = _make_device("d3", DeviceType.DIGITAL)
        rig = _make_rig([d1, d2, d3], ["d1", "d2", "d3"])
        result = DeviceGraph(rig).apply_order()
        assert result == [d1, d2, d3]

    def test_controller_always_last(self) -> None:
        d1 = _make_device("d1", DeviceType.DIGITAL)
        d2 = _make_device("d2", DeviceType.DIGITAL)
        ctrl = _make_device("ctrl", DeviceType.CONTROLLER)
        rig = _make_rig([ctrl, d1, d2], ["d1", "d2"])
        result = DeviceGraph(rig).apply_order()
        assert result[-1] == ctrl
        assert result[0] == d1
        assert result[1] == d2

    def test_off_chain_device_between_chain_and_controller(self) -> None:
        in_chain = _make_device("in_chain", DeviceType.DIGITAL)
        off_chain = _make_device("off_chain", DeviceType.DIGITAL)
        ctrl = _make_device("ctrl", DeviceType.CONTROLLER)
        rig = _make_rig([in_chain, off_chain, ctrl], ["in_chain"])
        result = DeviceGraph(rig).apply_order()
        assert result == [in_chain, off_chain, ctrl]

    def test_empty_devices_returns_empty_list(self) -> None:
        rig = _make_rig([], [])
        result = DeviceGraph(rig).apply_order()
        assert result == []

    def test_single_device_no_signal_chain(self) -> None:
        device = _make_device("solo", DeviceType.DIGITAL)
        rig = _make_rig([device], [])
        result = DeviceGraph(rig).apply_order()
        assert result == [device]


class TestCycleDetection:
    def test_no_duplicate_passes(self) -> None:
        d1 = _make_device("hx", DeviceType.DIGITAL)
        d2 = _make_device("brothers", DeviceType.DIGITAL)
        rig = _make_rig([d1, d2], ["hx", "brothers"])
        DeviceGraph(rig).apply_order()  # should not raise

    def test_duplicate_device_ref_raises_cycle_error(self) -> None:
        d1 = _make_device("hx", DeviceType.DIGITAL)
        d2 = _make_device("brothers", DeviceType.DIGITAL)
        rig = _make_rig([d1, d2], ["hx", "brothers", "hx"])
        with pytest.raises(CycleError):
            DeviceGraph(rig).apply_order()

    def test_cycle_error_is_config_error(self) -> None:
        assert issubclass(CycleError, ConfigError)
