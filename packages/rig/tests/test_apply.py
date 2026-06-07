from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rig.engine.apply import ApplyResult, apply_plan
from rig.engine.plan import compute_plan
from rig.models.device import ChaseBlissConfig, ControllerConfig, Device, DeviceType, MidiConfig
from rig.models.preset import DigitalPreset, HXStompPreset
from rig.models.rig import Rig
from rig.models.scene import Scene
from rig.models.signal_chain import SignalChainPosition
from rig_chasebliss.device import ChaseBlissDevice
from rig_hx.device import HXStompDevice
from tests.fakes import InMemoryPromptAdapter, InMemoryStateAdapter


def _make_config() -> Rig:
    hx = HXStompDevice(
        id="hx-stomp",
        type=DeviceType.MODELER,
        config=MidiConfig(midi_channel=1),
        presets=[
            HXStompPreset(
                id="clean-edge",
                name="Clean Edge",
                preset_number=12,
                hlx_file="hlx/clean-edge.hlx",
            )
        ],
    )
    bro = ChaseBlissDevice(
        id="brothers",
        type=DeviceType.DIGITAL,
        config=ChaseBlissConfig(midi_channel=3),
        presets=[DigitalPreset(id="low-gain", pedal="brothers", name="Low Gain", preset_number=4)],
    )
    ctrl = Device(
        id="mc6",
        manufacturer="Morningstar",
        model="MC6",
        type=DeviceType.CONTROLLER,
        config=ControllerConfig(
            midi_channel=1,
            scenes={
                "test-scene": Scene(
                    name="test-scene", presets={"hx-stomp": "clean-edge", "brothers": "low-gain"}
                )
            },
        ),
    )
    return Rig(
        name="test",
        signal_chain=[SignalChainPosition(device_ref="hx-stomp", position=1)],
        devices={"hx-stomp": hx, "brothers": bro, "mc6": ctrl},
    )


def _write_state_file(tmp_path: Path, data: dict):
    import json

    path = tmp_path / ".rig" / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


class TestApplyPlan:
    def test_clean_plan_prints_no_changes(self, tmp_path, capsys):
        config = _make_config()
        _write_state_file(
            tmp_path,
            {
                "devices": {
                    "hx-stomp": {"last_preset": "clean-edge"},
                    "brothers": {
                        "last_preset": "low-gain",
                        "channel_established": True,
                        "midi_channel": 3,
                        "presets_saved": {"low-gain": True},
                        "registration_done": True,
                    },
                },
                "scenes": {"test-scene": {}},
            },
        )
        plan = compute_plan(config, root_path=str(tmp_path))
        assert plan.status == "clean"
        state_adapter = InMemoryStateAdapter()
        apply_plan(plan, state_writer=state_adapter, dry_run=True)
        captured = capsys.readouterr()
        assert "No changes needed" in captured.out

    def test_dry_run_does_not_write_state(self, tmp_path):
        config = _make_config()
        plan = compute_plan(config)
        state_adapter = InMemoryStateAdapter()
        apply_plan(
            plan,
            state_writer=state_adapter,
            config_path=str(tmp_path),
            dry_run=True,
        )
        # InMemoryStateAdapter never writes to disk; state is always empty after dry_run
        assert state_adapter.state.devices == {}

    def test_apply_writes_state(self, tmp_path):
        config = _make_config()
        plan = compute_plan(config)
        state_adapter = InMemoryStateAdapter()
        prompt_io = InMemoryPromptAdapter(default="confirm")
        apply_plan(
            plan,
            state_writer=state_adapter,
            confirmation_io=prompt_io,
            rig=config,
            config_path=str(tmp_path),
            dry_run=False,
        )
        state = state_adapter.state
        assert "hx-stomp" in state.devices
        assert state.devices["hx-stomp"].last_preset == "clean-edge"
        assert "test-scene" in state.scenes

    def test_apply_skip_does_not_write_device_state(self, tmp_path):
        config = _make_config()
        plan = compute_plan(config)
        state_adapter = InMemoryStateAdapter()
        prompt_io = InMemoryPromptAdapter(default="skip")
        apply_plan(
            plan,
            state_writer=state_adapter,
            confirmation_io=prompt_io,
            config_path=str(tmp_path),
            dry_run=False,
        )
        # All actions skipped: no device state written
        state = state_adapter.state
        assert state.devices == {}
        assert state.scenes == {}

    def test_apply_quit_stops_early(self, tmp_path, capsys):
        config = _make_config()
        plan = compute_plan(config)
        state_adapter = InMemoryStateAdapter()
        prompt_io = InMemoryPromptAdapter(default="quit")
        apply_plan(
            plan,
            state_writer=state_adapter,
            confirmation_io=prompt_io,
            rig=config,
            config_path=str(tmp_path),
            dry_run=False,
        )
        captured = capsys.readouterr()
        assert "cancelled" in captured.out.lower()


class TestMidiApply:
    def test_midi_connect_and_send(self, tmp_path):
        """User selects a port, MIDI opens it, PC is sent, user confirms."""
        rig = _make_config()
        plan = compute_plan(rig)
        fake_port = MagicMock()
        state_adapter = InMemoryStateAdapter()
        # CBA: step1+step3, build_preset, register_scenes, hx-stomp scene confirm, brothers scene confirm
        prompt_io = InMemoryPromptAdapter(
            side_effect=["confirm", "confirm", "confirm", "confirm", "confirm", "confirm"]
        )
        with (
            patch("rig.midi.adapter.mido.get_output_names", return_value=["USB Interface"]),
            patch("rig.midi.adapter.mido.open_output", return_value=fake_port),
        ):
            from rig.midi.adapter import MidiManager

            midi = MidiManager()
            apply_plan(
                plan,
                state_writer=state_adapter,
                confirmation_io=prompt_io,
                rig=rig,
                config_path=str(tmp_path),
                dry_run=False,
                midi=midi,
            )
            midi.disconnect_all()

        state = state_adapter.state
        assert state.devices["brothers"].midi_port == "USB Interface"
        assert state.devices["hx-stomp"].midi_port == "USB Interface"
        assert state.devices["brothers"].channel_established is True
        assert fake_port.send.called

    def test_midi_auto_reconnect_from_state(self, tmp_path):
        """Cached midi_port reconnects without prompting."""
        rig = _make_config()
        _write_state_file(
            tmp_path,
            {
                "devices": {
                    "hx-stomp": {"midi_port": "USB Interface", "last_preset": "clean-edge"},
                    "brothers": {"midi_port": "USB Interface", "last_preset": "low-gain"},
                },
                "scenes": {"test-scene": {}},
            },
        )
        plan = compute_plan(rig, root_path=str(tmp_path))
        fake_port = MagicMock()
        state_adapter = InMemoryStateAdapter()
        # CBA step1, step3, build_preset, register_scenes; scene unchanged
        prompt_io = InMemoryPromptAdapter(side_effect=["confirm", "confirm", "confirm", "confirm"])
        with (
            patch("rig.midi.adapter.mido.get_output_names", return_value=["USB Interface"]),
            patch("rig.midi.adapter.mido.open_output", return_value=fake_port),
        ):
            from rig.midi.adapter import MidiManager

            midi = MidiManager()
            apply_plan(
                plan,
                state_writer=state_adapter,
                confirmation_io=prompt_io,
                rig=rig,
                config_path=str(tmp_path),
                dry_run=False,
                midi=midi,
            )
            midi.disconnect_all()

        state = state_adapter.state
        assert state.devices["brothers"].midi_port == "USB Interface"

    def test_midi_skip_falls_back_to_manual(self, tmp_path):
        """Skipping MIDI connect falls back to instructional prompts without PC send."""
        rig = _make_config()
        plan = compute_plan(rig)
        state_adapter = InMemoryStateAdapter()
        # CBA: step1 skipped (skip), then build_preset, register_scenes, scene confirms
        prompt_io = InMemoryPromptAdapter(side_effect=["skip", "confirm", "confirm", "confirm"])
        with (
            patch("rig.midi.adapter.mido.get_output_names", return_value=["USB Interface"]),
            patch("rig.midi.adapter.mido.open_output", return_value=MagicMock()),
        ):
            from rig.midi.adapter import MidiManager

            midi = MidiManager()
            apply_plan(
                plan,
                state_writer=state_adapter,
                confirmation_io=prompt_io,
                rig=rig,
                config_path=str(tmp_path),
                dry_run=False,
                midi=midi,
            )
            midi.disconnect_all()

        state = state_adapter.state
        # No midi_port saved (skipped connection)
        assert not hasattr(state.devices.get("brothers"), "midi_port") or (
            state.devices.get("brothers") is None or state.devices["brothers"].midi_port is None
        )
        # Manual config still works: last_preset was confirmed
        assert state.devices["brothers"].last_preset == "low-gain"

    def test_midi_dry_run_skips_connection(self, tmp_path, capsys):
        """Dry run shows connection instruction but does not prompt."""
        rig = _make_config()
        plan = compute_plan(rig)
        state_adapter = InMemoryStateAdapter()
        with (
            patch("rig.midi.adapter.mido.get_output_names", return_value=["USB Interface"]),
            patch("rig.midi.adapter.mido.open_output", return_value=MagicMock()),
        ):
            from rig.midi.adapter import MidiManager

            midi = MidiManager()
            apply_plan(
                plan,
                state_writer=state_adapter,
                rig=rig,
                dry_run=True,
                midi=midi,
            )
            midi.disconnect_all()

        captured = capsys.readouterr()
        assert "connect MIDI" in captured.out
        assert "dry-run" in captured.out

    def test_midi_quit_aborts_apply(self, tmp_path, capsys):
        """Quitting MIDI connect aborts the entire apply."""
        rig = _make_config()
        plan = compute_plan(rig)
        state_adapter = InMemoryStateAdapter()
        with (
            patch("rig.midi.adapter.mido.get_output_names", return_value=["USB Interface"]),
            patch("rig.midi.adapter.mido.open_output", return_value=MagicMock()),
        ):
            from rig.midi.adapter import MidiManager

            midi = MidiManager()
            apply_plan(
                plan,
                state_writer=state_adapter,
                rig=rig,
                config_path=str(tmp_path),
                dry_run=False,
                midi=midi,
            )
            midi.disconnect_all()

        captured = capsys.readouterr()
        assert "cancelled" in captured.out.lower()
        # No state written (InMemoryStateAdapter starts empty, nothing confirmed before quit)
        assert state_adapter.state.devices == {}

    def test_midi_connect_without_ports_shows_message(self, tmp_path, capsys):
        """When no MIDI ports detected, apply still runs with skip fallback."""
        rig = _make_config()
        plan = compute_plan(rig)
        state_adapter = InMemoryStateAdapter()
        # With no ports available, midi_io skips the connection
        # CBA: step1 skipped, then build_preset, register_scenes, scene confirms
        prompt_io = InMemoryPromptAdapter(side_effect=["skip", "confirm", "confirm", "confirm"])
        with patch("rig.midi.adapter.mido.get_output_names", return_value=[]):
            from rig.midi.adapter import MidiManager

            midi = MidiManager()
            apply_plan(
                plan,
                state_writer=state_adapter,
                confirmation_io=prompt_io,
                rig=rig,
                config_path=str(tmp_path),
                dry_run=False,
                midi=midi,
            )
            midi.disconnect_all()

        # Apply completed without MIDI connection
        state = state_adapter.state
        assert state.devices["brothers"].last_preset == "low-gain"


class TestCbaApply:
    def test_cba_channel_establishment_writes_state(self, tmp_path):
        rig = _make_config()
        plan = compute_plan(rig)
        fake_port = MagicMock()
        state_adapter = InMemoryStateAdapter()
        # CBA: step1 ready, step2 channel-saved, build_preset, register_scenes,
        # scene: hx-stomp confirm, brothers confirm
        prompt_io = InMemoryPromptAdapter(
            side_effect=["confirm", "confirm", "confirm", "confirm", "confirm", "confirm"]
        )
        with (
            patch("rig.midi.adapter.mido.get_output_names", return_value=["USB Interface"]),
            patch("rig.midi.adapter.mido.open_output", return_value=fake_port),
        ):
            from rig.midi.adapter import MidiManager

            midi = MidiManager()
            apply_plan(
                plan,
                state_writer=state_adapter,
                confirmation_io=prompt_io,
                rig=rig,
                config_path=str(tmp_path),
                dry_run=False,
                midi=midi,
            )
            midi.disconnect_all()
        state = state_adapter.state
        dev = state.devices.get("brothers")
        assert dev is not None
        assert dev.channel_established is True
        assert dev.midi_channel == 3

    def test_cba_channel_skipped_writes_no_state(self, tmp_path, capsys):
        rig = _make_config()
        plan = compute_plan(rig)
        state_adapter = InMemoryStateAdapter()
        prompt_io = InMemoryPromptAdapter(default="skip")
        apply_plan(
            plan,
            state_writer=state_adapter,
            confirmation_io=prompt_io,
            rig=rig,
            config_path=str(tmp_path),
            dry_run=False,
        )
        state = state_adapter.state
        # Channel was skipped, no channel_established set
        brothers_dev = state.devices.get("brothers")
        assert brothers_dev is None or not brothers_dev.channel_established

    def test_cba_preset_build_writes_state(self, tmp_path):
        rig = _make_config()
        # Pre-establish channel so plan goes to build_preset
        _write_state_file(
            tmp_path,
            {
                "devices": {
                    "brothers": {
                        "channel_established": True,
                        "midi_channel": 3,
                        "presets_saved": {},
                    }
                },
            },
        )
        plan = compute_plan(rig, root_path=str(tmp_path))
        state_adapter = InMemoryStateAdapter()
        prompt_io = InMemoryPromptAdapter(default="confirm")
        apply_plan(
            plan,
            state_writer=state_adapter,
            confirmation_io=prompt_io,
            rig=rig,
            config_path=str(tmp_path),
            dry_run=False,
        )
        state = state_adapter.state
        assert state.devices["brothers"].presets_saved.get("low-gain") is True

    def test_cba_setup_shown_in_dry_run(self, tmp_path, capsys):
        rig = _make_config()
        plan = compute_plan(rig)
        state_adapter = InMemoryStateAdapter()
        apply_plan(
            plan,
            state_writer=state_adapter,
            rig=rig,
            dry_run=True,
        )
        captured = capsys.readouterr()
        assert "establish MIDI channel" in captured.out
        assert "dry-run" in captured.out

    def test_cba_registration_writes_state(self, tmp_path):
        rig = _make_config()
        _write_state_file(
            tmp_path,
            {
                "devices": {
                    "brothers": {
                        "channel_established": True,
                        "midi_channel": 3,
                        "presets_saved": {"low-gain": True},
                    }
                },
                "scenes": {"test-scene": {}},
            },
        )
        plan = compute_plan(rig, root_path=str(tmp_path))
        state_adapter = InMemoryStateAdapter()
        prompt_io = InMemoryPromptAdapter(default="confirm")
        apply_plan(
            plan,
            state_writer=state_adapter,
            confirmation_io=prompt_io,
            rig=rig,
            config_path=str(tmp_path),
            dry_run=False,
        )
        state = state_adapter.state
        assert state.devices["brothers"].registration_done is True

    def test_cba_quit_during_channel_saves_no_state(self, tmp_path, capsys):
        rig = _make_config()
        plan = compute_plan(rig)
        state_adapter = InMemoryStateAdapter()
        prompt_io = InMemoryPromptAdapter(default="quit")
        apply_plan(
            plan,
            state_writer=state_adapter,
            confirmation_io=prompt_io,
            rig=rig,
            config_path=str(tmp_path),
            dry_run=False,
        )
        captured = capsys.readouterr()
        assert "cancelled" in captured.out.lower()
        # No device state written because quit before any confirmation
        assert state_adapter.state.devices == {}


class TestDevicePluginRouting:
    """Verify apply.py routes through device.apply(ctx) not get_scene_applier."""

    def _make_concrete_config(self) -> Rig:
        """Build a Rig using concrete device plugin types (as produced by loader)."""
        from rig_chasebliss.device import ChaseBlissDevice
        from rig_hx.device import HXStompDevice

        hx = HXStompDevice(
            id="hx-stomp",
            config=MidiConfig(midi_channel=1),
            type=DeviceType.MODELER,
            presets=[
                HXStompPreset(
                    id="clean-edge",
                    name="Clean Edge",
                    preset_number=12,
                    hlx_file="hlx/clean-edge.hlx",
                )
            ],
        )
        bro = ChaseBlissDevice(
            id="brothers",
            config=ChaseBlissConfig(midi_channel=3),
            type=DeviceType.DIGITAL,
            presets=[
                DigitalPreset(id="low-gain", pedal="brothers", name="Low Gain", preset_number=4)
            ],
        )
        ctrl = Device(
            id="mc6",
            manufacturer="Morningstar",
            model="MC6",
            type=DeviceType.CONTROLLER,
            config=ControllerConfig(
                midi_channel=1,
                scenes={
                    "test-scene": Scene(
                        name="test-scene",
                        presets={"hx-stomp": "clean-edge", "brothers": "low-gain"},
                    )
                },
            ),
        )
        return Rig(
            name="test",
            signal_chain=[SignalChainPosition(device_ref="hx-stomp", position=1)],
            devices={"hx-stomp": hx, "brothers": bro, "mc6": ctrl},
        )

    def test_device_apply_called_for_scene_action(self, tmp_path):
        """apply_plan routes through device.apply() for scene actions."""
        from unittest.mock import patch

        from rig_hx.device import HXStompDevice

        rig = self._make_concrete_config()
        plan = compute_plan(rig)
        state_adapter = InMemoryStateAdapter()
        prompt_io = InMemoryPromptAdapter(default="confirm")

        called_with_device_ctx = []

        original_apply = HXStompDevice.apply

        def patched_apply(self, ctx):
            called_with_device_ctx.append(ctx)
            return original_apply(self, ctx)

        with patch.object(HXStompDevice, "apply", patched_apply):
            apply_plan(
                plan,
                state_writer=state_adapter,
                confirmation_io=prompt_io,
                rig=rig,
                config_path=str(tmp_path),
                dry_run=False,
            )

        # HXStompDevice.apply() should have been called for hx-stomp
        assert len(called_with_device_ctx) > 0, "device.apply() was never called"
        # Each call receives a DeviceApplyContext
        from rig.engine.plugin import DeviceApplyContext

        for ctx in called_with_device_ctx:
            assert isinstance(ctx, DeviceApplyContext)

    def test_no_get_scene_applier_import_in_apply(self):
        """apply.py must not import get_scene_applier — routing is through device.apply()."""
        import ast
        import pathlib

        src = pathlib.Path(__file__).parent.parent / "src" / "rig" / "engine" / "apply.py"
        tree = ast.parse(src.read_text())
        forbidden = {"get_scene_applier", "get_mc6_applier"}
        for node in ast.walk(tree):
            if isinstance(node, (ast.ImportFrom, ast.Import)):
                names = {alias.name for alias in getattr(node, "names", [])}
                overlap = names & forbidden
                assert not overlap, (
                    f"apply.py imports {overlap} — should route through device.apply()"
                )


class TestApplyPlanFallback:
    def test_raises_when_no_plan_and_no_rig(self):
        state_adapter = InMemoryStateAdapter()
        with pytest.raises(ValueError):
            apply_plan(
                state_writer=state_adapter,
            )

    def test_fallback_computes_plan_from_rig(self):
        from tests.test_plan import _make_rig

        rig = _make_rig()
        state_adapter = InMemoryStateAdapter()
        result = apply_plan(
            state_writer=state_adapter,
            rig=rig,
            dry_run=True,
        )
        assert isinstance(result, ApplyResult)

    def test_explicit_plan_bypasses_compute(self):
        from rig.engine.plan import Plan

        clean_plan = Plan(status="clean")
        state_adapter = InMemoryStateAdapter()
        result = apply_plan(
            clean_plan,
            state_writer=state_adapter,
            dry_run=True,
        )
        assert result.status == "no_changes"
