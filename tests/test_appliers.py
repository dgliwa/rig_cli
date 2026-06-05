"""Unit tests for device appliers."""

from __future__ import annotations

from unittest.mock import MagicMock

from rig.engine.appliers.analog import AnalogApplier
from rig.engine.appliers.base import ApplyContext
from rig.engine.appliers.chase_bliss import ChaseBlissApplier
from rig.engine.appliers.midi_device import MidiApplier
from rig.engine.plan import CbaSetupAction, DeviceAction
from rig.engine.state import RigState
from tests.fakes import InMemoryPromptAdapter


def _make_ctx(
    dry_run: bool = False,
    connected: set[str] | None = None,
    confirmation_io: InMemoryPromptAdapter | None = None,
) -> ApplyContext:
    midi = MagicMock()
    return ApplyContext(
        dry_run=dry_run,
        confirmation_io=confirmation_io or InMemoryPromptAdapter(default="skip"),
        midi=midi,
        connected_devices=connected or set(),
        state=RigState(),
    )


def _analog_action(device: str = "fuzz", preset_name: str = "Noon") -> DeviceAction:
    return DeviceAction(
        device=device, device_type="analog", status="analog", preset_name=preset_name
    )


def _midi_action(
    device: str = "hx-stomp",
    preset_name: str = "Clean",
    preset_number: int = 5,
    midi_channel: int = 1,
) -> DeviceAction:
    return DeviceAction(
        device=device,
        device_type="digital",
        status="configure",
        preset_name=preset_name,
        preset_number=preset_number,
        midi_channel=midi_channel,
    )


class TestAnalogApplier:
    applier = AnalogApplier()

    def test_dry_run_skips_prompt_and_returns_skipped(self):
        ctx = _make_ctx(dry_run=True)
        action = _analog_action()

        result = self.applier.apply_scene(action, ctx)

        assert result.status == "skipped"
        assert result.device == "fuzz"
        assert result.preset == "Noon"

    def test_prompt_c_returns_confirmed_with_correct_device_and_preset(self):
        ctx = _make_ctx(confirmation_io=InMemoryPromptAdapter(default="confirm"))
        action = _analog_action()

        result = self.applier.apply_scene(action, ctx)

        assert result.status == "confirmed"
        assert result.device == "fuzz"
        assert result.preset == "Noon"

    def test_prompt_c_updates_state(self):
        ctx = _make_ctx(confirmation_io=InMemoryPromptAdapter(default="confirm"))
        action = _analog_action(device="fuzz", preset_name="Noon")

        self.applier.apply_scene(action, ctx)

        assert ctx.state.devices["fuzz"].last_preset == "Noon"

    def test_prompt_s_returns_skipped(self):
        ctx = _make_ctx(confirmation_io=InMemoryPromptAdapter(default="skip"))
        action = _analog_action()

        result = self.applier.apply_scene(action, ctx)

        assert result.status == "skipped"

    def test_prompt_q_returns_error_quit(self):
        ctx = _make_ctx(confirmation_io=InMemoryPromptAdapter(default="quit"))
        action = _analog_action()

        result = self.applier.apply_scene(action, ctx)

        assert result.status == "error"
        assert result.error == "quit"


class TestMidiApplier:
    applier = MidiApplier()

    def test_dry_run_no_midi_send_returns_skipped(self):
        ctx = _make_ctx(dry_run=True, connected={"hx-stomp"})
        action = _midi_action()

        result = self.applier.apply_scene(action, ctx)

        ctx.midi.send_program_change.assert_not_called()
        assert result.status == "skipped"
        assert result.device == "hx-stomp"

    def test_midi_connected_confirm_sends_pc_and_returns_confirmed(self):
        ctx = _make_ctx(
            connected={"hx-stomp"}, confirmation_io=InMemoryPromptAdapter(default="confirm")
        )
        action = _midi_action()

        result = self.applier.apply_scene(action, ctx)

        ctx.midi.send_program_change.assert_called_once_with("hx-stomp", 5, 1)
        assert result.status == "confirmed"

    def test_midi_not_connected_confirm_no_send_returns_confirmed(self):
        ctx = _make_ctx(connected=set(), confirmation_io=InMemoryPromptAdapter(default="confirm"))
        action = _midi_action()

        result = self.applier.apply_scene(action, ctx)

        ctx.midi.send_program_change.assert_not_called()
        assert result.status == "confirmed"

    def test_prompt_s_returns_skipped(self):
        ctx = _make_ctx(confirmation_io=InMemoryPromptAdapter(default="skip"))
        action = _midi_action()

        result = self.applier.apply_scene(action, ctx)

        assert result.status == "skipped"

    def test_prompt_q_returns_error_quit(self):
        ctx = _make_ctx(confirmation_io=InMemoryPromptAdapter(default="quit"))
        action = _midi_action()

        result = self.applier.apply_scene(action, ctx)

        assert result.status == "error"
        assert result.error == "quit"

    def test_prompt_r_then_c_retries_sends_pc_twice(self):
        ctx = _make_ctx(
            connected={"hx-stomp"},
            confirmation_io=InMemoryPromptAdapter(side_effect=["retry", "confirm"]),
        )
        action = _midi_action()

        result = self.applier.apply_scene(action, ctx)

        assert ctx.midi.send_program_change.call_count == 2
        assert result.status == "confirmed"

    def test_confirm_updates_state(self):
        ctx = _make_ctx(
            connected={"hx-stomp"}, confirmation_io=InMemoryPromptAdapter(default="confirm")
        )
        action = _midi_action(device="hx-stomp", preset_name="Clean")

        self.applier.apply_scene(action, ctx)

        assert ctx.state.devices["hx-stomp"].last_preset == "Clean"


class TestChaseBlissApplierApplyScene:
    applier = ChaseBlissApplier()

    def test_dry_run_delegates_to_midi_applier_no_send(self):
        ctx = _make_ctx(dry_run=True, connected={"cba-mood"})
        action = _midi_action(
            device="cba-mood", preset_name="Shimmer", preset_number=2, midi_channel=3
        )

        result = self.applier.apply_scene(action, ctx)

        ctx.midi.send_program_change.assert_not_called()
        assert result.status == "skipped"

    def test_connected_confirm_sends_pc_and_returns_confirmed(self):
        ctx = _make_ctx(
            connected={"cba-mood"}, confirmation_io=InMemoryPromptAdapter(default="confirm")
        )
        action = _midi_action(
            device="cba-mood", preset_name="Shimmer", preset_number=2, midi_channel=3
        )

        result = self.applier.apply_scene(action, ctx)

        ctx.midi.send_program_change.assert_called_once_with("cba-mood", 2, 3)
        assert result.status == "confirmed"

    def test_prompt_s_returns_skipped(self):
        ctx = _make_ctx(confirmation_io=InMemoryPromptAdapter(default="skip"))
        action = _midi_action(
            device="cba-mood", preset_name="Shimmer", preset_number=2, midi_channel=3
        )

        result = self.applier.apply_scene(action, ctx)

        assert result.status == "skipped"

    def test_prompt_q_returns_error_quit(self):
        ctx = _make_ctx(confirmation_io=InMemoryPromptAdapter(default="quit"))
        action = _midi_action(
            device="cba-mood", preset_name="Shimmer", preset_number=2, midi_channel=3
        )

        result = self.applier.apply_scene(action, ctx)

        assert result.status == "error"
        assert result.error == "quit"


class TestChaseBlissApplierSetup:
    applier = ChaseBlissApplier()

    def _ec_action(self, device: str = "cba-mood", midi_channel: int = 3) -> CbaSetupAction:
        return CbaSetupAction(device=device, midi_channel=midi_channel, type="establish_channel")

    def _bp_action(
        self,
        device: str = "cba-mood",
        midi_channel: int = 3,
        preset_id: str = "shimmer",
        preset_name: str = "Shimmer",
        preset_number: int = 2,
        cc_params: list[dict] | None = None,
    ) -> CbaSetupAction:
        return CbaSetupAction(
            device=device,
            midi_channel=midi_channel,
            type="build_preset",
            preset_id=preset_id,
            preset_name=preset_name,
            preset_number=preset_number,
            cc_params=cc_params or [],
        )

    def _rs_action(
        self,
        device: str = "cba-mood",
        midi_channel: int = 3,
        scene_refs: list[str] | None = None,
    ) -> CbaSetupAction:
        return CbaSetupAction(
            device=device,
            midi_channel=midi_channel,
            type="register_scenes",
            scene_refs=scene_refs or ["scene-a"],
        )

    # --- establish_channel ---

    def test_establish_channel_dry_run_no_prompts_returns_skipped(self):
        ctx = _make_ctx(dry_run=True)
        actions = [self._ec_action()]

        results = self.applier.apply_setup(actions, ctx)

        assert results is not None
        assert len(results) == 1
        assert results[0].status == "skipped"

    def test_establish_channel_confirm_sets_channel_established(self):
        ctx = _make_ctx(
            connected={"cba-mood"},
            confirmation_io=InMemoryPromptAdapter(side_effect=["confirm", "confirm"]),
        )
        actions = [self._ec_action(device="cba-mood", midi_channel=3)]

        results = self.applier.apply_setup(actions, ctx)

        assert results is not None
        assert results[0].status == "confirmed"
        assert ctx.state.devices["cba-mood"].channel_established is True
        assert ctx.state.devices["cba-mood"].midi_channel == 3

    # --- build_preset ---

    def test_build_preset_confirm_sends_ccs_and_updates_state(self):
        ctx = _make_ctx(
            connected={"cba-mood"}, confirmation_io=InMemoryPromptAdapter(default="confirm")
        )
        cc_params = [{"cc": 10, "value": 64}, {"cc": 20, "value": 100}]
        actions = [self._bp_action(cc_params=cc_params)]

        results = self.applier.apply_setup(actions, ctx)

        assert results is not None
        assert results[0].status == "confirmed"
        # CCs sent
        assert ctx.midi.send_control_change.call_count == 2
        # PC sent to save preset
        ctx.midi.send_program_change.assert_called_once_with("cba-mood", 2, 3)
        # State updated
        assert ctx.state.devices["cba-mood"].presets_saved.get("shimmer") is True

    def test_build_preset_dry_run_no_sends(self):
        ctx = _make_ctx(dry_run=True, connected={"cba-mood"})
        cc_params = [{"cc": 10, "value": 64}]
        actions = [self._bp_action(cc_params=cc_params)]

        results = self.applier.apply_setup(actions, ctx)

        assert results is not None
        assert results[0].status == "skipped"
        ctx.midi.send_control_change.assert_not_called()
        ctx.midi.send_program_change.assert_not_called()

    def test_build_preset_quit_returns_none(self):
        ctx = _make_ctx(
            connected={"cba-mood"}, confirmation_io=InMemoryPromptAdapter(default="quit")
        )
        actions = [self._bp_action()]

        result = self.applier.apply_setup(actions, ctx)

        assert result is None

    # --- register_scenes ---

    def test_register_scenes_confirm_sets_registration_done(self):
        ctx = _make_ctx(confirmation_io=InMemoryPromptAdapter(default="confirm"))
        actions = [self._rs_action(device="cba-mood", scene_refs=["scene-a", "scene-b"])]

        results = self.applier.apply_setup(actions, ctx)

        assert results is not None
        assert results[0].status == "confirmed"
        assert ctx.state.devices["cba-mood"].registration_done is True

    def test_register_scenes_dry_run_returns_skipped(self):
        ctx = _make_ctx(dry_run=True)
        actions = [self._rs_action()]

        results = self.applier.apply_setup(actions, ctx)

        assert results is not None
        assert results[0].status == "skipped"

    def test_register_scenes_quit_returns_none(self):
        ctx = _make_ctx(confirmation_io=InMemoryPromptAdapter(default="quit"))
        actions = [self._rs_action()]

        result = self.applier.apply_setup(actions, ctx)

        assert result is None

    def test_establish_channel_quit_returns_none(self):
        ctx = _make_ctx(
            connected={"cba-mood"}, confirmation_io=InMemoryPromptAdapter(default="quit")
        )
        actions = [self._ec_action()]

        result = self.applier.apply_setup(actions, ctx)

        assert result is None
