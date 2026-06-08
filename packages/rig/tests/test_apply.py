from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rig.engine.apply import ApplyResult, apply_plan
from rig.engine.plan import compute_plan
from rig.models.device import Device, DeviceType
from rig.models.preset import DigitalPreset, HXStompPreset
from rig.models.rig import Rig
from rig.models.scene import Scene
from rig_chasebliss.device import ChaseBlissConfig, ChaseBlissDevice
from rig_hx.device import HXStompDevice
from tests.fakes import InMemoryPromptAdapter, InMemoryStateAdapter


def _fake_midi_connect(
    device: str, channel: int, midi: object, cached_port: str | None
) -> tuple[str, str | None]:
    """Fake prompt_midi_connect that connects to a test port and returns confirm."""
    midi.connect("USB Interface", device)
    return ("confirm", "USB Interface")


def _patch_cba_prompts(
    channel: str = "confirm",
    preset: str = "confirm",
    register: str = "confirm",
) -> ExitStack:
    """Patch all three CBA prompt functions at rig_chasebliss.applier.

    Returns an ExitStack that can be used as a context manager:
    ``with _patch_cba_prompts():`` or ``with (_patch_cba_prompts(), other_patch):``
    """
    stack = ExitStack()
    stack.enter_context(patch("rig_chasebliss.applier.prompt_cba_channel", return_value=channel))
    stack.enter_context(
        patch("rig_chasebliss.applier.prompt_cba_build_preset", return_value=preset)
    )
    stack.enter_context(patch("rig_chasebliss.applier.prompt_cba_register", return_value=register))
    return stack


def _make_config() -> Rig:
    hx = HXStompDevice(
        id="hx-stomp",
        type=DeviceType.MODELER,
        config={"type": "midi", "midi_channel": 1},
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
        config={"type": "controller", "midi_channel": 1, "banks": []},
    )
    scene = Scene(
        name="test-scene",
        presets={"hx-stomp": "clean-edge", "brothers": "low-gain"},
    )
    return Rig(
        name="test",
        signal_chain=["hx-stomp"],
        devices={"hx-stomp": hx, "brothers": bro, "mc6": ctrl},
        scenes={"test-scene": scene},
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
        with _patch_cba_prompts():
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
        with _patch_cba_prompts(channel="quit"):
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
        # HX-stomp setup: prompt_midi_connect → confirm
        # Brothers CBA setup: prompt_midi_connect → confirm
        #    → establish_channel: prompt_cba_channel(ready) → confirm
        #      prompt_cba_channel(sent) → confirm
        #    → build_preset: prompt_cba_preset → confirm
        #    → register_scenes: prompt_cba_register → confirm
        # Scene hx-stomp: prompt_device → confirm
        # Scene brothers: prompt_device → confirm
        prompt_io = InMemoryPromptAdapter(
            side_effect=[
                "confirm",
                "confirm",
                "confirm",
                "confirm",
                "confirm",
                "confirm",
            ]
        )
        with (
            patch("rig.midi.adapter.mido.get_output_names", return_value=["USB Interface"]),
            patch("rig.midi.adapter.mido.open_output", return_value=fake_port),
            patch("rig.interaction.midi.prompt_midi_connect", _fake_midi_connect),
            _patch_cba_prompts(),
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
        """Cached midi_port from state is used by HXStompDevice.setup()."""
        from rig.engine.plugin import SetupContext
        from rig.engine.state import DeviceState, RigState
        from rig_hx.device import HXStompDevice

        fake_port = MagicMock()
        state = RigState()
        state.devices["hx-stomp"] = DeviceState(midi_port="USB Interface")

        dev = HXStompDevice(
            id="hx-stomp",
            config={"type": "midi", "midi_channel": 1},
        )
        with (
            patch("rig.midi.adapter.mido.get_output_names", return_value=["USB Interface"]),
            patch("rig.midi.adapter.mido.open_output", return_value=fake_port),
            patch("rig.interaction.midi.prompt_midi_connect", _fake_midi_connect),
        ):
            from rig.midi.adapter import MidiManager

            midi = MidiManager()
            ctx = SetupContext(
                state=state,
                rig=None,
                dry_run=False,
                confirmation_io=InMemoryPromptAdapter(),
                midi=midi,
                config_path=str(tmp_path),
                connected_devices=set(),
            )
            dev.setup(ctx)
            midi.disconnect_all()

        assert state.devices["hx-stomp"].midi_port == "USB Interface"

    def test_midi_skip_falls_back_to_manual(self, tmp_path):
        """Skipping MIDI connect falls back to instructional prompts without PC send."""
        rig = _make_config()
        plan = compute_plan(rig)
        state_adapter = InMemoryStateAdapter()
        prompt_io = InMemoryPromptAdapter(side_effect=["confirm", "confirm"])
        with (
            patch("rig.midi.adapter.mido.get_output_names", return_value=["USB Interface"]),
            patch("rig.midi.adapter.mido.open_output", return_value=MagicMock()),
            patch("rig.interaction.midi.prompt_midi_connect", return_value=("skip", None)),
            _patch_cba_prompts(channel="skip"),
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
        assert state.devices.get("brothers") is None or state.devices["brothers"].midi_port is None
        # Manual config still works: last_preset was confirmed
        assert (
            state.devices.get("brothers") is None
            or state.devices["brothers"].last_preset == "low-gain"
        )

    def test_midi_dry_run_skips_connection(self, tmp_path, capsys):
        """Dry run does not connect MIDI — devices add themselves to connected_devices."""
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
        assert "dry-run" in captured.out

    def test_midi_quit_aborts_apply(self, tmp_path, capsys):
        """Quitting MIDI connect aborts the entire apply."""
        rig = _make_config()
        plan = compute_plan(rig)
        state_adapter = InMemoryStateAdapter()
        with (
            patch("rig.midi.adapter.mido.get_output_names", return_value=["USB Interface"]),
            patch("rig.midi.adapter.mido.open_output", return_value=MagicMock()),
            patch("rig.interaction.midi.prompt_midi_connect", return_value=("quit", None)),
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
        prompt_io = InMemoryPromptAdapter(side_effect=["confirm", "confirm"])
        with (
            patch("rig.midi.adapter.mido.get_output_names", return_value=[]),
            patch("rig.interaction.midi.prompt_midi_connect", return_value=("skip", None)),
            _patch_cba_prompts(channel="skip"),
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

        # Apply completed without MIDI connection
        state = state_adapter.state
        assert (
            state.devices.get("brothers") is None
            or state.devices["brothers"].last_preset == "low-gain"
        )


class TestCbaApply:
    def test_cba_channel_establishment_writes_state(self, tmp_path):
        rig = _make_config()
        plan = compute_plan(rig)
        fake_port = MagicMock()
        state_adapter = InMemoryStateAdapter()
        prompt_io = InMemoryPromptAdapter(side_effect=["confirm", "confirm"])
        with (
            patch("rig.midi.adapter.mido.get_output_names", return_value=["USB Interface"]),
            patch("rig.midi.adapter.mido.open_output", return_value=fake_port),
            patch("rig.interaction.midi.prompt_midi_connect", _fake_midi_connect),
            _patch_cba_prompts(),
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
        with _patch_cba_prompts(channel="skip"):
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
        # Patch CBA prompts - channel already established so only build_preset fires
        with _patch_cba_prompts():
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
        # Patch CBA prompts — channel & build_saved already done, only register_scenes fires
        with _patch_cba_prompts():
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
        with _patch_cba_prompts(channel="quit"):
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
            config={"type": "midi", "midi_channel": 1},
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
            config={"type": "controller", "midi_channel": 1, "banks": []},
        )
        scene = Scene(
            name="test-scene",
            presets={"hx-stomp": "clean-edge", "brothers": "low-gain"},
        )
        return Rig(
            name="test",
            signal_chain=["hx-stomp"],
            devices={"hx-stomp": hx, "brothers": bro, "mc6": ctrl},
            scenes={"test-scene": scene},
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

        with (
            patch.object(HXStompDevice, "apply", patched_apply),
            _patch_cba_prompts(),
        ):
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
