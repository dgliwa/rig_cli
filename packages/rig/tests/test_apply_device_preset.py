"""Unit tests for apply_device_preset() — isolated single-device apply."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rig.engine.apply import apply_device_preset
from rig.engine.plugin import (
    DeviceApplyContext,
    DeviceApplyResult,
    DeviceType,
    SetupContext,
    SetupResult,
)
from rig.engine.state import RigState
from rig.models.rig import Rig
from tests.conftest import FakeDevice
from tests.fakes import InMemoryPromptAdapter, InMemoryStateAdapter

# ── Helpers ────────────────────────────────────────────────────────────────


@dataclass
class FakePreset:
    """Minimal preset satisfying the Preset Protocol."""

    id: str
    name: str = ""
    preset_number: int | None = None


class ConfirmedFakeDevice(FakeDevice):
    """FakeDevice whose apply() always returns 'confirmed'."""

    def apply(self, ctx: DeviceApplyContext) -> DeviceApplyResult:
        return DeviceApplyResult(device=self.id, status="confirmed", preset=ctx.action.preset_name)


class CancelledSetupFakeDevice(FakeDevice):
    """FakeDevice whose setup() returns cancelled=True."""

    def setup(self, ctx: SetupContext) -> SetupResult:
        return SetupResult(cancelled=True)


def _make_rig(
    device_id: str = "klon",
    preset_id: str = "clean",
    preset_number: int | None = 7,
    device_class=None,
) -> Rig:
    """Build a minimal Rig with one device and one preset."""
    if device_class is None:
        device_class = ConfirmedFakeDevice
    preset = FakePreset(id=preset_id, name="Clean Tone", preset_number=preset_number)
    device = device_class(
        id=device_id,
        type=DeviceType.DIGITAL,
        presets=[preset],
    )
    return Rig(
        name="test",
        signal_chain=[device_id],
        devices={device_id: device},
    )


def _make_two_device_rig() -> tuple[Rig, ConfirmedFakeDevice, FakeDevice]:
    """Build a Rig with two devices; first is confirmed, second is plain skipped."""
    p1 = FakePreset(id="clean", name="Clean", preset_number=1)
    p2 = FakePreset(id="drive", name="Drive", preset_number=2)
    dev1 = ConfirmedFakeDevice(id="klon", type=DeviceType.DIGITAL, presets=[p1])
    dev2 = FakeDevice(id="tumnus", type=DeviceType.ANALOG, presets=[p2])
    rig = Rig(
        name="test",
        signal_chain=["klon", "tumnus"],
        devices={"klon": dev1, "tumnus": dev2},
    )
    return rig, dev1, dev2


# ── Tests ──────────────────────────────────────────────────────────────────


class TestApplyDevicePresetIsolation:
    def test_applies_only_targeted_device(self):
        """Only the targeted device is changed; other device state is untouched."""
        rig, dev1, dev2 = _make_two_device_rig()
        state_adapter = InMemoryStateAdapter()
        prompt_io = InMemoryPromptAdapter(default="confirm")

        apply_device_preset(
            "klon",
            "clean",
            state_writer=state_adapter,
            rig=rig,
            config_path="/fake/path",
            dry_run=False,
            confirmation_io=prompt_io,
        )

        state = state_adapter.state
        assert "klon" in state.devices, "targeted device should be in state"
        assert "tumnus" not in state.devices, "non-targeted device state must not be touched"

    def test_state_updated_for_targeted_device(self):
        """state.devices[device_id].last_preset equals applied preset_id after confirmed apply."""
        rig = _make_rig()
        state_adapter = InMemoryStateAdapter()
        prompt_io = InMemoryPromptAdapter(default="confirm")

        apply_device_preset(
            "klon",
            "clean",
            state_writer=state_adapter,
            rig=rig,
            config_path="/fake/path",
            dry_run=False,
            confirmation_io=prompt_io,
        )

        state = state_adapter.state
        assert state.devices["klon"].last_preset == "clean"

    def test_state_scenes_not_touched(self):
        """state.scenes is not modified by apply_device_preset()."""
        rig = _make_rig()
        state_adapter = InMemoryStateAdapter()
        # Pre-populate scenes
        state_adapter._state = RigState(
            scenes={"test-scene": {}},
            devices={},
        )
        prompt_io = InMemoryPromptAdapter(default="confirm")

        apply_device_preset(
            "klon",
            "clean",
            state_writer=state_adapter,
            rig=rig,
            config_path="/fake/path",
            dry_run=False,
            confirmation_io=prompt_io,
        )

        assert state_adapter.state.scenes == {"test-scene": {}}, "scenes must be unchanged"


class TestApplyDevicePresetDryRun:
    def test_dry_run_does_not_write_state(self):
        """dry_run=True: state writer write() is never called."""
        rig = _make_rig()
        state_adapter = InMemoryStateAdapter()
        prompt_io = InMemoryPromptAdapter(default="confirm")
        initial_state = state_adapter.state

        apply_device_preset(
            "klon",
            "clean",
            state_writer=state_adapter,
            rig=rig,
            config_path="/fake/path",
            dry_run=True,
            confirmation_io=prompt_io,
        )

        # State object should not have changed (write never called)
        assert state_adapter.state is initial_state, "state should not be written in dry_run mode"
        assert "klon" not in state_adapter.state.devices


class TestApplyDevicePresetSkipped:
    def test_skipped_result_does_not_write_state(self):
        """When device.apply returns 'skipped', state is not written."""
        # FakeDevice (base class) returns "skipped"
        p = FakePreset(id="clean", name="Clean")
        device = FakeDevice(id="klon", type=DeviceType.DIGITAL, presets=[p])
        rig = Rig(
            name="test",
            signal_chain=["klon"],
            devices={"klon": device},
        )
        state_adapter = InMemoryStateAdapter()
        prompt_io = InMemoryPromptAdapter(default="confirm")

        apply_device_preset(
            "klon",
            "clean",
            state_writer=state_adapter,
            rig=rig,
            config_path="/fake/path",
            dry_run=False,
            confirmation_io=prompt_io,
        )

        assert "klon" not in state_adapter.state.devices, "skipped result must not write state"


class TestApplyDevicePresetSetupCancelled:
    def test_setup_cancelled_returns_skipped_and_does_not_call_apply(self):
        """When setup() returns cancelled=True, apply() is never called and result is skipped."""
        p = FakePreset(id="clean", name="Clean")
        device = CancelledSetupFakeDevice(id="klon", type=DeviceType.DIGITAL, presets=[p])
        rig = Rig(
            name="test",
            signal_chain=["klon"],
            devices={"klon": device},
        )
        state_adapter = InMemoryStateAdapter()
        prompt_io = InMemoryPromptAdapter(default="confirm")

        result = apply_device_preset(
            "klon",
            "clean",
            state_writer=state_adapter,
            rig=rig,
            config_path="/fake/path",
            dry_run=False,
            confirmation_io=prompt_io,
        )

        assert result.status == "skipped", "cancelled setup must yield skipped result"
        assert "klon" not in state_adapter.state.devices, (
            "state must not be written on setup cancel"
        )


class TestApplyDevicePresetPresetNumber:
    def test_preset_number_resolved_from_presets(self):
        """DeviceAction passed to apply has the preset_number from the preset definition."""
        received_actions: list[Any] = []

        class CapturingDevice(FakeDevice):
            def apply(self, ctx: DeviceApplyContext) -> DeviceApplyResult:
                received_actions.append(ctx.action)
                return DeviceApplyResult(
                    device=self.id, status="confirmed", preset=ctx.action.preset_name
                )

        p = FakePreset(id="clean", name="Clean Tone", preset_number=7)
        device = CapturingDevice(id="klon", type=DeviceType.DIGITAL, presets=[p])
        rig = Rig(
            name="test",
            signal_chain=["klon"],
            devices={"klon": device},
        )
        state_adapter = InMemoryStateAdapter()
        prompt_io = InMemoryPromptAdapter(default="confirm")

        apply_device_preset(
            "klon",
            "clean",
            state_writer=state_adapter,
            rig=rig,
            config_path="/fake/path",
            dry_run=False,
            confirmation_io=prompt_io,
        )

        assert len(received_actions) == 1
        assert received_actions[0].preset_number == 7
