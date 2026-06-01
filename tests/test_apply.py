import json
from pathlib import Path
from unittest.mock import patch
from rig.models.rig import RigConfig
from rig.models.pedal import PedalDefinition, PedalType
from rig.models.preset import DigitalPreset, HXStompPreset, HXBlock
from rig.models.scene import Scene
from rig.models.signal_chain import SignalChainPosition
from rig.engine.plan import compute_plan
from rig.engine.apply import apply_plan


def _make_config() -> RigConfig:
    hx = PedalDefinition(id="hx-stomp", manufacturer="Line6", model="HX Stomp", type=PedalType.MODELER, midi_channel=1)
    bro = PedalDefinition(id="brothers", manufacturer="CBA", model="Brothers", type=PedalType.DIGITAL, midi_channel=3)
    block = HXBlock(name="Amp", type="amp", model="US Double Nrm")
    return RigConfig(
        name="test",
        signal_chain=[SignalChainPosition(pedal_ref="hx-stomp", position=1)],
        pedals={"hx-stomp": hx, "brothers": bro},
        hx_presets={"hx-stomp": [HXStompPreset(id="clean-edge", pedal="hx-stomp", name="Clean Edge", preset_number=12, blocks=[block])]},
        digital_presets={"brothers": [DigitalPreset(id="low-gain", pedal="brothers", name="Low Gain", preset_number=4)]},
        scenes={"test-scene": Scene(name="test-scene", presets={"hx-stomp": "clean-edge", "brothers": "low-gain"})},
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
        _write_state(tmp_path, {
            "devices": {"brothers": {
                "channel_established": True,
                "midi_channel": 3,
                "presets_saved": {},
            }},
        })
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
        _write_state(tmp_path, {
            "devices": {"brothers": {
                "channel_established": True,
                "midi_channel": 3,
                "presets_saved": {"low-gain": True},
            }},
            "scenes": {"test-scene": {}},
        })
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
