from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from rig.engine.apply import ApplyResult, apply_plan
from rig.engine.plan import compute_plan
from rig.engine.plugin import DeviceType
from rig.models.rig import Rig
from rig_chasebliss.device import ChaseBlissConfig, ChaseBlissDevice
from rig_chasebliss.preset import DigitalPreset
from rig_hx.device import HXStompDevice
from rig_hx.preset import HXStompPreset
from tests.conftest import FakeDevice
from tests.fakes import InMemoryPromptAdapter, InMemoryStateAdapter


def _fake_midi_connect(
    device: str, channel: int, midi: object, cached_port: str | None
) -> tuple[str, str | None]:
    """Fake prompt_midi_connect that connects to a test port and returns confirm."""
    midi.connect("USB Interface", device)
    return ("confirm", "USB Interface")


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
    ctrl = FakeDevice(
        id="mc6",
        type=DeviceType.CONTROLLER,
        config=SimpleNamespace(
            scenes={"test-scene": {"presets": {"hx-stomp": "clean-edge", "brothers": "low-gain"}}},
            type="controller",
            midi_channel=1,
            banks=[],
        ),
    )
    return Rig(
        name="test",
        signal_chain=["hx-stomp"],
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
                "confirm",
            ]
        )
        with (
            patch("rig.midi.adapter.mido.get_output_names", return_value=["USB Interface"]),
            patch("rig.midi.adapter.mido.open_output", return_value=fake_port),
            patch("rig.interaction.midi.prompt_midi_connect", _fake_midi_connect),
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
        prompt_io = InMemoryPromptAdapter(default="confirm", side_effect=["skip"])
        with (
            patch("rig.midi.adapter.mido.get_output_names", return_value=["USB Interface"]),
            patch("rig.midi.adapter.mido.open_output", return_value=MagicMock()),
            patch("rig.interaction.midi.prompt_midi_connect", return_value=("skip", None)),
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
        prompt_io = InMemoryPromptAdapter(default="confirm", side_effect=["skip"])
        with (
            patch("rig.midi.adapter.mido.get_output_names", return_value=[]),
            patch("rig.interaction.midi.prompt_midi_connect", return_value=("skip", None)),
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
        prompt_io = InMemoryPromptAdapter(side_effect=["confirm"] * 7)
        with (
            patch("rig.midi.adapter.mido.get_output_names", return_value=["USB Interface"]),
            patch("rig.midi.adapter.mido.open_output", return_value=fake_port),
            patch("rig.interaction.midi.prompt_midi_connect", _fake_midi_connect),
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
        ctrl = FakeDevice(
            id="mc6",
            type=DeviceType.CONTROLLER,
            config=SimpleNamespace(
                scenes={
                    "test-scene": {"presets": {"hx-stomp": "clean-edge", "brothers": "low-gain"}}
                },
                type="controller",
                midi_channel=1,
                banks=[],
            ),
        )
        return Rig(
            name="test",
            signal_chain=["hx-stomp"],
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


class TestVerifyActionSkipped:
    """STATE-01: VERIFY actions are not sent to device.apply()."""

    def test_verify_action_does_not_call_device_apply(self, tmp_path):
        """apply_plan must skip device.apply() for VERIFY-status actions."""
        from unittest.mock import patch

        from rig.engine.plan.models import ActionStatus
        from rig_analog.device import AnalogDevice
        from rig_analog.preset import AnalogPreset

        # Build a rig with one analog device
        analog = AnalogDevice(
            id="tumnus",
            type=DeviceType.ANALOG,
            config={"type": "manual"},
            presets=[
                AnalogPreset(
                    id="edge",
                    pedal="tumnus",
                    name="Edge of Breakup",
                    values={"gain": 5.0},
                )
            ],
        )
        ctrl = FakeDevice(
            id="mc6",
            type=DeviceType.CONTROLLER,
            config=SimpleNamespace(
                scenes={"s1": {"presets": {"tumnus": "edge"}}},
                type="controller",
                midi_channel=1,
                banks=[],
            ),
        )
        rig = Rig(
            name="test",
            signal_chain=[],
            devices={"tumnus": analog, "mc6": ctrl},
        )

        # Pre-populate state so tumnus already has the correct preset → VERIFY
        _write_state_file(tmp_path, {"devices": {"tumnus": {"last_preset": "edge"}}, "scenes": {}})

        plan = compute_plan(rig, root_path=str(tmp_path))
        tum_action = [a for a in plan.scenes["s1"].device_actions if a.device == "tumnus"]
        assert len(tum_action) == 1
        assert tum_action[0].status == ActionStatus.VERIFY, (
            "Precondition: analog matching state must produce VERIFY action"
        )

        apply_called = []

        original_apply = AnalogDevice.apply

        def patched_apply(self, ctx):
            apply_called.append(self.id)
            return original_apply(self, ctx)

        state_adapter = InMemoryStateAdapter()
        prompt_io = InMemoryPromptAdapter(default="confirm")

        with patch.object(AnalogDevice, "apply", patched_apply):
            apply_plan(
                plan,
                state_writer=state_adapter,
                confirmation_io=prompt_io,
                rig=rig,
                config_path=str(tmp_path),
                dry_run=False,
            )

        assert "tumnus" not in apply_called, (
            "device.apply() must not be called for VERIFY-status actions (preset already correct)"
        )

    def test_same_scene_applied_twice_no_reprompt_on_second_apply(self, tmp_path):
        """STATE-01 criterion 3: applying the same scene twice must never prompt analog device on second apply."""
        from rig.engine.plan.models import ActionStatus
        from rig_analog.device import AnalogDevice
        from rig_analog.preset import AnalogPreset

        analog = AnalogDevice(
            id="tumnus",
            type=DeviceType.ANALOG,
            config={"type": "manual"},
            presets=[
                AnalogPreset(
                    id="edge",
                    pedal="tumnus",
                    name="Edge of Breakup",
                    values={"gain": 5.0},
                )
            ],
        )
        ctrl = FakeDevice(
            id="mc6",
            type=DeviceType.CONTROLLER,
            config=SimpleNamespace(
                scenes={"s1": {"presets": {"tumnus": "edge"}}},
                type="controller",
                midi_channel=1,
                banks=[],
            ),
        )
        rig = Rig(
            name="test",
            signal_chain=[],
            devices={"tumnus": analog, "mc6": ctrl},
        )

        # --- First apply: state is empty, so tumnus gets an APPLY action and a prompt ---
        apply_called_first = []
        original_apply = AnalogDevice.apply

        def tracking_apply(self, ctx):
            apply_called_first.append(self.id)
            return original_apply(self, ctx)

        state_adapter_first = InMemoryStateAdapter()
        prompt_io_first = InMemoryPromptAdapter(default="confirm")

        plan_first = compute_plan(rig, root_path=str(tmp_path))

        with patch.object(AnalogDevice, "apply", tracking_apply):
            apply_plan(
                plan_first,
                state_writer=state_adapter_first,
                confirmation_io=prompt_io_first,
                rig=rig,
                config_path=str(tmp_path),
                dry_run=False,
            )

        # First apply must have called device.apply() (prompted the user)
        assert "tumnus" in apply_called_first, (
            "Precondition: first apply should call device.apply() when state is empty"
        )

        # Write state to disk so second compute_plan() picks it up
        _write_state_file(tmp_path, {"devices": {"tumnus": {"last_preset": "edge"}}, "scenes": {}})

        # --- Second apply: state now matches, so tumnus must produce VERIFY → no prompt ---
        plan_second = compute_plan(rig, root_path=str(tmp_path))
        tum_action = [a for a in plan_second.scenes["s1"].device_actions if a.device == "tumnus"]
        assert len(tum_action) == 1
        assert tum_action[0].status == ActionStatus.VERIFY, (
            "Precondition: after first apply, second plan must produce VERIFY for analog device"
        )

        apply_called_second = []

        def tracking_apply_second(self, ctx):
            apply_called_second.append(self.id)
            return original_apply(self, ctx)

        state_adapter_second = InMemoryStateAdapter()
        prompt_io_second = InMemoryPromptAdapter(default="confirm")

        with patch.object(AnalogDevice, "apply", tracking_apply_second):
            apply_plan(
                plan_second,
                state_writer=state_adapter_second,
                confirmation_io=prompt_io_second,
                rig=rig,
                config_path=str(tmp_path),
                dry_run=False,
            )

        assert "tumnus" not in apply_called_second, (
            "STATE-01 criterion 3: applying the same scene twice must not re-prompt "
            "analog device whose state already matches"
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


class TestVerifyDisplay:
    """APPLY-01: VERIFY branch prints 'already set' message to console."""

    def test_verify_action_prints_already_set(self, tmp_path, capsys):
        """apply_plan must print 'already set' when a device is already at the desired preset."""
        from rig_analog.device import AnalogDevice
        from rig_analog.preset import AnalogPreset

        analog = AnalogDevice(
            id="tumnus",
            type=DeviceType.ANALOG,
            config={"type": "manual"},
            presets=[
                AnalogPreset(
                    id="edge", pedal="tumnus", name="Edge of Breakup", values={"gain": 5.0}
                )
            ],
        )
        ctrl = FakeDevice(
            id="mc6",
            type=DeviceType.CONTROLLER,
            config=SimpleNamespace(
                scenes={"s1": {"presets": {"tumnus": "edge"}}},
                type="controller",
                midi_channel=1,
                banks=[],
            ),
        )
        rig = Rig(name="test", signal_chain=[], devices={"tumnus": analog, "mc6": ctrl})

        _write_state_file(tmp_path, {"devices": {"tumnus": {"last_preset": "edge"}}, "scenes": {}})
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

        captured = capsys.readouterr()
        assert "already set" in captured.out
        assert "tumnus" in captured.out
        assert "edge" in captured.out

    def test_verify_action_does_not_call_prompt(self, tmp_path):
        """Prompt adapter must not be called when a device is already at the desired preset."""
        from rig_analog.device import AnalogDevice
        from rig_analog.preset import AnalogPreset

        analog = AnalogDevice(
            id="tumnus",
            type=DeviceType.ANALOG,
            config={"type": "manual"},
            presets=[
                AnalogPreset(
                    id="edge", pedal="tumnus", name="Edge of Breakup", values={"gain": 5.0}
                )
            ],
        )
        ctrl = FakeDevice(
            id="mc6",
            type=DeviceType.CONTROLLER,
            config=SimpleNamespace(
                scenes={"s1": {"presets": {"tumnus": "edge"}}},
                type="controller",
                midi_channel=1,
                banks=[],
            ),
        )
        rig = Rig(name="test", signal_chain=[], devices={"tumnus": analog, "mc6": ctrl})

        _write_state_file(tmp_path, {"devices": {"tumnus": {"last_preset": "edge"}}, "scenes": {}})
        plan = compute_plan(rig, root_path=str(tmp_path))

        call_log: list[str] = []

        class TrackingPromptAdapter(InMemoryPromptAdapter):
            def prompt_device(
                self, device, preset_name, preset_number, midi_channel, midi_connected
            ):
                call_log.append(device)
                return super().prompt_device(
                    device, preset_name, preset_number, midi_channel, midi_connected
                )

        state_adapter = InMemoryStateAdapter()
        prompt_io = TrackingPromptAdapter(default="confirm")

        apply_plan(
            plan,
            state_writer=state_adapter,
            confirmation_io=prompt_io,
            rig=rig,
            config_path=str(tmp_path),
            dry_run=False,
        )

        assert "tumnus" not in call_log, (
            "Prompt must not be shown when device is already at correct preset"
        )


class TestDeviceFilterApply:
    """APPLY-02: apply_plan with device_filter applies only the named device across all scenes."""

    def _make_two_device_rig(self) -> tuple[Rig, FakeDevice]:
        from rig_analog.device import AnalogDevice
        from rig_analog.preset import AnalogPreset

        klon = AnalogDevice(
            id="klon",
            type=DeviceType.ANALOG,
            config={"type": "manual"},
            presets=[AnalogPreset(id="clean", pedal="klon", name="Clean", values={})],
        )
        brothers = AnalogDevice(
            id="brothers",
            type=DeviceType.ANALOG,
            config={"type": "manual"},
            presets=[AnalogPreset(id="lo-gain", pedal="brothers", name="Lo Gain", values={})],
        )
        ctrl = FakeDevice(
            id="mc6",
            type=DeviceType.CONTROLLER,
            config=SimpleNamespace(
                scenes={
                    "s1": {"presets": {"klon": "clean", "brothers": "lo-gain"}},
                    "s2": {"presets": {"klon": "clean", "brothers": "lo-gain"}},
                },
                type="controller",
                midi_channel=1,
                banks=[],
            ),
        )
        rig = Rig(
            name="test",
            signal_chain=[],
            devices={"klon": klon, "brothers": brothers, "mc6": ctrl},
        )
        return rig, ctrl

    def test_device_filter_applies_only_named_device(self, tmp_path):
        """apply_plan with device_filter only writes state for the named device."""
        rig, _ = self._make_two_device_rig()
        state_adapter = InMemoryStateAdapter()
        prompt_io = InMemoryPromptAdapter(default="confirm")

        result = compute_plan(rig, root_path=str(tmp_path))
        apply_plan(
            result,
            state_writer=state_adapter,
            confirmation_io=prompt_io,
            rig=rig,
            config_path=str(tmp_path),
            dry_run=False,
            device_filter="klon",
        )

        state = state_adapter.state
        assert "klon" in state.devices
        assert "brothers" not in state.devices, (
            "device_filter must not write state for other devices"
        )

    def test_device_filter_across_multiple_scenes(self, tmp_path):
        """device_filter applies the named device's action across all scenes in the plan."""
        rig, _ = self._make_two_device_rig()
        state_adapter = InMemoryStateAdapter()
        prompt_io = InMemoryPromptAdapter(default="confirm")

        result = compute_plan(rig, root_path=str(tmp_path))
        apply_plan(
            result,
            state_writer=state_adapter,
            confirmation_io=prompt_io,
            rig=rig,
            config_path=str(tmp_path),
            dry_run=False,
            device_filter="klon",
        )

        assert "klon" in state_adapter.state.devices, (
            "klon state must be written after filtered apply"
        )

    def test_device_filter_does_not_run_controller_phase(self, tmp_path):
        """Controller programming phase is skipped when device_filter is set."""
        from unittest.mock import patch

        rig, ctrl = self._make_two_device_rig()
        state_adapter = InMemoryStateAdapter()
        prompt_io = InMemoryPromptAdapter(default="confirm")

        result = compute_plan(rig, root_path=str(tmp_path))
        controller_apply_calls: list[str] = []
        original_apply = type(ctrl).apply

        def tracking_apply(self, ctx):
            controller_apply_calls.append(self.id)
            return original_apply(self, ctx)

        with patch.object(type(ctrl), "apply", tracking_apply):
            apply_plan(
                result,
                state_writer=state_adapter,
                confirmation_io=prompt_io,
                rig=rig,
                config_path=str(tmp_path),
                dry_run=False,
                device_filter="klon",
            )

        assert "mc6" not in controller_apply_calls, (
            "Controller apply must not run when device_filter is set"
        )
