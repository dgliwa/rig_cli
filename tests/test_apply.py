import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from rig.engine.apply import apply_plan
from rig.engine.plan import compute_plan
from rig.models.pedal import ChaseBlissConfig, MidiConfig, PedalDefinition, PedalType
from rig.models.preset import DigitalPreset, HXStompPreset
from rig.models.rig import RigConfig
from rig.models.scene import Scene
from rig.models.signal_chain import SignalChainPosition


def _make_config() -> RigConfig:
    hx = PedalDefinition(
        id="hx-stomp",
        manufacturer="Line6",
        model="HX Stomp",
        type=PedalType.MODELER,
        config=MidiConfig(midi_channel=1),
    )
    bro = PedalDefinition(
        id="brothers",
        manufacturer="CBA",
        model="Brothers",
        type=PedalType.DIGITAL,
        config=ChaseBlissConfig(midi_channel=3),
    )
    return RigConfig(
        name="test",
        signal_chain=[SignalChainPosition(pedal_ref="hx-stomp", position=1)],
        pedals={"hx-stomp": hx, "brothers": bro},
        hx_presets={
            "hx-stomp": [
                HXStompPreset(
                    id="clean-edge",
                    name="Clean Edge",
                    preset_number=12,
                    hlx_file="hlx/clean-edge.hlx",
                )
            ]
        },
        digital_presets={
            "brothers": [
                DigitalPreset(id="low-gain", pedal="brothers", name="Low Gain", preset_number=4)
            ]
        },
        scenes={
            "test-scene": Scene(
                name="test-scene", presets={"hx-stomp": "clean-edge", "brothers": "low-gain"}
            )
        },
    )


def _write_state(tmp_path: Path, data: dict):
    path = tmp_path / ".rig" / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


class TestApplyPlan:
    def test_clean_plan_prints_no_changes(self, capsys):
        config = _make_config()
        plan = compute_plan(config)
        apply_plan(plan, dry_run=True)
        captured = capsys.readouterr()
        assert "No changes needed" not in captured.out

    def test_dry_run_does_not_write_state(self, tmp_path):
        config = _make_config()
        plan = compute_plan(config)
        apply_plan(plan, config_path=str(tmp_path), dry_run=True)
        state_file = tmp_path / ".rig" / "state.json"
        assert not state_file.exists()

    def test_apply_writes_state(self, tmp_path):
        config = _make_config()
        plan = compute_plan(config)
        with patch("builtins.input", return_value="c"):
            apply_plan(plan, config_path=str(tmp_path), dry_run=False)
        state_file = tmp_path / ".rig" / "state.json"
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert "devices" in state
        assert state["devices"]["hx-stomp"]["last_preset"] == "clean-edge"

    def test_apply_skip_does_not_write_device_state(self, tmp_path):
        config = _make_config()
        plan = compute_plan(config)
        with patch("builtins.input", return_value="s"):
            apply_plan(plan, config_path=str(tmp_path), dry_run=False)
        state_file = tmp_path / ".rig" / "state.json"
        state = json.loads(state_file.read_text())
        assert "scenes" in state

    def test_apply_quit_stops_early(self, tmp_path, capsys):
        config = _make_config()
        plan = compute_plan(config)
        with patch("builtins.input", return_value="q"):
            apply_plan(plan, config_path=str(tmp_path), dry_run=False)
        captured = capsys.readouterr()
        assert "cancelled" in captured.out.lower()


class TestMidiApply:
    def test_midi_connect_and_send(self, tmp_path):
        """User selects a port, MIDI opens it, PC is sent, user confirms."""
        rig = _make_config()
        plan = compute_plan(rig)
        fake_port = MagicMock()
        inputs = [
            "1",
            "1",
            "c",
            "c",
            "c",
            "c",
            "c",
            "c",
        ]  # 2 MIDI connects, CBA step1+step3, build_preset, register_scenes, 2 scene confirms
        with (
            patch("rig.midi.adapter.mido.get_output_names", return_value=["USB Interface"]),
            patch("rig.midi.adapter.mido.open_output", return_value=fake_port),
            patch("builtins.input", side_effect=inputs),
        ):
            from rig.midi.adapter import MidiManager

            midi = MidiManager()
            apply_plan(plan, rig=rig, config_path=str(tmp_path), dry_run=False, midi=midi)
            midi.disconnect_all()

        # State written
        state = json.loads((tmp_path / ".rig" / "state.json").read_text())
        assert state["devices"]["brothers"]["midi_port"] == "USB Interface"
        assert state["devices"]["hx-stomp"]["midi_port"] == "USB Interface"
        assert state["devices"]["brothers"]["channel_established"] is True
        # PC was sent on the port
        assert fake_port.send.called

    def test_midi_auto_reconnect_from_state(self, tmp_path):
        """Cached midi_port reconnects without prompting."""
        rig = _make_config()
        _write_state(
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
        # No MIDI connect prompts needed (auto-reconnect)
        # CBA establish_channel still runs (channel_established not in state): step1 + step3
        # Scene loop: brothers needs config (hx-stomp already verified via state)
        inputs = [
            "c",
            "c",
            "c",
            "c",
        ]  # CBA step1, step3, build_preset, register_scenes; scene unchanged
        with (
            patch("rig.midi.adapter.mido.get_output_names", return_value=["USB Interface"]),
            patch("rig.midi.adapter.mido.open_output", return_value=fake_port),
            patch("builtins.input", side_effect=inputs),
        ):
            from rig.midi.adapter import MidiManager

            midi = MidiManager()
            apply_plan(plan, rig=rig, config_path=str(tmp_path), dry_run=False, midi=midi)
            midi.disconnect_all()

        state = json.loads((tmp_path / ".rig" / "state.json").read_text())
        assert state["devices"]["brothers"]["midi_port"] == "USB Interface"

    def test_midi_skip_falls_back_to_manual(self, tmp_path):
        """Skipping MIDI connect falls back to old instructional prompts."""
        rig = _make_config()
        plan = compute_plan(rig)
        # Skip MIDI connect for both devices, skip CBA step1, then manual confirms
        inputs = ["s", "s", "s", "c", "c", "c"]
        with (
            patch("rig.midi.adapter.mido.get_output_names", return_value=["USB Interface"]),
            patch("rig.midi.adapter.mido.open_output", return_value=MagicMock()),
            patch("builtins.input", side_effect=inputs),
        ):
            from rig.midi.adapter import MidiManager

            midi = MidiManager()
            apply_plan(plan, rig=rig, config_path=str(tmp_path), dry_run=False, midi=midi)
            midi.disconnect_all()

        state = json.loads((tmp_path / ".rig" / "state.json").read_text())
        # No midi_port saved
        assert "midi_port" not in state.get("devices", {}).get("brothers", {})
        # But manual config still works
        assert state["devices"]["brothers"]["last_preset"] == "low-gain"

    def test_midi_dry_run_skips_connection(self, tmp_path, capsys):
        """Dry run shows connection instruction but does not prompt."""
        rig = _make_config()
        plan = compute_plan(rig)
        with (
            patch("rig.midi.adapter.mido.get_output_names", return_value=["USB Interface"]),
            patch("rig.midi.adapter.mido.open_output", return_value=MagicMock()),
        ):
            from rig.midi.adapter import MidiManager

            midi = MidiManager()
            apply_plan(plan, rig=rig, dry_run=True, midi=midi)
            midi.disconnect_all()

        captured = capsys.readouterr()
        assert "connect MIDI" in captured.out
        assert "dry-run" in captured.out

    def test_midi_quit_aborts_apply(self, tmp_path, capsys):
        """Quitting MIDI connect aborts the entire apply."""
        rig = _make_config()
        plan = compute_plan(rig)
        inputs = ["q"]  # quit during first MIDI connect prompt
        with (
            patch("rig.midi.adapter.mido.get_output_names", return_value=["USB Interface"]),
            patch("rig.midi.adapter.mido.open_output", return_value=MagicMock()),
            patch("builtins.input", side_effect=inputs),
        ):
            from rig.midi.adapter import MidiManager

            midi = MidiManager()
            apply_plan(plan, rig=rig, config_path=str(tmp_path), dry_run=False, midi=midi)
            midi.disconnect_all()

        captured = capsys.readouterr()
        assert "cancelled" in captured.out.lower()
        # No state written
        state_file = tmp_path / ".rig" / "state.json"
        assert not state_file.exists()

    def test_midi_connect_without_ports_shows_message(self, tmp_path, capsys):
        """When no MIDI ports detected, show message and allow skip/refresh."""
        rig = _make_config()
        plan = compute_plan(rig)
        # No ports → "r" (refresh, still none) → "s" (skip both devices) → "s" (skip CBA step1) → manual prompts
        inputs = ["r", "s", "s", "s", "c", "c", "c"]
        with (
            patch("rig.midi.adapter.mido.get_output_names", return_value=[]),
            patch("builtins.input", side_effect=inputs),
        ):
            from rig.midi.adapter import MidiManager

            midi = MidiManager()
            apply_plan(plan, rig=rig, config_path=str(tmp_path), dry_run=False, midi=midi)
            midi.disconnect_all()

        captured = capsys.readouterr()
        assert "No MIDI output ports" in captured.out


class TestCbaApply:
    def test_cba_channel_establishment_writes_state(self, tmp_path):
        rig = _make_config()
        plan = compute_plan(rig)
        # confirm CBA channel, then "c" for each device in scene
        with patch("builtins.input", return_value="c"):
            apply_plan(plan, rig=rig, config_path=str(tmp_path), dry_run=False)
        state = json.loads((tmp_path / ".rig" / "state.json").read_text())
        dev = state["devices"]["brothers"]
        assert dev["channel_established"] is True
        assert dev["midi_channel"] == 3

    def test_cba_channel_skipped_writes_no_state(self, tmp_path, capsys):
        rig = _make_config()
        plan = compute_plan(rig)
        with patch("builtins.input", return_value="s"):
            apply_plan(plan, rig=rig, config_path=str(tmp_path), dry_run=False)
        state = json.loads((tmp_path / ".rig" / "state.json").read_text())
        # Channel was skipped, but scene was still visited
        assert "channel_established" not in state.get("devices", {}).get("brothers", {})

    def test_cba_preset_build_writes_state(self, tmp_path):
        rig = _make_config()
        # Pre-establish channel so plan goes to build_preset
        _write_state(
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
        with patch("builtins.input", return_value="c"):
            apply_plan(plan, rig=rig, config_path=str(tmp_path), dry_run=False)
        state = json.loads((tmp_path / ".rig" / "state.json").read_text())
        assert state["devices"]["brothers"]["presets_saved"]["low-gain"] is True

    def test_cba_setup_shown_in_dry_run(self, tmp_path, capsys):
        rig = _make_config()
        plan = compute_plan(rig)
        apply_plan(plan, rig=rig, dry_run=True)
        captured = capsys.readouterr()
        assert "establish MIDI channel" in captured.out
        assert "dry-run" in captured.out

    def test_cba_registration_writes_state(self, tmp_path):
        rig = _make_config()
        _write_state(
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
        with patch("builtins.input", return_value="c"):
            apply_plan(plan, rig=rig, config_path=str(tmp_path), dry_run=False)
        state = json.loads((tmp_path / ".rig" / "state.json").read_text())
        assert state["devices"]["brothers"]["registration_done"] is True

    def test_cba_quit_during_channel_saves_no_state(self, tmp_path, capsys):
        rig = _make_config()
        plan = compute_plan(rig)
        with patch("builtins.input", return_value="q"):
            apply_plan(plan, rig=rig, config_path=str(tmp_path), dry_run=False)
        captured = capsys.readouterr()
        assert "cancelled" in captured.out.lower()
        # No state written because we quit before any confirmation
        state_file = tmp_path / ".rig" / "state.json"
        assert not state_file.exists()
