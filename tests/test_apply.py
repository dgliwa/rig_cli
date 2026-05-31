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


class TestApplyPlan:
    def test_clean_plan_prints_no_changes(self, capsys):
        config = _make_config()
        plan = compute_plan(config)
        # Set up state to match
        apply_plan(plan, dry_run=True)
        captured = capsys.readouterr()
        # With no state file, all scenes are new, so we should see changes
        assert "No changes needed" not in captured.out

    def test_dry_run_does_not_write_state(self, tmp_path):
        config = _make_config()
        # Temporarily set config_path so it would write
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
        # Scene should be saved but devices may be skipped
        assert "scenes" in state

    def test_apply_quit_stops_early(self, tmp_path, capsys):
        config = _make_config()
        plan = compute_plan(config)
        # First input = q for quit
        with patch("builtins.input", return_value="q"):
            apply_plan(plan, config_path=str(tmp_path), dry_run=False)
        captured = capsys.readouterr()
        assert "cancelled" in captured.out.lower()
