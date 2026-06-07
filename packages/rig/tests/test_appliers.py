"""Unit tests for retained appliers (ChaseBlissApplier setup flow).

AnalogApplier, MidiApplier, and MC6Applier have been migrated to concrete device
plugin types (AnalogDevice, MidiDevice, MC6Device in engine/devices.py).
Their tests now live in tests/test_devices.py.

This file retains tests for ChaseBlissApplier.apply_setup only — the 3-phase
CBA setup flow is kept in appliers/chase_bliss.py because it handles multi-step
interaction sequences that are separate from scene-level apply.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from rig.engine.appliers.base import ApplyContext
from rig.engine.plan import CbaSetupAction
from rig.engine.state import RigState
from rig_chasebliss.applier import ChaseBlissApplier
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

    def test_detect_cba_setup_fresh_device_produces_all_phases(self):
        from rig.engine.plan.compute import detect_cba_setup
        from rig.models.device import ChaseBlissConfig, ControllerConfig, Device, DeviceType
        from rig.models.preset import DigitalPreset
        from rig.models.rig import Rig
        from rig.models.scene import Scene
        from rig.models.signal_chain import SignalChainPosition

        bro = Device(
            id="cba-mood",
            manufacturer="CBA",
            model="Mood MKII",
            type=DeviceType.DIGITAL,
            config=ChaseBlissConfig(midi_channel=3),
            presets=[
                DigitalPreset(id="shimmer", pedal="cba-mood", name="Shimmer", preset_number=2),
                DigitalPreset(id="drone", pedal="cba-mood", name="Drone", preset_number=3),
            ],
        )
        ctrl = Device(
            id="mc6",
            manufacturer="Morningstar",
            model="MC6",
            type=DeviceType.CONTROLLER,
            config=ControllerConfig(
                midi_channel=1,
                scenes={"scene-a": Scene(name="scene-a", presets={"cba-mood": "shimmer"})},
            ),
        )
        rig = Rig(
            name="test",
            signal_chain=[SignalChainPosition(device_ref="cba-mood", position=1)],
            devices={"cba-mood": bro, "mc6": ctrl},
        )
        state = RigState()  # empty state — channel_established=False for all devices

        actions = detect_cba_setup(rig, state)
        types = [a.type for a in actions]

        assert "establish_channel" in types
        assert "build_preset" in types
        assert "register_scenes" in types
        # establish_channel comes first
        assert types.index("establish_channel") < types.index("build_preset")
        assert types.index("build_preset") < types.index("register_scenes")

    def test_apply_setup_does_not_enqueue_actions_dynamically_on_confirm(self):
        ctx = _make_ctx(
            connected={"cba-mood"},
            confirmation_io=InMemoryPromptAdapter(side_effect=["confirm", "confirm"]),
        )
        actions = [self._ec_action(device="cba-mood", midi_channel=3)]

        results = self.applier.apply_setup(actions, ctx)

        assert results is not None
        assert len(results) == 1  # only the passed-in action; no dynamic additions
        assert results[0].status == "confirmed"
