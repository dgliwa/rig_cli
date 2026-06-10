from __future__ import annotations

from unittest.mock import MagicMock, call, patch

from rig.engine.appliers.base import ApplyContext
from rig.engine.state import RigState
from rig.models.rig import Rig
from rig_chasebliss.applier import ChaseBlissApplier, _find_device
from rig_chasebliss.catalog import Control, ControlType
from rig_chasebliss.device import ChaseBlissConfig
from rig_chasebliss.models import CbaSetupAction

_TEST_MODEL = "Test Model"


class _FakeDevice:
    """Minimal device object for test rig construction."""

    def __init__(self, device_id: str, config: ChaseBlissConfig):
        self.id = device_id
        self.name = device_id
        self.type = "digital"
        self.config = config
        self.presets = []


def _make_rig() -> Rig:
    config = ChaseBlissConfig(model=_TEST_MODEL)
    device = _FakeDevice("test_cba", config)
    return Rig(
        name="test",
        devices={"test_cba": device},
        scenes={},
        midi_channel=1,
    )


def _patch_get_controls(controls: list[Control]):
    """Patch get_controls so the applier resolves to specified controls."""
    return patch("rig_chasebliss.applier.get_controls", return_value=controls)


def _make_ctx(rig: Rig, dry_run: bool = False) -> ApplyContext:
    midi = MagicMock() if not dry_run else None
    return ApplyContext(
        state=RigState(),
        rig=rig,
        dry_run=dry_run,
        confirmation_io=MagicMock() if dry_run else None,
        midi=midi,
        connected_devices={"test_cba"} if not dry_run else set(),
        config_path=None,
    )


def _make_action(cc_params: list[dict[str, int]] | None = None) -> CbaSetupAction:
    return CbaSetupAction(
        device="test_cba",
        midi_channel=1,
        type="build_preset",
        preset_id="test_preset",
        preset_name="Test Preset",
        preset_number=1,
        cc_params=cc_params or [{"cc": 14, "value": 100}],
    )


def _make_applier() -> ChaseBlissApplier:
    return ChaseBlissApplier()


# --- _find_device tests ---


def test_find_device_returns_none_for_unknown_id():
    rig = _make_rig()
    assert _find_device(rig, "nonexistent") is None


def test_find_device_returns_none_for_none_rig():
    assert _find_device(None, "anything") is None


def test_find_device_finds_existing_device():
    rig = _make_rig()
    assert _find_device(rig, "test_cba") is not None
    assert _find_device(rig, "test_cba").id == "test_cba"


# --- reset-to-defaults behavior tests ---


def _patch_prompt(return_value: str = "confirm"):
    """Context manager that mocks prompt_cba_build_preset to return a fixed value."""
    return patch("rig_chasebliss.applier.prompt_cba_build_preset", return_value=return_value)


def test_reset_sent_before_cc_params():
    """Reset CCs are sent before preset CC params, in correct order."""
    controls = [
        Control(name="vol", type=ControlType.KNOB, midi_cc=14, min=0, max=127, default=64),
    ]
    rig = _make_rig()
    ctx = _make_ctx(rig)
    action = _make_action([{"cc": 14, "value": 100}])

    applier = _make_applier()
    with _patch_get_controls(controls), _patch_prompt():
        result = applier._build_preset(action, ctx)

    assert result.status == "confirmed"
    # Expect reset CC (cc=14, value=64) then preset CC (cc=14, value=100)
    calls = ctx.midi.send_control_change.call_args_list
    assert len(calls) >= 2
    assert calls[0] == call("test_cba", 14, 64, 1)
    assert calls[1] == call("test_cba", 14, 100, 1)


def test_reset_excludes_default_none_controls():
    """Controls with default=None are excluded from the reset batch."""
    controls = [
        Control(name="vol", type=ControlType.KNOB, midi_cc=14, min=0, max=127, default=64),
        Control(name="sw", type=ControlType.SWITCH, midi_cc=55, default=None),
    ]
    rig = _make_rig()
    ctx = _make_ctx(rig)
    action = _make_action([{"cc": 14, "value": 100}])

    applier = _make_applier()
    with _patch_get_controls(controls), _patch_prompt():
        result = applier._build_preset(action, ctx)

    assert result.status == "confirmed"
    # Only 1 reset CC (the KNOB), plus the preset CC
    assert ctx.midi.send_control_change.call_count == 2
    ctx.midi.send_control_change.assert_any_call("test_cba", 14, 64, 1)
    ctx.midi.send_control_change.assert_any_call("test_cba", 14, 100, 1)


def test_dry_run_shows_reset_count():
    """Dry-run mode returns skipped without crashing."""
    controls = [
        Control(name="vol", type=ControlType.KNOB, midi_cc=14, min=0, max=127, default=64),
        Control(name="mix", type=ControlType.KNOB, midi_cc=15, min=0, max=127, default=100),
        Control(name="sw", type=ControlType.SWITCH, midi_cc=55, default=None),
    ]
    rig = _make_rig()
    ctx = _make_ctx(rig, dry_run=True)
    action = _make_action()

    applier = _make_applier()
    with _patch_get_controls(controls):
        result = applier._build_preset(action, ctx)

    assert result.status == "skipped"


def test_no_resettable_controls_no_reset():
    """When all controls have default=None, no extra CCs are sent."""
    controls = [
        Control(name="sw1", type=ControlType.SWITCH, midi_cc=55, default=None),
        Control(name="sw2", type=ControlType.SWITCH, midi_cc=56, default=None),
    ]
    rig = _make_rig()
    ctx = _make_ctx(rig)
    action = _make_action([{"cc": 14, "value": 100}])

    applier = _make_applier()
    with _patch_get_controls(controls), _patch_prompt():
        result = applier._build_preset(action, ctx)

    assert result.status == "confirmed"
    # Only the preset CC should have been sent
    assert ctx.midi.send_control_change.call_count == 1
    ctx.midi.send_control_change.assert_called_with("test_cba", 14, 100, 1)


def test_reset_failure_non_blocking():
    """Individual reset CC failures are caught and don't block preset CCs."""
    controls = [
        Control(name="vol", type=ControlType.KNOB, midi_cc=14, min=0, max=127, default=64),
    ]
    rig = _make_rig()
    ctx = _make_ctx(rig)
    action = _make_action([{"cc": 14, "value": 100}])

    # Make the first send fail
    ctx.midi.send_control_change.side_effect = [Exception("MIDI error"), None]

    applier = _make_applier()
    with _patch_get_controls(controls), _patch_prompt():
        result = applier._build_preset(action, ctx)

    assert result.status == "confirmed"
    # Both calls attempted (reset failed, preset succeeded)
    assert ctx.midi.send_control_change.call_count == 2


def test_reset_per_preset_frequency():
    """Reset fires on every _build_preset invocation (unconditional per-preset, D-02)."""
    controls = [
        Control(name="vol", type=ControlType.KNOB, midi_cc=14, min=0, max=127, default=64),
    ]
    rig = _make_rig()
    ctx = _make_ctx(rig)

    action1 = _make_action([{"cc": 14, "value": 100}])
    action2 = CbaSetupAction(
        device="test_cba",
        midi_channel=1,
        type="build_preset",
        preset_id="other_preset",
        preset_name="Other Preset",
        preset_number=2,
        cc_params=[{"cc": 14, "value": 50}],
    )

    applier = _make_applier()

    # First preset
    ctx.midi.reset_mock()
    with _patch_get_controls(controls), _patch_prompt():
        r1 = applier._build_preset(action1, ctx)
    assert r1.status == "confirmed"
    calls_before = ctx.midi.send_control_change.call_count
    # Reset + preset CCs
    assert calls_before == 2

    # Second preset — reset should fire again
    ctx.midi.reset_mock()
    with _patch_get_controls(controls), _patch_prompt():
        r2 = applier._build_preset(action2, ctx)
    assert r2.status == "confirmed"
    # Reset + preset CCs again
    assert ctx.midi.send_control_change.call_count == 2


def test_reset_with_empty_controls():
    """Empty controls list doesn't cause errors; preset CCs still sent."""
    rig = _make_rig()
    ctx = _make_ctx(rig)
    action = _make_action([{"cc": 14, "value": 100}])

    applier = _make_applier()
    with _patch_get_controls([]), _patch_prompt():
        result = applier._build_preset(action, ctx)

    assert result.status == "confirmed"
    # Only the preset CC
    assert ctx.midi.send_control_change.call_count == 1


def test_reset_with_rig_none():
    """When ctx.rig is None, _build_preset still handles gracefully."""
    action = _make_action([{"cc": 14, "value": 100}])
    midi = MagicMock()
    ctx = ApplyContext(
        state=RigState(),
        rig=None,
        dry_run=False,
        confirmation_io=None,
        midi=midi,
        connected_devices={"test_cba"},
        config_path=None,
    )

    applier = _make_applier()
    with _patch_prompt():
        result = applier._build_preset(action, ctx)
    # Without a rig, _send_reset_ccs returns 0, _send_ccs handles
    # via the connected_devices + action.cc_params check
    assert result is not None


def test_reset_sends_multiple_reset_ccs():
    """Multiple resettable controls each get their reset CC sent."""
    controls = [
        Control(name="vol", type=ControlType.KNOB, midi_cc=14, min=0, max=127, default=64),
        Control(name="mix", type=ControlType.KNOB, midi_cc=15, min=0, max=127, default=100),
        Control(name="time", type=ControlType.KNOB, midi_cc=16, min=0, max=127, default=32),
    ]
    rig = _make_rig()
    ctx = _make_ctx(rig)
    action = _make_action([{"cc": 14, "value": 90}])

    applier = _make_applier()
    with _patch_get_controls(controls), _patch_prompt():
        result = applier._build_preset(action, ctx)

    assert result.status == "confirmed"
    # 3 reset CCs + 1 preset CC
    assert ctx.midi.send_control_change.call_count == 4
    ctx.midi.send_control_change.assert_any_call("test_cba", 14, 64, 1)
    ctx.midi.send_control_change.assert_any_call("test_cba", 15, 100, 1)
    ctx.midi.send_control_change.assert_any_call("test_cba", 16, 32, 1)
    ctx.midi.send_control_change.assert_any_call("test_cba", 14, 90, 1)
