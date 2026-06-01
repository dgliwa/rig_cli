import json
from rig.models.rig import RigConfig
from rig.models.pedal import PedalDefinition, PedalType, MidiConfig, ChaseBlissConfig
from rig.models.preset import DigitalPreset, HXStompPreset, HXBlock
from rig.models.scene import Scene
from rig.models.signal_chain import SignalChainPosition
from rig.engine.diff import compute_diff, format_diff


def _make_rig() -> RigConfig:
    hx = PedalDefinition(id="hx-stomp", manufacturer="Line6", model="HX Stomp", type=PedalType.MODELER, config=MidiConfig(midi_channel=1))
    bro = PedalDefinition(id="brothers", manufacturer="CBA", model="Brothers", type=PedalType.DIGITAL, config=ChaseBlissConfig(midi_channel=3))
    block = HXBlock(name="Amp", type="amp", model="US Double Nrm")
    return RigConfig(
        name="test",
        signal_chain=[SignalChainPosition(pedal_ref="hx-stomp", position=1)],
        pedals={"hx-stomp": hx, "brothers": bro},
        hx_presets={"hx-stomp": [HXStompPreset(id="clean-edge", pedal="hx-stomp", name="Clean Edge", preset_number=12, blocks=[block])]},
        digital_presets={"brothers": [DigitalPreset(id="low-gain", pedal="brothers", name="Low Gain", preset_number=4)]},
        scenes={"test-scene": Scene(name="test-scene", presets={"hx-stomp": "clean-edge", "brothers": "low-gain"})},
    )


class TestDiff:
    def test_diff_detects_new_scene(self, tmp_path):
        rig = _make_rig()
        # No state file → scene is new
        diff = compute_diff(rig, root_path=str(tmp_path))
        assert "test-scene" in diff["scenes"]
        assert diff["scenes"]["test-scene"]["_status"] == "new"

    def test_diff_clean_when_state_matches(self, tmp_path):
        rig = _make_rig()
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(json.dumps({
            "devices": {"hx-stomp": {"last_preset": "clean-edge"}, "brothers": {"last_preset": "low-gain"}},
            "scenes": {"test-scene": {}},
        }))
        diff = compute_diff(rig, root_path=str(tmp_path))
        assert "test-scene" not in diff["scenes"]

    def test_diff_detects_preset_change(self, tmp_path):
        rig = _make_rig()
        state = tmp_path / ".rig" / "state.json"
        state.parent.mkdir(parents=True)
        state.write_text(json.dumps({
            "devices": {"hx-stomp": {"last_preset": "old-preset"}, "brothers": {"last_preset": "low-gain"}},
            "scenes": {"test-scene": {}},
        }))
        diff = compute_diff(rig, root_path=str(tmp_path))
        assert diff["scenes"]["test-scene"]["presets"]["hx-stomp"]["old"] == "old-preset"

    def test_format_diff_includes_arrow(self):
        diff = {
            "scenes": {
                "test-scene": {
                    "_status": "changed",
                    "presets": {"hx-stomp": {"_status": "changed", "old": "old", "new": "new"}},
                },
            },
        }
        output = format_diff(diff)
        assert "→" in output
        assert "test-scene" in output

    def test_format_diff_new_scene(self):
        diff = {
            "scenes": {
                "test-scene": {
                    "_status": "new",
                    "presets": {"hx-stomp": {"_status": "added", "new": "clean-edge"}},
                },
            },
        }
        output = format_diff(diff)
        assert "[new]" in output
        assert "'clean-edge'" in output
